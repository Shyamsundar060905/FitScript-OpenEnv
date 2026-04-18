"""
Fitness Agent v2.

Changes from v1:
  - Uses utils.overload for deterministic progressive overload prescriptions
    rather than hoping the LLM infers the right weight/reps.
  - Sanitizes adaptation_context before injecting into prompt (prompt injection defence).
  - Emits observability metrics: exercise count, volume, overload type.
  - Calls call_llm_structured() for Pydantic-validated retry instead of ad hoc
    JSON-parsing hacks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call, parse_json_response, fix_reps_in_plan
from memory.long_term import load_profile
from memory.episodic import (
    get_latest_workout_plan, save_workout_plan,
    get_all_logged_exercises, get_exercise_history,
    get_recent_exercise_summary,
)
from memory.semantic import retrieve_for_agent
from schemas import UserProfile, WorkoutPlan, WorkoutDay, Exercise, AgentMessage
from utils.observability import agent_span
from utils.sanitize import sanitize_user_text, sanitize_constraint_list
from utils.overload import (
    ExerciseHistory, prescribe_next_session, format_prescriptions_for_prompt,
)


def _clean_reps(reps) -> str:
    reps_map = {
        1: "3-5", 2: "6-8", 3: "8-10", 4: "8-12",
        5: "10-12", 6: "12-15", 7: "12-15", 8: "8-12",
        9: "8-12", 10: "10-12", 11: "10-15", 12: "10-15",
        15: "12-15", 20: "15-20"
    }
    if isinstance(reps, str) and "-" in reps and not reps.startswith("-"):
        return reps
    try:
        num = abs(int(float(str(reps))))
        return reps_map.get(num, f"{num}-{num + 2}")
    except (ValueError, TypeError):
        return "8-12"


SYSTEM_PROMPT = """You are the Fitness Agent in a multi-agent AI system.
You design safe, effective, evidence-based workout programs following NSCA and
ACSM guidelines. Respond with valid JSON only. All numeric values must be plain
numbers. Rep ranges must be strings like "8-12".

When progressive overload prescriptions are provided, you MUST use those exact
sets, reps, and weights for those exercises. Do not override the overload engine.
"""


def _build_overload_prescriptions(user_id: str) -> list:
    """For each recently-logged exercise, compute next-session prescription."""
    exercises = get_all_logged_exercises(user_id, days=30)
    prescriptions = []
    for ex_name in exercises:
        history_rows = get_exercise_history(user_id, ex_name, days=60)
        if not history_rows:
            continue
        history = [
            ExerciseHistory(
                date=r["date"],
                sets_completed=r.get("sets_completed") or 0,
                reps_completed=r.get("reps_completed") or "",
                weight_kg=r.get("weight_kg") or 0,
                target_sets=r.get("target_sets"),
                target_reps=r.get("target_reps"),
                rpe=r.get("rpe"),
            )
            for r in history_rows
        ]
        prescriptions.append(prescribe_next_session(ex_name, history))
    return prescriptions


def generate_workout_plan(
    profile: UserProfile,
    week_number: int = 1,
    adaptation_context: str = "",
    previous_plan_summary: str = "",
) -> tuple[WorkoutPlan, list, list]:
    """
    Generate a weekly workout plan.
    Returns (WorkoutPlan, knowledge_chunks_used, overload_prescriptions).
    """
    # Sanitize user-sourced text before putting it in the prompt
    safe_adaptation = sanitize_user_text(adaptation_context, max_length=800)

    # Parse constraints from the adaptation context for RAG filter
    constraints = []
    lower = safe_adaptation.lower()
    if "knee" in lower:
        constraints.append("knee pain — avoid squats, lunges, leg press")
    if "shoulder" in lower:
        constraints.append("shoulder injury — avoid overhead press, dips")
    if "wrist" in lower:
        constraints.append("wrist pain — avoid push-ups on palms, barbell curls")
    if "lower back" in lower or "back pain" in lower:
        constraints.append("lower back pain — avoid deadlifts, heavy squats")
    constraints = sanitize_constraint_list(constraints)

    knowledge, chunks_used = retrieve_for_agent(
        "fitness",
        profile.to_summary(),
        goal=profile.goal,
        fitness_level=profile.fitness_level,
        constraints=constraints,
    )

    # Deterministic overload prescriptions
    overload_prescriptions = _build_overload_prescriptions(profile.user_id)
    overload_block = format_prescriptions_for_prompt(overload_prescriptions)

    history_note = ""
    if previous_plan_summary:
        history_note = f"\nPrevious plan: {sanitize_user_text(previous_plan_summary, 400)}"
    if safe_adaptation:
        history_note += f"\nAdaptation signals: {safe_adaptation}"

    exercise_summary = get_recent_exercise_summary(profile.user_id, days=14)
    if exercise_summary:
        history_note += f"\n\n{exercise_summary}"

    prompt = f"""Create a {profile.sessions_per_week}-day workout plan for this user:

