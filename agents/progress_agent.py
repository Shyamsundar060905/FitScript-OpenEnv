"""
Progress Agent v2.

Changes from v1:
  - Uses statistical plateau detector (utils.plateau) instead of raw threshold.
  - Emits observability events with plateau status + confidence.
  - Generates signals based on *trend status* (plateau, reversing,
    overshooting) rather than binary plateau/non-plateau.
  - All rule-based signals are authoritative — LLM is only called for
    descriptive reasoning when no rule fires.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call, parse_json_response
from memory.long_term import load_profile
from memory.episodic import (
    get_recent_logs, detect_weight_plateau, log_adaptation_event,
)
from schemas import UserProfile, AdaptationSignal, AgentMessage
from utils.observability import agent_span
from utils.sanitize import sanitize_user_text


SYSTEM_PROMPT = """You are the Progress Agent in a multi-agent fitness AI system.
You analyze user progress data and identify patterns. You provide clear,
evidence-based adaptation signals. Respond with valid JSON only.
All numeric values must be plain numbers.
"""


def detect_workout_adherence(user_id: str, days: int = 14) -> dict:
    logs = get_recent_logs(user_id, days=days)
    if not logs:
        return {"adherence_pct": 0, "completed": 0, "total_logged": 0,
                "avg_difficulty_rating": None}
    completed = sum(1 for l in logs if l["workout_completed"])
    ratings = [l["workout_rating"] for l in logs if l["workout_rating"] is not None]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
    return {
        "adherence_pct": round(completed / len(logs) * 100),
        "completed": completed,
        "total_logged": len(logs),
        "avg_difficulty_rating": avg_rating,
    }


def analyze_progress(profile: UserProfile) -> list[AdaptationSignal]:
    """
    Statistical + rule-based progress analysis.
    Rule-based signals are authoritative; LLM is only used for a progress
    summary when no rules fire.
    """
    plateau_data = detect_weight_plateau(profile.user_id, goal=profile.goal)
    adherence    = detect_workout_adherence(profile.user_id)
    recent_logs  = get_recent_logs(profile.user_id, days=30)

    forced_signals: list[AdaptationSignal] = []

    # ── Rule 1: Statistical plateau during active goal ───────────────────────
    status = plateau_data["status"]
    conf = plateau_data["confidence"]

    if status == "plateau" and profile.goal in ("weight_loss", "muscle_gain") and conf >= 0.5:
        severity = "high" if (profile.goal == "weight_loss" and conf > 0.7) else "medium"
        forced_signals.append(AdaptationSignal(
            user_id=profile.user_id,
            signal_type="plateau",
            severity=severity,
            description=(
                f"Weight trend is flat (slope {plateau_data['slope_kg_per_week']:+.2f} kg/week "
                f"over {plateau_data['data_points']} days, confidence {conf:.2f}) "
                f"despite {profile.goal} goal."
            ),
            recommended_action=(
                "Increase training volume by 10%, adjust caloric intake by "
                f"{'+200 kcal' if profile.goal == 'muscle_gain' else '-200 kcal'}, "
                "and diversify rep ranges."
            ),
            data_points={
                "slope_kg_per_week": plateau_data["slope_kg_per_week"],
                "confidence": conf,
                "data_points": plateau_data["data_points"],
                "status": status,
            },
        ))

    # ── Rule 2: Reversing trend — serious, always high severity ──────────────
    if status == "reversing" and conf >= 0.5:
        forced_signals.append(AdaptationSignal(
            user_id=profile.user_id,
            signal_type="plateau",   # closest enum match
            severity="high",
            description=(
                f"Weight is trending OPPOSITE to {profile.goal} goal "
                f"(slope {plateau_data['slope_kg_per_week']:+.2f} kg/week)."
            ),
            recommended_action=(
                "Review caloric intake accuracy. "
                f"{'Reduce calories by 300' if profile.goal == 'weight_loss' else 'Increase calories by 300'} "
                "kcal/day and re-evaluate in 2 weeks."
            ),
            data_points={
                "slope_kg_per_week": plateau_data["slope_kg_per_week"],
                "confidence": conf,
                "status": status,
            },
        ))

    # ── Rule 3: Overshooting — too fast, safety concern ──────────────────────
    if status == "overshooting" and conf >= 0.5:
        forced_signals.append(AdaptationSignal(
            user_id=profile.user_id,
            signal_type="plateau",
            severity="medium",
            description=(
                f"Rate of change is outside healthy range "
                f"(slope {plateau_data['slope_kg_per_week']:+.2f} kg/week, "
                f"healthy range {plateau_data['expected_slope_range']})."
            ),
            recommended_action=(
                "Moderate the rate of change — losing/gaining too fast risks "
                "muscle loss or excessive fat gain. Aim for the midpoint of "
                "the healthy range."
            ),
            data_points={
                "slope_kg_per_week": plateau_data["slope_kg_per_week"],
                "expected_range": plateau_data["expected_slope_range"],
                "confidence": conf,
            },
        ))

    # ── Rule 4: Low adherence ────────────────────────────────────────────────
    if adherence["total_logged"] >= 5 and adherence["adherence_pct"] < 60:
        forced_signals.append(AdaptationSignal(
            user_id=profile.user_id,
            signal_type="schedule_change",
            severity="medium",
            description=(
                f"Workout adherence is {adherence['adherence_pct']}% "
                f"({adherence['completed']}/{adherence['total_logged']} sessions)."
            ),
            recommended_action=(
                "Reduce sessions per week by 1 — consistency beats frequency. "
                "Identify the top blocker (time, energy, motivation) and adjust."
            ),
            data_points={
                "adherence_pct": adherence["adherence_pct"],
                "total_logged": adherence["total_logged"],
            },
        ))

    # ── Rule 5: Consistent low ratings → overtraining ────────────────────────
    if adherence["avg_difficulty_rating"] is not None and \
       len([l for l in recent_logs if l["workout_rating"] is not None]) >= 4 and \
       adherence["avg_difficulty_rating"] <= 2.0:
        forced_signals.append(AdaptationSignal(
            user_id=profile.user_id,
            signal_type="overtraining",
            severity="medium",
            description=(
                f"Average workout difficulty rating is "
                f"{adherence['avg_difficulty_rating']}/5 — consistently low, "
                "suggesting fatigue accumulation or undertraining."
            ),
            recommended_action="Add a deload week with 50% reduced volume.",
            data_points={"avg_rating": adherence["avg_difficulty_rating"]},
        ))

    # ── Log and return ───────────────────────────────────────────────────────
    if forced_signals:
        for s in forced_signals:
            log_adaptation_event(
                profile.user_id, s.signal_type, s.description, s.recommended_action
            )
        return forced_signals

    # ── No rule fired — generate a positive progress signal ──────────────────
    # Use LLM only for the descriptive summary, since no actual decision
    # depends on it.
    try:
        prompt = f"""Write a brief positive progress note for this user:
