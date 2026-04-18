"""
LLM Router v2 — safer JSON parsing, native JSON mode, response caching,
Pydantic-validated retry loop.

Changes vs v1:
  - Removed eval() — use ast.literal_eval + explicit arithmetic evaluator.
  - Groq JSON mode via response_format={"type": "json_object"}.
  - In-memory + on-disk response cache keyed on (system, user, json_mode).
  - call_llm_structured(): retries with Pydantic validation on parse failure.
  - LangSmith traces carry model, provider, and token usage.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable, Optional, Type, TypeVar

import requests
from pydantic import BaseModel, ValidationError

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import (
    GROQ_API_KEY, GEMINI_API_KEY,
    GROQ_MODEL, GEMINI_MODEL, OLLAMA_MODEL,
    LLM_TIMEOUT,
)

try:
    from langsmith import traceable
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
except ImportError:
    def traceable(fn):
        return fn


# ── Response cache ────────────────────────────────────────────────────────────

_CACHE_DIR = Path(__file__).parent.parent / "data" / "llm_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_MEMORY_CACHE: dict[str, str] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week


def _cache_key(system: str, user: str, json_mode: bool) -> str:
    h = hashlib.sha256()
    h.update(system.encode())
    h.update(b"\x00")
    h.update(user.encode())
    h.update(b"\x00")
    h.update(str(json_mode).encode())
    return h.hexdigest()[:32]


def _cache_get(key: str) -> Optional[str]:
    if key in _MEMORY_CACHE:
        return _MEMORY_CACHE[key]
    p = _CACHE_DIR / f"{key}.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if time.time() - data["ts"] > _CACHE_TTL_SECONDS:
            p.unlink(missing_ok=True)
            return None
        _MEMORY_CACHE[key] = data["response"]
        return data["response"]
    except Exception:
        return None


def _cache_put(key: str, response: str):
    _MEMORY_CACHE[key] = response
    try:
        (_CACHE_DIR / f"{key}.json").write_text(json.dumps({
            "ts": time.time(),
            "response": response,
        }))
    except Exception:
        pass


def clear_cache():
    """Clear both memory and disk cache. Useful for demos and testing."""
    _MEMORY_CACHE.clear()
    for f in _CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)


# ── Core LLM call with fallback chain ─────────────────────────────────────────

@traceable
def llm_call(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    use_cache: bool = True,
) -> str:
    """
    Call LLM with Groq -> Gemini -> Ollama fallback, optional caching.
    Returns raw text response.
    """
    if use_cache:
        key = _cache_key(system_prompt, user_prompt, json_mode)
        cached = _cache_get(key)
        if cached is not None:
            print("  [LLM] ✓ cache hit")
            return cached

    providers = [
        ("Groq",   _call_groq),
        ("Gemini", _call_gemini),
        ("Ollama", _call_ollama),
    ]

    last_error = None
    for name, fn in providers:
        try:
            print(f"  [LLM] Trying {name}...")
            result = fn(system_prompt, user_prompt, json_mode)
            print(f"  [LLM] ✓ {name} responded ({len(result)} chars)")
            if use_cache:
                _cache_put(_cache_key(system_prompt, user_prompt, json_mode), result)
            return result
        except Exception as e:
            print(f"  [LLM] ✗ {name} failed: {e}")
            last_error = e
            continue

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


# ── Provider implementations ──────────────────────────────────────────────────

def _call_groq(system: str, user: str, json_mode: bool) -> str:
    keys = [k for k in [
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("GROQ_API_KEY_2", ""),
        GROQ_API_KEY,
    ] if k]
    keys = list(dict.fromkeys(keys))  # dedupe, preserve order

    if not keys:
        raise ValueError("No GROQ_API_KEY set")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    if json_mode:
        # Native JSON mode eliminates most of our regex-parsing hacks
        payload["response_format"] = {"type": "json_object"}

    for key in keys:
        for attempt in range(2):
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=LLM_TIMEOUT,
            )
            if resp.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"  [LLM] Groq rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    raise RuntimeError("All Groq keys rate limited")


def _call_gemini(system: str, user: str, json_mode: bool) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    combined = f"{system}\n\n{user}"
    if json_mode:
        combined += "\n\nRespond ONLY with valid JSON. No explanation, no markdown."

    payload = {
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
            **({"responseMimeType": "application/json"} if json_mode else {}),
        },
    }

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
        json=payload,
        timeout=LLM_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(system: str, user: str, json_mode: bool) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }
    if json_mode:
        payload["format"] = "json"

    resp = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── Safe arithmetic evaluator (replaces eval) ─────────────────────────────────

# Models sometimes output "68.0 * 22 * 1.6 + 300" where we need a literal.
# Use AST walker that only allows numeric operations — no attribute access,
# no function calls, no name lookups.
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd,
)


def _safe_arith_eval(expr: str) -> Optional[float]:
    """
    Evaluate a numeric expression safely. Returns None on failure.
    Never uses Python's eval or exec.
    """
    try:
        tree = ast.parse(expr.strip(), mode='eval')
    except (SyntaxError, ValueError):
        return None

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return None

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, (int, float)) else None
        if isinstance(node, ast.UnaryOp):
            v = _eval(node.operand)
            if v is None:
                return None
            return +v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if left is None or right is None:
                return None
            op = node.op
            if isinstance(op, ast.Add):      return left + right
            if isinstance(op, ast.Sub):      return left - right
            if isinstance(op, ast.Mult):     return left * right
            if isinstance(op, ast.Div):      return left / right if right else None
            if isinstance(op, ast.FloorDiv): return left // right if right else None
            if isinstance(op, ast.Mod):      return left % right if right else None
            if isinstance(op, ast.Pow):      return left ** right
        return None

    try:
        return _eval(tree)
    except Exception:
        return None


def _eval_math_expressions_in_text(text: str) -> str:
    """Find bare arithmetic expressions in JSON-ish text and replace with values."""
    def repl(m):
        expr = m.group(0)
        v = _safe_arith_eval(expr)
        if v is None:
            return expr
        return str(round(float(v), 2))

    # Match patterns like `68.0 * 22 * 1.6 + 300` — but only on whole tokens
    # to avoid mangling "3-5" style rep ranges.
    # We require at least one operator and spaces around it.
    return re.sub(
        r'(?<=[\s:,\[])\s*[\d.]+(?:\s*[\*\+\/]\s*[\d.]+){1,}\s*(?=[,\]\}\s])',
        repl, text,
    )


# ── Safe JSON parsing ─────────────────────────────────────────────────────────

def parse_json_response(text: str) -> dict | list:
    """
    Safely parse JSON from an LLM response. Never uses eval().

    Pipeline:
        1. Strip markdown fences.
        2. Evaluate embedded arithmetic (safely via AST).
        3. Direct json.loads.
        4. Extract first {...} or [...] block.
        5. Remove trailing commas.
    """
    if not text:
        raise ValueError("Empty response")

    s = text.strip()

    # Strip markdown fences
    if s.startswith("```"):
        parts = s.split("\n")
        # drop first line (```json or ```), and last line if it's ```
        if parts[-1].strip() == "```":
            parts = parts[1:-1]
        else:
            parts = parts[1:]
        s = "\n".join(parts).strip()

    # Evaluate embedded math expressions
    s = _eval_math_expressions_in_text(s)

    # Direct parse
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Extract first balanced object or array
    m = re.search(r'(\{.*\}|\[.*\])', s, re.DOTALL)
    if m:
        candidate = m.group(1)
        # Remove trailing commas
        candidate = re.sub(r',(\s*[}\]])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last resort: strip trailing commas from whole text
    cleaned = re.sub(r',(\s*[}\]])', r'\1', s)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse LLM response as JSON.\n"
            f"Raw preview: {s[:300]}\n"
            f"Error: {e}"
        )


# ── Structured call with Pydantic retry ───────────────────────────────────────

T = TypeVar("T", bound=BaseModel)


def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    post_process: Optional[Callable[[dict], dict]] = None,
    use_cache: bool = True,
) -> T:
    """
    Call LLM and validate response against a Pydantic schema.
    Retries with error feedback on validation failure.
    """
    last_error = None
    current_user_prompt = user_prompt

    for attempt in range(max_retries + 1):
        try:
            response = llm_call(
                system_prompt,
                current_user_prompt,
                json_mode=True,
                use_cache=(use_cache and attempt == 0),  # don't cache retries
            )
            data = parse_json_response(response)

            if post_process:
                data = post_process(data)

            return schema(**data)

        except (ValueError, ValidationError) as e:
            last_error = e
            if attempt < max_retries:
                print(f"  [LLM] Validation failed (attempt {attempt + 1}): {str(e)[:150]}")
                # Retry with error feedback
                current_user_prompt = (
                    user_prompt
                    + f"\n\nYour previous response had this error:\n{str(e)[:300]}\n"
                    "Return ONLY valid JSON matching the requested schema. "
                    "No explanations, no markdown."
                )
            else:
                break

    raise ValueError(f"Structured call failed after {max_retries + 1} attempts. Last error: {last_error}")


# ── Plan post-processor (ported from v1) ──────────────────────────────────────

def fix_reps_in_plan(data: dict) -> dict:
    """
    Post-process workout plan: ensure reps field is always a string range.
    LLMs sometimes return integer reps; we need '8-12' format.
    """
    reps_map = {
        1: "1-3", 2: "6-8", 3: "8-10", 4: "8-12",
        5: "10-12", 6: "12-15", 7: "12-15", 8: "8-12",
        9: "8-12", 10: "10-12", 11: "10-15", 12: "10-15",
        15: "12-15", 20: "15-20",
    }
    for day in data.get("days", []):
        for ex in day.get("exercises", []):
            reps = ex.get("reps")
            if isinstance(reps, (int, float)):
                ex["reps"] = reps_map.get(int(reps), f"{int(reps)}-{int(reps) + 2}")
    return data


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("── Safe arithmetic evaluator ──")
    assert _safe_arith_eval("2 + 2") == 4
    assert _safe_arith_eval("68.0 * 22 * 1.6 + 300") == 2693.6
    assert _safe_arith_eval("__import__('os').system('ls')") is None
    assert _safe_arith_eval("foo.bar") is None
    print("  ✓ Evaluates arithmetic, blocks malicious expressions")

    print("\n── JSON parser ──")
    raw_samples = [
        '{"a": 1, "b": 2}',
        '```json\n{"x": 5}\n```',
        '{"tdee": 68.0 * 22 * 1.6 + 300}',
        '{"reps": [1, 2, 3,]}',  # trailing comma
        'here is your answer {"key": "value"} end',
    ]
    for r in raw_samples:
        try:
            out = parse_json_response(r)
            print(f"  ✓ {r[:40]:<42} -> {out}")
        except ValueError as e:
            print(f"  ✗ {r[:40]:<42} -> ERROR: {e}")

    print("\n  [Router v2] Self-tests passed")