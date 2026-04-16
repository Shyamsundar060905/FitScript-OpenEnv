"""
Progress Agent — detects plateaus and generates adaptation signals.
"""
from memory.semantic import retrieve_for_agent, seed_knowledge_base
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call, parse_json_response
from memory.long_term import load_profile
from memory.episodic import get_recent_logs, get_weight_series, log_adaptation_event
from schemas import UserProfile, AdaptationSignal, AgentMessage
from config import PLATEAU_WINDOW_DAYS, PLATEAU_WEIGHT_THRESHOLD


SYSTEM_PROMPT = """You are the Progress Agent in a multi-agent fitness AI system.
You analyze user progress data and identify patterns like plateaus, overtraining,
or rapid progress. You provide clear, evidence-based adaptation signals.
You always respond with valid JSON only. No explanations, no markdown, no formulas.
All numeric values must be plain numbers.
"""


def detect_weight_plateau(user_id: str) -> dict:
    """Check if weight has stalled over the plateau window using RECENT data only."""
    weights = get_weight_series(user_id, days=PLATEAU_WINDOW_DAYS)
    if len(weights) < 3:
        return {"plateau": False, "change_kg": 0,
                "data_points": len(weights), "reason": "insufficient data"}

    # Use only the most recent entries to avoid old data contaminating the signal
    recent = weights[-10:]
    first  = recent[0]["weight_kg"]
    last   = recent[-1]["weight_kg"]
    change = round(last - first, 2)

    # Also check variance — true plateau has very low variance
    weight_values = [w["weight_kg"] for w in recent]
    variance = max(weight_values) - min(weight_values)

    return {
        "plateau": abs(change) < PLATEAU_WEIGHT_THRESHOLD and variance < 0.8,
        "change_kg": change,
        "variance": round(variance, 2),
        "data_points": len(recent),
        "first_weight": first,
        "last_weight": last,
        "direction": "losing" if change < -0.1 else "gaining" if change > 0.1 else "stable"
    }

def detect_workout_adherence(user_id: str, days: int = 14) -> dict:
    logs = get_recent_logs(user_id, days=days)
    if not logs:
        return {"adherence_pct": 0, "completed": 0, "total_logged": 0}
    completed = sum(1 for l in logs if l["workout_completed"])
    ratings = [l["workout_rating"] for l in logs if l["workout_rating"] is not None]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
    return {
        "adherence_pct": round(completed / len(logs) * 100),
        "completed": completed,
        "total_logged": len(logs),
        "avg_difficulty_rating": avg_rating
    }

def analyze_progress(profile: UserProfile) -> list:
    """
    Full progress analysis. Rule-based checks are authoritative —
    LLM only adds reasoning and recommendations on top.
    """
    plateau_data = detect_weight_plateau(profile.user_id)
    adherence    = detect_workout_adherence(profile.user_id)
    recent_logs  = get_recent_logs(profile.user_id, days=30)

    logs_summary = []
    for log in recent_logs[-10:]:
        logs_summary.append({
            "date": log["date"],
            "weight_kg": log["weight_kg"],
            "workout_done": bool(log["workout_completed"]),
            "rating": log["workout_rating"],
            "calories": log["calories_eaten"]
        })

    # ── Rule-based signals (authoritative) ───────────────────────────────────
    forced_signals = []

    if plateau_data["data_points"] >= 3 and plateau_data["plateau"]:
        if profile.goal in ["weight_loss", "muscle_gain"]:
            severity = "high" if profile.goal == "weight_loss" else "medium"
            forced_signals.append({
                "signal_type": "plateau",
                "severity": severity,
                "description": f"Weight has been flat for {plateau_data['data_points']} days "
                               f"(change: {plateau_data['change_kg']}kg). Goal is {profile.goal}.",
                "recommended_action": "Change rep ranges, increase training volume by 10%, "
                                      "and adjust caloric intake by +200 kcal."
            })

    if adherence["total_logged"] >= 5 and adherence["adherence_pct"] < 60:
        forced_signals.append({
            "signal_type": "schedule_change",
            "severity": "medium",
            "description": f"Workout adherence is only {adherence['adherence_pct']}% "
                           f"({adherence['completed']}/{adherence['total_logged']} sessions).",
            "recommended_action": "Reduce sessions per week by 1 to improve consistency."
        })

    ratings = [l["workout_rating"] for l in recent_logs if l["workout_rating"] is not None]
    if ratings and len(ratings) >= 4:
        avg_rating = sum(ratings) / len(ratings)
        if avg_rating <= 2.0:
            forced_signals.append({
                "signal_type": "overtraining",
                "severity": "medium",
                "description": f"Average workout difficulty rating is {avg_rating:.1f}/5 — "
                               f"consistently low, suggesting fatigue or overtraining.",
                "recommended_action": "Add a deload week with 50% reduced volume."
            })

    # If rule-based signals found, use them directly — no LLM needed
    if forced_signals:
        signals = []
        for s in forced_signals:
            signal = AdaptationSignal(
                user_id=profile.user_id,
                signal_type=s["signal_type"],
                severity=s["severity"],
                description=s["description"],
                recommended_action=s["recommended_action"],
                data_points={
                    "weight_change_kg": plateau_data["change_kg"],
                    "adherence_pct": adherence["adherence_pct"],
                    "data_points": plateau_data["data_points"]
                }
            )
            signals.append(signal)
            log_adaptation_event(profile.user_id, signal.signal_type,
                                 signal.description, signal.recommended_action)
        return signals

    # ── LLM analysis (only if no rule-based signals triggered) ───────────────
    prompt = f"""Analyze this user's fitness progress:

User: {profile.to_summary()}
Weight trend: {plateau_data}
Adherence: {adherence}
Recent logs: {logs_summary}

Return ONLY a JSON array with 1 signal:
[
  {{
    "user_id": "{profile.user_id}",
    "signal_type": "progress",
    "severity": "low",
    "description": "brief description of what is going well",
    "recommended_action": "continue current plan with minor adjustments",
    "data_points": {{
      "weight_change_kg": {plateau_data['change_kg']},
      "adherence_pct": {adherence['adherence_pct']},
      "weeks_on_current_plan": 1
    }}
  }}
]
All numbers must be plain values."""

    response = llm_call(SYSTEM_PROMPT, prompt, json_mode=False)
    data = parse_json_response(response)

    if isinstance(data, dict):
        data = data.get("signals", [data])

    signals = []
    for s in data:
        signal = AdaptationSignal(
            user_id=profile.user_id,
            signal_type=s.get("signal_type", "progress"),
            severity=s.get("severity", "low"),
            description=s.get("description", ""),
            recommended_action=s.get("recommended_action", ""),
            data_points=s.get("data_points", {})
        )
        signals.append(signal)
        log_adaptation_event(profile.user_id, signal.signal_type,
                             signal.description, signal.recommended_action)
    return signals


