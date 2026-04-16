"""
Evaluation — compares single-agent baseline vs full multi-agent system.
This is the core research evaluation for the BTP.
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call
from memory.long_term import load_profile, create_sample_user
from memory.episodic import clear_user_data, log_progress
from agents.orchestrator import run_pipeline
from schemas import ProgressLog, WeeklyPrescription
from datetime import datetime, timedelta


# ── Baseline: single LLM call, no memory, no agents, no RAG ──────────────────

def run_baseline(profile_summary: str, has_plateau: bool = False) -> dict:
    """
    Naive single-agent baseline.
    One LLM call with basic user info — no memory, no RAG, no conflict resolution.
    """
    plateau_note = ""
    if has_plateau:
        plateau_note = "\nNote: User has been on the same plan for 2 weeks."

    prompt = f"""Create a weekly fitness and nutrition plan for this user:

{profile_summary}
{plateau_note}

Provide:
1. A weekly workout plan
2. Daily nutrition targets
3. Any recommendations

Be specific and practical."""

    response = llm_call(
        "You are a fitness and nutrition assistant.",
        prompt,
        json_mode=False
    )
    return {"response": response, "type": "baseline"}


# ── Scoring rubric ────────────────────────────────────────────────────────────

def score_baseline(response: str, profile) -> dict:
    """Score the baseline response against evaluation criteria."""
    text = response.lower()
    scores = {}

    # 1. Equipment specificity — does it mention user's actual equipment?
    equipment_mentioned = sum(
        1 for eq in profile.available_equipment
        if eq.lower() in text
    )
    scores["equipment_specificity"] = min(equipment_mentioned / max(len(profile.available_equipment), 1), 1.0)

    # 2. Diet compliance — does it respect dietary restrictions?
    if profile.dietary_restrictions:
        diet_keywords = {
            "vegetarian": ["vegetarian", "plant", "tofu", "legume", "lentil", "paneer", "dal"],
            "vegan": ["vegan", "plant-based", "tofu", "tempeh"],
            "gluten_free": ["gluten-free", "rice", "quinoa", "gluten free"],
        }
        diet_score = 0
        for restriction in profile.dietary_restrictions:
            keywords = diet_keywords.get(restriction, [restriction])
            if any(k in text for k in keywords):
                diet_score += 1
        scores["diet_compliance"] = min(diet_score / len(profile.dietary_restrictions), 1.0)
    else:
        scores["diet_compliance"] = 1.0

    # 3. Adaptation — does it mention plateau or plan changes?
    adaptation_keywords = ["plateau", "change", "adjust", "increase", "modify",
                           "progressive overload", "deload", "variation"]
    scores["adaptation_awareness"] = min(
        sum(1 for k in adaptation_keywords if k in text) / 3, 1.0
    )

    # 4. Knowledge grounding — does it use scientific terminology?
    science_keywords = ["progressive overload", "hypertrophy", "protein synthesis",
                        "tdee", "deficit", "surplus", "compound", "macro",
                        "rep range", "volume", "frequency"]
    scores["knowledge_grounding"] = min(
        sum(1 for k in science_keywords if k in text) / 4, 1.0
    )

    # 5. Specificity — specific numbers vs vague advice
    import re
    numbers = len(re.findall(r'\d+', text))
    scores["numerical_specificity"] = min(numbers / 20, 1.0)

    scores["total"] = round(sum(scores.values()) / len(scores), 3)
    return scores


def score_multiagent(prescription: WeeklyPrescription, profile, has_plateau: bool) -> dict:
    """Score the multi-agent system output."""
    scores = {}

    # 1. Equipment specificity — workout plan uses correct equipment
    workout_text = " ".join(
        ex.name.lower()
        for day in prescription.workout_plan.days
        for ex in day.exercises
    )
    equipment_mentioned = sum(
        1 for eq in profile.available_equipment
        if eq.lower().replace("_", " ") in workout_text
        or any(word in workout_text for word in eq.lower().split("_"))
    )
    scores["equipment_specificity"] = min(
        equipment_mentioned / max(len(profile.available_equipment), 1), 1.0
    )

    # 2. Diet compliance — nutrition plan respects restrictions
    nutrition_text = " ".join(
        food.lower()
        for day in prescription.nutrition_plan.daily_plans
        for meal in day.meals
        for food in meal.foods
    )
    diet_keywords = {
        "vegetarian": ["tofu", "paneer", "lentil", "chickpea", "dal", "yogurt",
                       "egg", "quinoa", "bean", "tempeh"],
        "vegan": ["tofu", "tempeh", "lentil", "chickpea", "quinoa"],
        "gluten_free": ["rice", "quinoa", "potato"],
    }
    if profile.dietary_restrictions:
        diet_score = 0
        for restriction in profile.dietary_restrictions:
            keywords = diet_keywords.get(restriction, [restriction])
            if any(k in nutrition_text for k in keywords):
                diet_score += 1
        scores["diet_compliance"] = min(
            diet_score / len(profile.dietary_restrictions), 1.0
        )
    else:
        scores["diet_compliance"] = 1.0

    # 3. Adaptation — did it detect and respond to plateau?
    if has_plateau:
        plateau_detected = any(
            s.signal_type in ["plateau", "overtraining"]
            for s in prescription.adaptation_signals
        )
        conflict_fired = len(prescription.conflicts_resolved) > 0
        scores["adaptation_awareness"] = (
            1.0 if plateau_detected and conflict_fired else
            0.6 if plateau_detected else 0.2
        )
    else:
        scores["adaptation_awareness"] = 0.8  # no plateau to detect, neutral score

    # 4. Knowledge grounding — RAG injected knowledge
    notes_text = prescription.orchestrator_notes.lower()
    science_keywords = ["volume", "protein", "calorie", "recovery", "overtraining",
                        "plateau", "progressive", "deficit", "surplus", "sets"]
    scores["knowledge_grounding"] = min(
        sum(1 for k in science_keywords if k in notes_text) / 4, 1.0
    )

    # 5. Numerical specificity — concrete numbers in plan
    scores["numerical_specificity"] = min(
        (prescription.workout_plan.weekly_volume_sets > 0) * 0.4 +
        (prescription.nutrition_plan.target_calories > 0) * 0.4 +
        (prescription.nutrition_plan.target_protein_g > 0) * 0.2,
        1.0
    )

    scores["total"] = round(sum(scores.values()) / len(scores), 3)
    return scores


# ── Main evaluation ───────────────────────────────────────────────────────────

def run_evaluation():
    print("\n" + "="*60)
    print("  EVALUATION: Baseline vs Multi-Agent System")
    print("="*60)

    # Setup
    profile = create_sample_user()
    clear_user_data(profile.user_id)
    print(f"\n  User: {profile.name} | Goal: {profile.goal} | Level: {profile.fitness_level}")

    # ── Round 1: No plateau (fresh user) ─────────────────────────────────────
    print("\n" + "-"*60)
    print("  ROUND 1 — Fresh user, no history")
    print("-"*60)

    print("\n  [Baseline] Running single-agent...")
    baseline_r1 = run_baseline(profile.to_summary(), has_plateau=False)
    baseline_scores_r1 = score_baseline(baseline_r1["response"], profile)

    print("  Waiting 60 seconds for rate limit reset...")
    time.sleep(60)

    print("\n  [Multi-Agent] Running full pipeline...")
    ma_r1 = run_pipeline(profile.user_id, week_number=1)
    ma_scores_r1 = score_multiagent(ma_r1, profile, has_plateau=False)

    # ── Seed plateau data ─────────────────────────────────────────────────────
    print("\n  Seeding plateau data...")
    for i in range(14):
        date = (datetime.now() - timedelta(days=14-i)).strftime("%Y-%m-%d")
        log_progress(ProgressLog(
            user_id=profile.user_id,
            date=date,
            weight_kg=78.0,
            workout_completed=(i % 7 not in [2, 6]),
            workout_rating=2,
            calories_eaten=2100.0,
            notes="Eval plateau data"
        ))

    print("  Waiting 90 seconds for rate limit reset...")
    time.sleep(90)

    # ── Round 2: With plateau ─────────────────────────────────────────────────
    print("\n" + "-"*60)
    print("  ROUND 2 — After 2 weeks of plateau")
    print("-"*60)

    print("\n  [Baseline] Running single-agent with plateau hint...")
    baseline_r2 = run_baseline(profile.to_summary(), has_plateau=True)
    baseline_scores_r2 = score_baseline(baseline_r2["response"], profile)

    print("  Waiting 60 seconds for rate limit reset...")
    time.sleep(60)

    print("\n  [Multi-Agent] Running full pipeline with plateau data...")
    ma_r2 = run_pipeline(profile.user_id, week_number=2)
    ma_scores_r2 = score_multiagent(ma_r2, profile, has_plateau=True)

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  EVALUATION RESULTS")
    print("="*60)

    metrics = ["equipment_specificity", "diet_compliance",
               "adaptation_awareness", "knowledge_grounding",
               "numerical_specificity", "total"]

    print(f"\n  {'Metric':<28} {'Baseline R1':>11} {'Multi-A R1':>11} {'Baseline R2':>11} {'Multi-A R2':>11}")
    print("  " + "-"*56)

    for m in metrics:
        b1 = baseline_scores_r1.get(m, 0)
        ma1 = ma_scores_r1.get(m, 0)
        b2 = baseline_scores_r2.get(m, 0)
        ma2 = ma_scores_r2.get(m, 0)
        marker = " ◄" if m == "total" else ""
        print(f"  {m:<28} {b1:>11.2f} {ma1:>11.2f} {b2:>11.2f} {ma2:>11.2f}{marker}")

    # ── Key findings ──────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  KEY FINDINGS")
    print("="*60)

    total_improvement_r1 = ma_scores_r1["total"] - baseline_scores_r1["total"]
    total_improvement_r2 = ma_scores_r2["total"] - baseline_scores_r2["total"]
    adaptation_delta = ma_scores_r2["adaptation_awareness"] - baseline_scores_r2["adaptation_awareness"]

    print(f"\n  Overall score improvement (no plateau):   {total_improvement_r1:+.2f}")
    print(f"  Overall score improvement (with plateau): {total_improvement_r2:+.2f}")
    print(f"  Adaptation gap (plateau scenario):        {adaptation_delta:+.2f}")

    print(f"\n  Multi-agent plateau signals detected: "
          f"{[s.signal_type for s in ma_r2.adaptation_signals]}")
    print(f"  Multi-agent conflicts resolved: "
          f"{ma_r2.conflicts_resolved or ['none']}")
    print(f"  Baseline plateau response: "
          f"{'mentions change' if 'change' in baseline_r2['response'].lower() else 'generic advice only'}")

    print("\n  [Evaluation] ✓ Complete")
    return {
        "baseline_r1": baseline_scores_r1,
        "multiagent_r1": ma_scores_r1,
        "baseline_r2": baseline_scores_r2,
        "multiagent_r2": ma_scores_r2,
    }


if __name__ == "__main__":
    results = run_evaluation()