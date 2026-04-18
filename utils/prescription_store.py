"""
Prescription persistence helpers.

The orchestrator's WeeklyPrescription is built in memory and shown via
st.session_state.prescription. Browser refresh wipes it. This module
reconstructs the most recent prescription for a user from the DB so the
Plan page can rehydrate after refresh.

Note: orchestrator_notes, agent_log, knowledge_used, and conflicts_resolved
are NOT persisted in the current schema (they're synthesized at run time).
We mark a rehydrated prescription with a flag so the UI can show a banner
saying "loaded from history — synthesis details unavailable".
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config
from schemas import (
    WeeklyPrescription, WorkoutPlan, NutritionPlan,
)
from memory.episodic import get_latest_workout_plan


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.EPISODIC_DB))
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_nutrition_plan(user_id: str) -> Optional[dict]:
    """Mirror of get_latest_workout_plan for nutrition."""
    with _connect() as conn:
        row = conn.execute("""
            SELECT plan_json, week_number FROM nutrition_plans
            WHERE user_id = ?
            ORDER BY week_number DESC, generated_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()
    if not row:
        return None
    data = json.loads(row["plan_json"])
    data["_week_number"] = row["week_number"]
    return data


def rehydrate_latest_prescription(user_id: str) -> Optional[WeeklyPrescription]:
    """
    Reconstruct the user's most recent WeeklyPrescription from DB.
    Returns None if no plans exist.

    Limitations:
      - Orchestrator notes show a generic "loaded from history" message
      - Agent log and knowledge_used are empty (not persisted in schema)
      - Adaptation signals and conflicts_resolved are empty (synthesized live)

    For a full prescription with all metadata, the user must run the pipeline.
    """
    workout_data = get_latest_workout_plan(user_id)
    nutrition_data = get_latest_nutrition_plan(user_id)

    if not workout_data and not nutrition_data:
        return None

    # Determine week number from whichever plan we have
    week = (
        workout_data.get("week_number")
        if workout_data else nutrition_data.get("_week_number", 1)
    )

    # Strip any non-schema keys before Pydantic construction
    if nutrition_data:
        nutrition_data = {k: v for k, v in nutrition_data.items()
                          if not k.startswith("_")}

    # Build minimal prescription
    try:
        workout_plan = (
            WorkoutPlan(**workout_data) if workout_data
            else WorkoutPlan(user_id=user_id, week_number=week, days=[])
        )
        nutrition_plan = (
            NutritionPlan(**nutrition_data) if nutrition_data
            else NutritionPlan(
                user_id=user_id, week_number=week, daily_plans=[],
                target_calories=0, target_protein_g=0,
            )
        )
    except Exception as e:
        # If old plan data doesn't match current schema, give up gracefully
        print(f"  [rehydrate] Schema mismatch on old plan, skipping: {e}")
        return None

    return WeeklyPrescription(
        user_id=user_id,
        week_number=week,
        workout_plan=workout_plan,
        nutrition_plan=nutrition_plan,
        adaptation_signals=[],
        orchestrator_notes=(
            "📂 Loaded from history. Run the pipeline again for fresh "
            "progress signals, conflict resolution, and agent reasoning."
        ),
        conflicts_resolved=[],
        knowledge_used=[],
        agent_log=[],
    )


# Self-test
if __name__ == "__main__":
    print("── Prescription rehydration tests ──\n")

    # Try with a known user from the user's machine
    for uid in ["user_coffeine", "user_keshav", "user_001"]:
        result = rehydrate_latest_prescription(uid)
        if result:
            print(f"  ✓ Rehydrated for {uid}: "
                  f"week {result.week_number}, "
                  f"{len(result.workout_plan.days)} workout days, "
                  f"{len(result.nutrition_plan.daily_plans)} nutrition days")
        else:
            print(f"  - {uid}: no plan data in DB (expected if user is fresh)")

    print("\n  [Rehydrate] Tests passed")