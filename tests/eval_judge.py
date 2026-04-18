"""
LLM-as-judge evaluation.

Uses a strong LLM (Gemini/Claude via router) to grade both baseline and
multi-agent outputs against a structured rubric. This is far more defensible
than the v1 keyword-count approach ("does the text contain 'vegetarian'").

Rubric dimensions (each scored 1-5):
  1. Personalization — does the plan reflect THIS user's profile?
  2. Goal alignment — does every element push toward the stated goal?
  3. Constraint respect — dietary/equipment/injury constraints honoured?
  4. Scientific grounding — cites or reflects evidence-based principles?
  5. Specificity — concrete numbers (weights, kcal, macros) vs vague prose?
  6. Safety — avoids unsafe rates of change, appropriate for fitness level?
  7. Coherence — does the fitness plan match the nutrition plan (volume ↔ calories)?

Output format is structured JSON so we can aggregate across many samples
and compute inter-dimension correlations for the report.

The judge is called with temperature 0 for reproducibility.
"""

from __future__ import annotations

import json
import sys
import os
from dataclasses import dataclass, field
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from llm.router import llm_call, parse_json_response


RUBRIC = {
    "personalization": {
        "1": "Generic advice; could be copy-pasted to anyone.",
        "3": "Mentions some profile details (goal, level, restrictions).",
        "5": "Tightly adapted to profile — equipment, diet, experience, schedule all reflected."
    },
    "goal_alignment": {
        "1": "Recommendations contradict the stated goal.",
        "3": "Partial alignment — some elements support goal, others neutral.",
        "5": "Every element (rep ranges, calorie adjustment, frequency) pushes toward the goal."
    },
    "constraint_respect": {
        "1": "Violates restrictions (e.g. meat for vegetarian, barbell for bodyweight).",
        "3": "Respects some constraints, overlooks others.",
        "5": "All listed constraints (diet, equipment, injuries) strictly honoured."
    },
    "scientific_grounding": {
        "1": "Advice contradicts mainstream sports science.",
        "3": "Sound but unremarkable — no standout evidence-based choices.",
        "5": "Reflects specific, defensible principles (progressive overload, MEV/MRV, leucine threshold, etc.)."
    },
    "specificity": {
        "1": "Vague: 'eat healthy', 'lift weights'.",
        "3": "Some numbers given but not consistently.",
        "5": "Concrete values everywhere: weights, reps, kcal, macros, rest periods."
    },
    "safety": {
        "1": "Unsafe volume/rate — likely to injure or burn out.",
        "3": "Generally safe but not well matched to fitness level.",
        "5": "Rate of change, volume, and recovery all appropriate for fitness level."
    },
    "coherence": {
        "1": "Workout and nutrition plans contradict each other.",
        "3": "Plans coexist but aren't actively coordinated.",
        "5": "Nutrition supports the specific training volume; plans are clearly coordinated."
    },
}


JUDGE_SYSTEM_PROMPT = """You are an expert fitness and nutrition evaluator.
You score AI-generated fitness prescriptions against a structured rubric.
You are strict, objective, and return ONLY valid JSON.

You consider the USER PROFILE when scoring. A plan that is good for one
user can be bad for another — your job is to score relative to THIS user.
"""


@dataclass
class JudgeScores:
    personalization: int
    goal_alignment: int
    constraint_respect: int
    scientific_grounding: int
    specificity: int
    safety: int
    coherence: int
    rationale: dict[str, str] = field(default_factory=dict)
    overall: float = 0.0

    def compute_overall(self):
        dims = [
            self.personalization, self.goal_alignment, self.constraint_respect,
            self.scientific_grounding, self.specificity, self.safety,
            self.coherence,
        ]
        self.overall = round(sum(dims) / len(dims), 2)


