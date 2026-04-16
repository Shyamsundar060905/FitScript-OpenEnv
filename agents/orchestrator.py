"""
Orchestrator — the brain of the multi-agent system.
Coordinates all agents, resolves conflicts, synthesizes the final prescription.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from datetime import datetime
from llm.router import llm_call, parse_json_response
from memory.long_term import load_profile
from memory.episodic import get_recent_logs
from schemas import AgentMessage, WeeklyPrescription
import agents.profile_agent   as profile_agent
import agents.fitness_agent   as fitness_agent
import agents.nutrition_agent as nutrition_agent
import agents.progress_agent  as progress_agent


# ── Conflict resolution rules ─────────────────────────────────────────────────

CONFLICT_RULES = [
    {
        "condition": lambda fit_msg, nut_msg, prog_msg: (
            any(s["signal_type"] == "plateau" and s["severity"] in ["medium","high"]
                for s in prog_msg.payload.get("signals", []))
            and fit_msg.payload.get("weekly_volume_sets", 0) < 40
        ),
        "action": "increase_volume",
        "description": "Plateau detected but training volume is low — increase workout volume"
    },
    {
        "condition": lambda fit_msg, nut_msg, prog_msg: ("fitness" in nut_msg.conflicts_with or nut_msg.payload.get("target_calories", 9999) < fit_msg.payload.get("weekly_volume_sets", 0) * 15),
        "action": "increase_calories",
        "description": "High training volume with insufficient calories — increase calorie target by 200"
    },
    {
        "condition": lambda fit_msg, nut_msg, prog_msg: (
            any(s["signal_type"] == "overtraining"
                for s in prog_msg.payload.get("signals", []))
        ),
        "action": "reduce_volume",
        "description": "Overtraining signal detected — reduce weekly volume by 20% and add recovery day"
    },
    {
        "condition": lambda fit_msg, nut_msg, prog_msg: (
            any(s["signal_type"] == "schedule_change"
                for s in prog_msg.payload.get("signals", []))
        ),
        "action": "reduce_frequency",
        "description": "Low adherence detected — reduce sessions per week by 1"
    },
]


def resolve_conflicts(fit_msg: AgentMessage,
                      nut_msg: AgentMessage,
                      prog_msg: AgentMessage) -> list:
    """
    Run each conflict rule and collect triggered resolutions.
    Returns list of resolution description strings.
    """
    triggered = []
    for rule in CONFLICT_RULES:
        try:
            if rule["condition"](fit_msg, nut_msg, prog_msg):
                triggered.append(rule["description"])
                print(f"  [Conflict] ⚡ {rule['description']}")
        except Exception:
            continue
    return triggered


def synthesize_with_llm(profile_msg: AgentMessage,
                         fit_msg: AgentMessage,
                         nut_msg: AgentMessage,
                         prog_msg: AgentMessage,
                         conflicts_resolved: list) -> str:
    """
    Ask the LLM to write a final synthesis note explaining the prescription.
    This becomes the orchestrator_notes field.
    """
    signals = prog_msg.payload.get("signals", [])
    signal_text = "; ".join(
        f"{s['signal_type']} ({s['severity']}): {s['description']}"
        for s in signals
    ) or "No significant signals"

    conflict_text = "; ".join(conflicts_resolved) or "No conflicts detected"

    prompt = f"""You are the Orchestrator of a multi-agent fitness AI system.
You have received plans from specialist agents. Write a brief 2-3 sentence
summary explaining this week's prescription for the user.

User goal: {profile_msg.payload.get('goal', 'unknown')}
Fitness plan: {fit_msg.reasoning}
Nutrition plan: {nut_msg.reasoning}
Progress signals: {signal_text}
Conflicts resolved: {conflict_text}

