"""
LLM Router — tries Groq first, falls back to Gemini, then Ollama.
All agents call llm_call() and never worry about which provider responds.
"""

import json
import time
import requests
from langsmith import traceable
import langsmith
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import (
    GROQ_API_KEY, GEMINI_API_KEY,
    GROQ_MODEL, GEMINI_MODEL, OLLAMA_MODEL,
    LLM_TIMEOUT
)
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
@traceable
def llm_call(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Call LLM with automatic fallback: Groq -> Gemini -> Ollama.
    Returns the model's text response as a string.
    If json_mode=True, the response is expected to be valid JSON.
    """
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
            print(f"  [LLM] ✓ {name} responded")
            return result
        except Exception as e:
            print(f"  [LLM] ✗ {name} failed: {e}")
            last_error = e
            continue

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


# ── Groq ──────────────────────────────────────────────────────────────────────

def _call_groq(system: str, user: str, json_mode: bool) -> str:
    keys = [k for k in [
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("GROQ_API_KEY_2", ""),
    ] if k]

    if not keys:
        raise ValueError("No GROQ_API_KEY set")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    for key in keys:
        for attempt in range(2):
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=LLM_TIMEOUT
            )
            if resp.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"  [LLM] Groq rate limited, waiting {wait}s...")
                import time
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    raise RuntimeError("All Groq keys rate limited")
# ── Gemini ────────────────────────────────────────────────────────────────────

def _call_gemini(system: str, user: str, json_mode: bool) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    combined_prompt = f"{system}\n\n{user}"
    if json_mode:
        combined_prompt += "\n\nRespond ONLY with valid JSON. No explanation, no markdown backticks."

    payload = {
        "contents": [{"parts": [{"text": combined_prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
    }

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
        json=payload,
        timeout=LLM_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


# ── Ollama (local) ────────────────────────────────────────────────────────────

def _call_ollama(system: str, user: str, json_mode: bool) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "stream": False,
        "options": {"temperature": 0.3}
    }
    if json_mode:
        payload["format"] = "json"

    resp = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=60  # Ollama is slower locally
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── Helper: parse JSON from LLM response ─────────────────────────────────────

def parse_json_response(text: str) -> dict:
    """Safely parse JSON from an LLM response, handling common formatting issues."""
    import re
    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    # Fix math expressions like 68.0 * 22 * 1.6 + 300 -> evaluate them
    def eval_math(match):
        try:
            result = eval(match.group(0))
            return str(round(float(result), 2))
        except:
            return match.group(0)
    text = re.sub(r'[\d.]+\s*[\*\+\-\/]\s*[\d.\s\*\+\-\/]+', eval_math, text)

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract first JSON object or array using regex
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Remove trailing commas before } or ]
    cleaned = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse LLM response as JSON.\nRaw response:\n{text}\nError: {e}")
# ── Quick test ────────────────────────────────────────────────────────────────

def fix_reps_in_plan(data: dict) -> dict:
    """Post-process parsed JSON to fix numeric reps to string ranges."""
    reps_map = {
        1: "1-3", 2: "6-8", 3: "8-10", 4: "8-12",
        5: "10-12", 6: "12-15", 7: "12-15", 8: "8-12",
        9: "8-12", 10: "10-12", 11: "10-15", 12: "10-15",
        15: "12-15", 20: "15-20"
    }
    for day in data.get("days", []):
        for ex in day.get("exercises", []):
            reps = ex.get("reps")
            if isinstance(reps, (int, float)):
                ex["reps"] = reps_map.get(int(reps), f"{int(reps)}-{int(reps)+2}")
    return data

if __name__ == "__main__":
    response = llm_call(
        system_prompt="You are a helpful assistant. Always respond in JSON.",
        user_prompt='Say hello and tell me your model name. Respond as {"greeting": "...", "model": "..."}',
        json_mode=True
    )
    print("Response:", response)
    parsed = parse_json_response(response)
    print("Parsed:", parsed)