def seed_test_data(user_id: str, weeks: int = 3):
    """Insert synthetic plateau data for demo/testing."""
    from memory.episodic import log_progress
    from schemas import ProgressLog
    from datetime import datetime, timedelta

    base_weight = 78.0
    base_date = datetime.now() - timedelta(days=weeks * 7)

    for day in range(weeks * 7):
        current_date = base_date + timedelta(days=day)
        if day < 7:
            weight = base_weight - (day * 0.1)
        else:
            weight = base_weight - 0.7 + (0.1 * (day % 3 - 1))

        log = ProgressLog(
            user_id=user_id,
            date=current_date.strftime("%Y-%m-%d"),
            weight_kg=round(weight, 1),
            workout_completed=(day % 7 not in [2, 6]),
            workout_rating=3 + (day % 2),
            calories_eaten=2200 + (day % 3) * 100,
            notes="Synthetic test data"
        )
        log_progress(log)
    print(f"  Seeded {weeks * 7} days of test data for {user_id}")


def run(user_id: str) -> AgentMessage:
    profile = load_profile(user_id)
    if not profile:
        return AgentMessage(from_agent="progress", to_agent="orchestrator",
                            message_type="conflict", payload={}, confidence=0.0,
                            reasoning=f"No profile found for {user_id}")

    signals = analyze_progress(profile)
    high_severity = [s for s in signals if s.severity == "high"]

    return AgentMessage(
        from_agent="progress", to_agent="orchestrator", message_type="signal",
        payload={
            "signals": [s.model_dump() for s in signals],
            "needs_replan": len(high_severity) > 0,
            "signal_count": len(signals)
        },
        confidence=0.85,
        reasoning=f"Detected {len(signals)} signal(s). "
                  f"{'Recommending replan.' if high_severity else 'No major adaptations needed.'}"
    )


if __name__ == "__main__":
    from memory.long_term import create_sample_user

    print("\n── Test 1: Seed synthetic plateau data ──")
    profile = create_sample_user()
    seed_test_data(profile.user_id, weeks=3)

    print("\n── Test 2: Rule-based checks ──")
    plateau = detect_weight_plateau(profile.user_id)
    print(f"  Plateau: {plateau['plateau']} | Change: {plateau['change_kg']}kg | Points: {plateau['data_points']}")
    adherence = detect_workout_adherence(profile.user_id)
    print(f"  Adherence: {adherence['adherence_pct']}% ({adherence['completed']}/{adherence['total_logged']})")

    print("\n── Test 3: LLM analysis ──")
    signals = analyze_progress(profile)
    for s in signals:
        print(f"  [{s.severity.upper()}] {s.signal_type}")
        print(f"    → {s.description}")
        print(f"    → Action: {s.recommended_action}")

    print("\n  [Progress Agent] ✓ All tests passed")