Write a friendly, motivating summary in second person (use "you/your").
Keep it under 60 words. Plain text only, no JSON."""

    return llm_call("You are a helpful fitness coach.", prompt, json_mode=False)


def run_pipeline(user_id: str, week_number: int = 1, constraint_context: str = "") -> WeeklyPrescription:
    """
    Full orchestration pipeline:
    1. Load profile
    2. Get progress signals
    3. Run fitness + nutrition agents (with adaptation context)
    4. Resolve conflicts
    5. Synthesize final prescription
    """
    print(f"\n{'='*55}")
    print(f"  ORCHESTRATOR — Week {week_number} | User: {user_id}")
    print(f"{'='*55}")

    # Step 1 — Profile
    print("\n  [Step 1] Loading profile...")
    profile_msg = profile_agent.run(user_id)
    profile = load_profile(user_id)

    # Step 2 — Progress signals (run first to inform other agents)
    print("\n  [Step 2] Analyzing progress...")
    prog_msg = progress_agent.run(user_id)
    signals = prog_msg.payload.get("signals", [])
    needs_replan = prog_msg.payload.get("needs_replan", False)

    # Build adaptation context string for other agents
    adaptation_context = ""
    if signals:
        adaptation_context = "; ".join(
            f"{s['signal_type']}: {s['recommended_action']}"
            for s in signals
        )
        print(f"  Adaptation context: {adaptation_context}")
    if constraint_context:
        adaptation_context = adaptation_context + "; " + constraint_context \
                             if adaptation_context else constraint_context
    # Step 3 — Fitness agent
    # Agent log — records decisions for UI display
    agent_log = []
    agent_log.append({
        "agent": "Profile Agent",
        "icon": "👤",
        "decision": f"Loaded profile for {profile.name}",
        "detail": profile.to_summary(),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

    signal_summary = (", ".join(f"{s['signal_type']} ({s['severity']})"
                                for s in signals)
                      if signals else "No issues detected")
    agent_log.append({
        "agent": "Progress Agent",
        "icon": "📊",
        "decision": signal_summary,
        "detail": adaptation_context or "Fresh start — no history to analyze",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

    # Step 3 — Fitness agent
    print("\n  [Step 3] Generating workout plan...")
    fit_msg = fitness_agent.run(user_id, week_number=week_number,
                                adaptation_context=adaptation_context)
    agent_log.append({
        "agent": "Fitness Agent",
        "icon": "💪",
        "decision": f"Generated {len(fit_msg.payload.get('days', []))} day plan, "
                    f"{fit_msg.payload.get('weekly_volume_sets', 0)} sets/week",
        "detail": fit_msg.reasoning,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

    # Step 4 — Nutrition agent
    print("\n  [Step 4] Generating nutrition plan...")
    calorie_adj = 200.0 if fit_msg.payload.get("weekly_volume_sets", 0) > 60 else 0.0
    nut_msg = nutrition_agent.run(user_id, week_number=week_number,
                                  calorie_adjustment=calorie_adj,
                                  adaptation_context=adaptation_context)
    agent_log.append({
        "agent": "Nutrition Agent",
        "icon": "🥗",
        "decision": f"{nut_msg.payload.get('target_calories', 0):.0f} kcal/day, "
                    f"{nut_msg.payload.get('target_protein_g', 0):.0f}g protein",
        "detail": nut_msg.reasoning,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

    # Step 5 — Conflict resolution
    print("\n  [Step 5] Resolving conflicts...")
    conflicts_resolved = resolve_conflicts(fit_msg, nut_msg, prog_msg)
    if not conflicts_resolved:
        print("  No conflicts detected")
    agent_log.append({
        "agent": "Conflict Resolver",
        "icon": "⚡",
        "decision": (f"Resolved: {conflicts_resolved[0]}"
                     if conflicts_resolved else "No conflicts detected"),
        "detail": "; ".join(conflicts_resolved) if conflicts_resolved else "All agents in agreement",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

    # Step 6 — Synthesize
    print("\n  [Step 6] Synthesizing prescription...")
    notes = synthesize_with_llm(profile_msg, fit_msg, nut_msg,
                                 prog_msg, conflicts_resolved)
    print(f"  Notes: {notes.strip()}")
    agent_log.append({
        "agent": "Orchestrator",
        "icon": "🧠",
        "decision": "Prescription synthesized",
        "detail": notes.strip(),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

    # Build final prescription
    from schemas import WorkoutPlan, NutritionPlan, AdaptationSignal
    exclude_keys = {"knowledge_chunks", "knowledge_chunks_data"}
    workout_plan   = WorkoutPlan(**{k: v for k, v in fit_msg.payload.items()
                                    if k not in exclude_keys})
    nutrition_plan = NutritionPlan(**{k: v for k, v in nut_msg.payload.items()
                                      if k not in exclude_keys})
    adaptation_signals = [AdaptationSignal(**s) for s in signals]

    # Collect knowledge chunks from both agents
    knowledge_used = []
    for msg in [fit_msg, nut_msg]:
        chunks = msg.payload.get("knowledge_chunks_data", [])
        if chunks:
            knowledge_used.extend(chunks)

    prescription = WeeklyPrescription(
        user_id=user_id,
        week_number=week_number,
        workout_plan=workout_plan,
        nutrition_plan=nutrition_plan,
        adaptation_signals=adaptation_signals,
        orchestrator_notes=notes.strip(),
        conflicts_resolved=conflicts_resolved,
        knowledge_used=knowledge_used,
        agent_log=agent_log
    )

    print(f"\n  ✓ Prescription ready — {len(workout_plan.days)} workout days, "
          f"{len(nutrition_plan.daily_plans)} nutrition days, "
          f"{len(adaptation_signals)} signal(s)")
    return prescription


def print_prescription(p: WeeklyPrescription):
    """Print a full summary of the prescription."""
    print(f"\n{'='*55}")
    print(f"  WEEKLY PRESCRIPTION — Week {p.week_number}")
    print(f"{'='*55}")
    print(f"\n📋 Orchestrator Notes:\n  {p.orchestrator_notes}")

    if p.conflicts_resolved:
        print(f"\n⚡ Conflicts Resolved:")
        for c in p.conflicts_resolved:
            print(f"  • {c}")

    if p.adaptation_signals:
        print(f"\n📊 Adaptation Signals:")
        for s in p.adaptation_signals:
            print(f"  [{s.severity.upper()}] {s.signal_type}: {s.description}")

    print(f"\n💪 Workout Plan — {p.workout_plan.weekly_volume_sets} sets/week")
    for day in p.workout_plan.days:
        print(f"  {day.day_name} | {day.focus} | {len(day.exercises)} exercises")

    print(f"\n🥗 Nutrition Plan — {p.nutrition_plan.target_calories} kcal/day")
    for day in p.nutrition_plan.daily_plans:
        print(f"  {day.day_name} | {day.total_calories:.0f} kcal | "
              f"P:{day.total_protein_g:.0f}g")

def demo_adaptation(user_id: str):
    """Demo showing week-over-week adaptation."""
    from memory.episodic import get_adaptation_history, clear_user_data, log_progress
    from schemas import ProgressLog
    from datetime import datetime, timedelta
    import time

    print("\n" + "="*55)
    print("  ADAPTATION DEMO — Week-over-Week Comparison")
    print("="*55)

    # Clean slate
    clear_user_data(user_id)
    print("  ✓ Cleared old test data for clean demo")

    # Week 1 — clean start, no plateau
    print("\n>>> WEEK 1 — Initial plan (no plateau data)")
    p1 = run_pipeline(user_id, week_number=1)

    # Seed 14 days of flat weight = plateau
    print("\n>>> Simulating 2 weeks of plateau...")
    for i in range(14):
        date = (datetime.now() - timedelta(days=14-i)).strftime("%Y-%m-%d")
        log_progress(ProgressLog(
            user_id=user_id,
            date=date,
            weight_kg=78.0,
            workout_completed=(i % 7 not in [2, 6]),
            workout_rating=2,
            calories_eaten=2100.0,
            notes="Plateau simulation"
        ))
    print("  Plateau data seeded — 14 days flat weight, low ratings")
    print("  Waiting 30 seconds to avoid rate limits...")
    time.sleep(30)

    # Week 2 — should detect plateau and adapt
    print("\n>>> WEEK 2 — Adaptive plan (plateau detected)")
    p2 = run_pipeline(user_id, week_number=2)

    # Comparison
    print("\n" + "="*55)
    print("  COMPARISON: Week 1 vs Week 2")
    print("="*55)
    print(f"  Week 1 volume:   {p1.workout_plan.weekly_volume_sets} sets/week")
    print(f"  Week 2 volume:   {p2.workout_plan.weekly_volume_sets} sets/week")
    print(f"  Week 1 calories: {p1.nutrition_plan.target_calories:.0f} kcal")
    print(f"  Week 2 calories: {p2.nutrition_plan.target_calories:.0f} kcal")
    print(f"\n  Week 1 signals:  {[s.signal_type for s in p1.adaptation_signals]}")
    print(f"  Week 2 signals:  {[s.signal_type for s in p2.adaptation_signals]}")
    print(f"\n  Week 1 conflicts: {p1.conflicts_resolved or ['none']}")
    print(f"  Week 2 conflicts: {p2.conflicts_resolved or ['none']}")
    print(f"\n  Week 1 notes: {p1.orchestrator_notes}")
    print(f"\n  Week 2 notes: {p2.orchestrator_notes}")

    history = get_adaptation_history(user_id)
    print(f"\n  Total adaptation events logged: {len(history)}")
    
if __name__ == "__main__":
    from memory.long_term import create_sample_user

    print("\n── Setting up test user ──")
    profile = create_sample_user()

    demo_adaptation(profile.user_id)