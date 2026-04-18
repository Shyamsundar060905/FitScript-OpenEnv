"""
Ablation study.

Measures the contribution of each system component by running the full
pipeline with each component selectively disabled:

  - full:           all components enabled (baseline for this study)
  - no_rag:         semantic retrieval returns empty
  - no_progress:    progress agent returns no signals
  - no_conflict:    conflict resolver is a no-op
  - no_overload:    fitness agent doesn't receive progressive overload prescriptions
  - no_verification: nutrition agent doesn't verify macros against IFCT/USDA

Each variant is scored by the LLM judge on the same rubric. We report:
  - Mean score per dimension per variant
  - Delta vs full pipeline per dimension (shows what each component adds)
  - Statistical significance via bootstrap CI (optional)

This is the ablation table that goes into your BTP report. Example claim
from the numbers: "Removing the RAG layer dropped scientific_grounding
from 4.6 to 3.2 (Δ=-1.4), confirming the retrieval component contributes
substantively to evidence-based justification."
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from typing import Callable, Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from memory.long_term import load_profile
from agents import fitness_agent, nutrition_agent, progress_agent
import agents.orchestrator as orch
import memory.semantic as semantic
from tests.eval_judge import judge_plan, format_plan_for_judging, JudgeScores


VARIANTS = [
    "full",
    "no_rag",
    "no_progress",
    "no_conflict",
    "no_overload",
    "no_verification",
]


@dataclass
class AblationResult:
    variant: str
    scores: JudgeScores
    prescription_summary: str


# ── Monkey-patch helpers ──────────────────────────────────────────────────────

class _Patches:
    """Context-manager style patch stack for clean variant switching."""

    def __init__(self):
        self._originals = {}

    def patch(self, module, attr, replacement):
        self._originals.setdefault((id(module), attr), getattr(module, attr))
        setattr(module, attr, replacement)

    def restore(self):
        for (mod_id, attr), original in self._originals.items():
            # Find module by id
            import importlib
            for name in list(sys.modules):
                if id(sys.modules[name]) == mod_id:
                    setattr(sys.modules[name], attr, original)
                    break
        self._originals.clear()


def _apply_variant(variant: str, patches: _Patches):
    """Apply monkey-patches for a variant."""
    if variant == "no_rag":
        def _empty_retrieve(*args, **kwargs):
            return "", []
        patches.patch(semantic, "retrieve_for_agent", _empty_retrieve)

    elif variant == "no_progress":
        # Make progress agent return an empty signal list
        original_analyze = progress_agent.analyze_progress
        def _no_signals(profile):
            return []
        patches.patch(progress_agent, "analyze_progress", _no_signals)

    elif variant == "no_conflict":
        patches.patch(orch, "resolve_conflicts", lambda a, b, c: [])

    elif variant == "no_overload":
        def _no_overload(*args, **kwargs):
            return []
        patches.patch(fitness_agent, "_build_overload_prescriptions", _no_overload)

    elif variant == "no_verification":
        # Replace verify_meal_macros with a function that returns zero coverage
        from data.knowledge_base import nutrition_db
        def _empty_verify(foods, allow_fuzzy=True):
            return {
                "calories": 0, "protein_g": 0, "carbs_g": 0,
                "fats_g": 0, "fiber_g": 0,
                "verified_items": [], "unverified_items": list(foods),
                "coverage": 0.0, "sources": [],
            }
        patches.patch(nutrition_db, "verify_meal_macros", _empty_verify)
        # Also patch the imported reference inside nutrition_agent
        patches.patch(nutrition_agent, "verify_meal_macros", _empty_verify)


def run_variant(user_id: str, variant: str, week_number: int = 1) -> AblationResult:
    """Run the pipeline with one ablation variant and score it."""
    patches = _Patches()
    try:
        _apply_variant(variant, patches)
        prescription = orch.run_pipeline(
            user_id,
            week_number=week_number,
            skip_rate_limit=True,
        )
    finally:
        patches.restore()

    profile = load_profile(user_id)
    plan_text = format_plan_for_judging(prescription)
    scores = judge_plan(profile.to_summary(), plan_text)
    return AblationResult(
        variant=variant,
        scores=scores,
        prescription_summary=plan_text[:400],
    )


def run_ablation_study(
    user_id: str,
    variants: Optional[list[str]] = None,
    week_number: int = 1,
) -> dict[str, AblationResult]:
    """Run all variants and return results keyed by variant name."""
    variants = variants or VARIANTS
    results = {}
    for v in variants:
        print(f"\n{'='*60}\n  ABLATION VARIANT: {v}\n{'='*60}")
        try:
            result = run_variant(user_id, v, week_number=week_number)
            results[v] = result
            print(f"  ✓ {v}: overall {result.scores.overall}")
        except Exception as e:
            print(f"  ✗ {v} failed: {e}")
            results[v] = None
    return results


def print_ablation_table(results: dict[str, AblationResult]):
    """Print a markdown-ready ablation table."""
    dims = [
        "personalization", "goal_alignment", "constraint_respect",
        "scientific_grounding", "specificity", "safety", "coherence", "overall",
    ]

    full_scores = results.get("full")

    header = f"{'Variant':<18} " + " ".join(f"{d[:10]:>10}" for d in dims)
    print("\n" + header)
    print("-" * len(header))

    for variant, result in results.items():
        if result is None:
            print(f"{variant:<18}  [FAILED]")
            continue
        row = f"{variant:<18}"
        for d in dims:
            val = getattr(result.scores, d) if d != "overall" else result.scores.overall
            row += f" {val:>10.2f}"
        print(row)

    # Delta table
    if full_scores:
        print("\n── Delta vs FULL (negative = this component contributes that dimension) ──")
        print(header)
        print("-" * len(header))
        for variant, result in results.items():
            if variant == "full" or result is None:
                continue
            row = f"{variant:<18}"
            for d in dims:
                full_val = getattr(full_scores.scores, d) if d != "overall" else full_scores.scores.overall
                var_val = getattr(result.scores, d) if d != "overall" else result.scores.overall
                delta = var_val - full_val
                row += f" {delta:>+10.2f}"
            print(row)


if __name__ == "__main__":
    print("── Ablation Study Configuration ──\n")
    print(f"  Variants: {VARIANTS}")
    print(f"  Dimensions scored: {list(j for j in dir(JudgeScores) if not j.startswith('_'))[:8]}")
    print("\n  Run with: run_ablation_study(user_id) in a real environment")
    print("  (requires seeded ChromaDB, running LLM API, a user profile with data)")