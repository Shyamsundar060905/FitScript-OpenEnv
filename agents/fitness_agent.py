"""
Fitness Agent — generates weekly workout plans from user profile and history.
Uses filtered RAG retrieval for evidence-based, personalized recommendations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from memory.episodic import get_recent_exercise_summary
from llm.router import llm_call, parse_json_response
from memory.long_term import load_profile
from memory.episodic import get_latest_workout_plan, save_workout_plan
from memory.semantic import retrieve_for_agent
from schemas import UserProfile, WorkoutPlan, WorkoutDay, Exercise, AgentMessage

def _clean_reps(reps) -> str:
    """Convert any reps value to a proper string range like '8-12'."""
    reps_map = {
        1: "3-5", 2: "6-8", 3: "8-10", 4: "8-12",
        5: "10-12", 6: "12-15", 7: "12-15", 8: "8-12",
        9: "8-12", 10: "10-12", 11: "10-15", 12: "10-15",
        15: "12-15", 20: "15-20"
    }
    # Already a proper string range like "8-12"
    if isinstance(reps, str) and "-" in reps and not reps.startswith("-"):
        return reps
    # Convert to number and map
    try:
        num = abs(int(float(str(reps))))
        return reps_map.get(num, f"{num}-{num+2}")
    except (ValueError, TypeError):
        return "8-12"  # safe default

SYSTEM_PROMPT = """You are the Fitness Agent in a multi-agent AI system.
You are an expert certified personal trainer with knowledge of NSCA and ACSM guidelines.
You design safe, effective, evidence-based workout programs.
You always respond with valid JSON only. No explanations, no markdown, no formulas.
All numeric values must be plain numbers, never math expressions.
Rep ranges must be strings like "8-12" not numbers.
"""


def generate_workout_plan(profile: UserProfile, week_number: int = 1,
                          adaptation_context: str = "",
                          previous_plan_summary: str = "") -> tuple:
    """
    Generate a weekly workout plan.
    Returns (WorkoutPlan, knowledge_chunks_used)
    """
    constraints = []
    if "knee pain" in adaptation_context.lower():
        constraints.append("knee pain — avoid squats, lunges, leg press")
    if "shoulder" in adaptation_context.lower():
        constraints.append("shoulder injury — avoid overhead press, dips")
    if "wrist" in adaptation_context.lower():
        constraints.append("wrist pain — avoid push-ups on palms, barbell curls")
    if "lower back" in adaptation_context.lower():
        constraints.append("lower back pain — avoid deadlifts, heavy squats")

    knowledge, chunks_used = retrieve_for_agent(
        "fitness",
        profile.to_summary(),
        goal=profile.goal,
        fitness_level=profile.fitness_level,
        constraints=constraints
    )

    history_note = ""
    if previous_plan_summary:
        history_note = f"\nPrevious plan: {previous_plan_summary}"
    if adaptation_context:
        history_note += f"\nAdaptation signals: {adaptation_context}"
    # Get progressive overload history
    exercise_history = get_recent_exercise_summary(profile.user_id, days=14)
    if exercise_history:
        history_note += f"\n\n{exercise_history}"
    prompt = f"""Create a {profile.sessions_per_week}-day workout plan for this user:

{profile.to_summary()}
Week number: {week_number}
{history_note}

{knowledge}

Return ONLY a JSON object in this exact structure:
{{
  "user_id": "{profile.user_id}",
  "week_number": {week_number},
  "notes": "brief evidence-based plan rationale",
  "weekly_volume_sets": <total sets as a plain integer like 48>,
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
- All numeric values must be plain numbers
- Week {week_number}: {"focus on form and movement patterns" if week_number == 1
  else "apply progressive overload from previous week"}
"""

    response = llm_call(SYSTEM_PROMPT, prompt, json_mode=False)
    from llm.router import fix_reps_in_plan
    data = fix_reps_in_plan(parse_json_response(response))
    # Debug — remove after fix confirmed
    #if data.get("days"):
    #    sample_reps = data["days"][0]["exercises"][0].get("reps")
    #    print(f"  [DEBUG] Sample reps type: {type(sample_reps)} value: {sample_reps}")
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
                notes=ex.get("notes", "")
            ))
        days.append(WorkoutDay(
            day_name=d.get("day_name", ""),
            focus=d.get("focus", ""),
            exercises=exercises,
            estimated_duration_minutes=d.get("estimated_duration_minutes", 45)
        ))

    plan = WorkoutPlan(
        user_id=profile.user_id,
        week_number=week_number,
        days=days,
        weekly_volume_sets=data.get("weekly_volume_sets", 0),
        notes=data.get("notes", "")
    )
    save_workout_plan(profile.user_id, week_number, data)
    return plan, chunks_used


def format_plan_for_display(plan: WorkoutPlan) -> str:
    lines = [f"\n{'='*50}",
             f"WORKOUT PLAN — Week {plan.week_number}",
             f"Volume: {plan.weekly_volume_sets} sets | {plan.notes}",
             '='*50]
    for day in plan.days:
        lines.append(f"\n📅 {day.day_name} | {day.focus} (~{day.estimated_duration_minutes} min)")
        lines.append("-" * 40)
        for ex in day.exercises:
            reps_display = str(ex.reps).lstrip('-').replace('.0', '') if ex.reps else '?'
            if ex.duration_minutes:
                lines.append(f"  • {ex.name} — {ex.duration_minutes} min")
            else:
                lines.append(f"  • {ex.name} — {ex.sets}x{reps_display} | rest {ex.rest_seconds}s")
            if ex.notes:
                lines.append(f"    ↳ {ex.notes}")
    return "\n".join(lines)


def run(user_id: str, week_number: int = 1,
        adaptation_context: str = "") -> AgentMessage:
    profile = load_profile(user_id)
    if not profile:
        return AgentMessage(
            from_agent="fitness", to_agent="orchestrator",
            message_type="conflict", payload={}, confidence=0.0,
            reasoning=f"No profile found for {user_id}"
        )

    prev = get_latest_workout_plan(user_id)
    prev_summary = (f"Week {prev.get('week_number','?')}: {prev.get('notes','')}"
                    if prev else "")

    plan, chunks_used = generate_workout_plan(
        profile, week_number=week_number,
        adaptation_context=adaptation_context,
        previous_plan_summary=prev_summary
    )

    conflicts = []
    if plan.weekly_volume_sets > 80 and profile.fitness_level == "beginner":
        conflicts.append("nutrition")

    return AgentMessage(
        from_agent="fitness", to_agent="orchestrator",
        message_type="plan",
        payload={**plan.model_dump(),
                 "knowledge_chunks": len(chunks_used),
                 "knowledge_chunks_data": chunks_used},
        confidence=0.9, conflicts_with=conflicts,
        reasoning=(f"Generated {profile.sessions_per_week}-day plan for "
                   f"{profile.goal}. Volume: {plan.weekly_volume_sets} sets/week. "
                   f"RAG retrieved {len(chunks_used)} knowledge chunks.")
    )


if __name__ == "__main__":
    from memory.long_term import create_sample_user
    print("\n── Test: Generate workout plan with filtered RAG ──")
    profile = create_sample_user()
    plan, chunks = generate_workout_plan(profile, week_number=1)
    print(f"  Knowledge chunks used: {len(chunks)}")
    for c in chunks:
        print(f"  - [{c.get('relevance', 0):.2f}] {c['content'][:80]}...")
    print(format_plan_for_display(plan))
    print("\n  [Fitness Agent v2] ✓ Test passed")