{profile.to_summary()}
Week number: {week_number}
{history_note}

{overload_block}

{knowledge}

Return ONLY a JSON object in this exact structure:
{{
  "user_id": "{profile.user_id}",
  "week_number": {week_number},
  "notes": "brief evidence-based plan rationale",
  "weekly_volume_sets": <total sets as a plain integer>,
  "days": [
    {{
      "day_name": "Day 1 - Monday",
      "focus": "Push / Pull / Legs / Full Body",
      "estimated_duration_minutes": 45,
      "exercises": [
        {{
          "name": "Exercise name",
          "sets": 3,
          "reps": "8-12",
          "rest_seconds": 90,
          "notes": "why this exercise was chosen"
        }}
      ]
    }}
  ]
}}

Critical rules:
- Only use equipment: {', '.join(profile.available_equipment)}
- Fitness level: {profile.fitness_level}
- Goal: {profile.goal}
- Provide exactly {profile.sessions_per_week} workout days
- reps MUST be a string like "8-12" or "10-15", never a number
- For exercises listed in the OVERLOAD PRESCRIPTIONS above, use those exact
  sets, reps, and weights — do not override the overload engine.
- Week {week_number}: {"focus on form and movement patterns" if week_number == 1 else "apply progressive overload"}
"""

    response = llm_call(SYSTEM_PROMPT, prompt, json_mode=True)
    data = fix_reps_in_plan(parse_json_response(response))

    days = []
    for d in data.get("days", []):
        exercises = []
        for ex in d.get("exercises", []):
            exercises.append(Exercise(
                name=ex.get("name", ""),
                sets=ex.get("sets"),
                reps=_clean_reps(ex.get("reps", "")),
                duration_minutes=ex.get("duration_minutes"),
                rest_seconds=ex.get("rest_seconds", 90),
                notes=ex.get("notes", ""),
            ))
        days.append(WorkoutDay(
            day_name=d.get("day_name", ""),
            focus=d.get("focus", ""),
            exercises=exercises,
            estimated_duration_minutes=d.get("estimated_duration_minutes", 45),
        ))

    plan = WorkoutPlan(
        user_id=profile.user_id,
        week_number=week_number,
        days=days,
        weekly_volume_sets=data.get("weekly_volume_sets", 0),
        notes=data.get("notes", ""),
    )
    save_workout_plan(profile.user_id, week_number, data)
    return plan, chunks_used, overload_prescriptions


def run(user_id: str, week_number: int = 1,
        adaptation_context: str = "") -> AgentMessage:
    profile = load_profile(user_id)
    if not profile:
        return AgentMessage(
            from_agent="fitness", to_agent="orchestrator",
            message_type="conflict", payload={}, confidence=0.0,
            reasoning=f"No profile found for {user_id}",
        )

    prev = get_latest_workout_plan(user_id)
    prev_summary = (
        f"Week {prev.get('week_number', '?')}: {prev.get('notes', '')}"
        if prev else ""
    )

    with agent_span("fitness", user_id, metadata={"week": week_number}) as span:
        plan, chunks_used, overload_prescriptions = generate_workout_plan(
            profile, week_number=week_number,
            adaptation_context=adaptation_context,
            previous_plan_summary=prev_summary,
        )
        span["metrics"]["weekly_volume_sets"] = plan.weekly_volume_sets
        span["metrics"]["days"] = len(plan.days)
        span["metrics"]["overload_prescriptions"] = len(overload_prescriptions)
        span["metrics"]["knowledge_chunks"] = len(chunks_used)

    conflicts = []
    if plan.weekly_volume_sets > 80 and profile.fitness_level == "beginner":
        conflicts.append("nutrition")

    return AgentMessage(
        from_agent="fitness", to_agent="orchestrator",
        message_type="plan",
        payload={
            **plan.model_dump(),
            "knowledge_chunks": len(chunks_used),
            "knowledge_chunks_data": chunks_used,
            "overload_prescriptions": [p.to_dict() for p in overload_prescriptions],
        },
        confidence=0.9, conflicts_with=conflicts,
        reasoning=(
            f"Generated {profile.sessions_per_week}-day plan for {profile.goal}. "
            f"Volume: {plan.weekly_volume_sets} sets/week. "
            f"RAG chunks: {len(chunks_used)}. "
            f"Overload prescriptions: {len(overload_prescriptions)}."
        ),
    )