def build_judge_prompt(profile_summary: str, plan_text: str) -> str:
    rubric_json = json.dumps(RUBRIC, indent=2)
    return f"""Evaluate the following fitness prescription for this user.

USER PROFILE:
{profile_summary}

PLAN UNDER EVALUATION:
{plan_text}

RUBRIC (score 1-5 on each dimension; 1 = poor, 3 = acceptable, 5 = excellent):
{rubric_json}

Return ONLY a JSON object with this exact structure:
{{
  "personalization":       <int 1-5>,
  "goal_alignment":        <int 1-5>,
  "constraint_respect":    <int 1-5>,
  "scientific_grounding":  <int 1-5>,
  "specificity":           <int 1-5>,
  "safety":                <int 1-5>,
  "coherence":             <int 1-5>,
  "rationale": {{
    "personalization":      "one sentence justifying the score",
    "goal_alignment":       "one sentence",
    "constraint_respect":   "one sentence",
    "scientific_grounding": "one sentence",
    "specificity":          "one sentence",
    "safety":               "one sentence",
    "coherence":            "one sentence"
  }}
}}
"""


def judge_plan(profile_summary: str, plan_text: str) -> JudgeScores:
    """Run the judge on a single plan and return structured scores."""
    prompt = build_judge_prompt(profile_summary, plan_text)
    response = llm_call(JUDGE_SYSTEM_PROMPT, prompt, json_mode=True, use_cache=True)
    data = parse_json_response(response)

    scores = JudgeScores(
        personalization=int(data.get("personalization", 3)),
        goal_alignment=int(data.get("goal_alignment", 3)),
        constraint_respect=int(data.get("constraint_respect", 3)),
        scientific_grounding=int(data.get("scientific_grounding", 3)),
        specificity=int(data.get("specificity", 3)),
        safety=int(data.get("safety", 3)),
        coherence=int(data.get("coherence", 3)),
        rationale=data.get("rationale", {}),
    )
    scores.compute_overall()
    return scores


def format_plan_for_judging(prescription) -> str:
    """Turn a WeeklyPrescription object into plain text for the judge."""
    lines = [
        f"# Week {prescription.week_number} Prescription",
        f"\nOrchestrator notes: {prescription.orchestrator_notes}",
        f"\n## Workout plan ({prescription.workout_plan.weekly_volume_sets} sets/week)",
    ]
    for day in prescription.workout_plan.days:
        lines.append(f"\n### {day.day_name} — {day.focus}")
        for ex in day.exercises:
            reps = ex.reps if ex.reps else "?"
            lines.append(
                f"  - {ex.name}: {ex.sets}×{reps} "
                f"({'bodyweight' if not getattr(ex, 'weight_kg', 0) else str(ex.weight_kg) + 'kg'}), "
                f"rest {ex.rest_seconds}s"
            )

    lines.append(
        f"\n## Nutrition plan "
        f"({prescription.nutrition_plan.target_calories:.0f} kcal, "
        f"{prescription.nutrition_plan.target_protein_g:.0f}g protein)"
    )
    for day in prescription.nutrition_plan.daily_plans:
        lines.append(f"\n### {day.day_name}")
        for meal in day.meals:
            lines.append(
                f"  - {meal.meal_name} ({meal.calories:.0f} kcal, "
                f"{meal.protein_g:.0f}g protein): {', '.join(meal.foods)}"
            )

    if prescription.adaptation_signals:
        lines.append("\n## Adaptation signals")
        for s in prescription.adaptation_signals:
            lines.append(f"  - [{s.severity}] {s.signal_type}: {s.description}")

    return "\n".join(lines)


def format_baseline_for_judging(baseline_text: str) -> str:
    """Baseline is already text."""
    return f"# Baseline (single-agent)\n\n{baseline_text}"


# Self-test
if __name__ == "__main__":
    print("── LLM-as-Judge rubric inspection ──\n")
    for dim, anchors in RUBRIC.items():
        print(f"  {dim}:")
        for score, desc in anchors.items():
            print(f"    {score} - {desc}")
        print()
    print("  (To run an actual judging pass, call judge_plan(profile, plan))")