Goal: {profile.goal} | Fitness level: {profile.fitness_level}
Trend status: {status}
Slope: {plateau_data['slope_kg_per_week']:+.2f} kg/week
Adherence: {adherence['adherence_pct']}%
Data points: {plateau_data['data_points']}

Return ONLY a JSON object:
{{
  "description": "one sentence about what is going well",
  "recommended_action": "one sentence about what to continue or tweak"
}}
"""
        response = llm_call(SYSTEM_PROMPT, prompt, json_mode=True)
        data = parse_json_response(response)
        desc = sanitize_user_text(data.get("description", "Continue current plan"), max_length=300)
        action = sanitize_user_text(data.get("recommended_action", "Maintain consistency"), max_length=300)
    except Exception:
        desc = f"Trend is {status}; continue current approach."
        action = "Maintain consistency with sessions and nutrition."

    return [AdaptationSignal(
        user_id=profile.user_id,
        signal_type="progress",
        severity="low",
        description=desc,
        recommended_action=action,
        data_points={
            "slope_kg_per_week": plateau_data["slope_kg_per_week"],
            "confidence": plateau_data["confidence"],
            "adherence_pct": adherence["adherence_pct"],
            "status": status,
        },
    )]


def run(user_id: str) -> AgentMessage:
    profile = load_profile(user_id)
    if not profile:
        return AgentMessage(
            from_agent="progress", to_agent="orchestrator",
            message_type="conflict", payload={}, confidence=0.0,
            reasoning=f"No profile found for {user_id}",
        )

    with agent_span("progress", user_id) as span:
        signals = analyze_progress(profile)
        span["metrics"]["signal_count"] = len(signals)
        span["metrics"]["severities"] = [s.severity for s in signals]

    high_severity = [s for s in signals if s.severity == "high"]

    return AgentMessage(
        from_agent="progress", to_agent="orchestrator", message_type="signal",
        payload={
            "signals": [s.model_dump() for s in signals],
            "needs_replan": len(high_severity) > 0,
            "signal_count": len(signals),
        },
        confidence=0.85,
        reasoning=(
            f"Detected {len(signals)} signal(s). "
            + ("Recommending replan." if high_severity else "No major adaptations needed.")
        ),
    )


# Synthetic data for demo/testing
def seed_test_data(user_id: str, weeks: int = 3):
    from memory.episodic import log_progress
    from schemas import ProgressLog
    from datetime import datetime as _dt, timedelta as _td

    base_weight = 78.0
    base_date = _dt.now() - _td(days=weeks * 7)
    for day in range(weeks * 7):
        current_date = base_date + _td(days=day)
        if day < 7:
            weight = base_weight - (day * 0.1)
        else:
            weight = base_weight - 0.7 + (0.1 * (day % 3 - 1))
        log_progress(ProgressLog(
            user_id=user_id,
            date=current_date.strftime("%Y-%m-%d"),
            weight_kg=round(weight, 1),
            workout_completed=(day % 7 not in [2, 6]),
            workout_rating=3 + (day % 2),
            calories_eaten=2200 + (day % 3) * 100,
            notes="Synthetic test data",
        ))