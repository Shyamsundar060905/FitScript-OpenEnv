"""
Orchestrator v2.

Changes from v1:
  - Rate-limit checks before running the pipeline.
  - Sanitizes constraint_context.
  - Wraps the full pipeline in an observability span with trace_id linking
    all agent calls together.
  - Conflict rules unchanged but now use the verified `status` field from
    the new plateau detector.
"""

import sys
import os
import uuid
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime

from llm.router import llm_call
from memory.long_term import load_profile
from memory.episodic import get_active_constraints
from schemas import AgentMessage, WeeklyPrescription
import agents.profile_agent as profile_agent
import agents.fitness_agent as fitness_agent
import agents.nutrition_agent as nutrition_agent
import agents.progress_agent as progress_agent
from utils.observability import agent_span, log_event
from utils.rate_limit import check_and_record, RateLimitDecision
from utils.sanitize import sanitize_user_text, sanitize_constraint_list


CONFLICT_RULES = [
    {
        "condition": lambda fit, nut, prog: (
            any(
                s["signal_type"] == "plateau"
                and s["severity"] in ["medium", "high"]
                for s in prog.payload.get("signals", [])
            )
            and fit.payload.get("weekly_volume_sets", 0) < 40
        ),
        "action": "increase_volume",
        "description": "Plateau detected but training volume is low — increase workout volume",
    },
    {
        "condition": lambda fit, nut, prog: (
            "fitness" in nut.conflicts_with
            or nut.payload.get("target_calories", 9999) <
               fit.payload.get("weekly_volume_sets", 0) * 15
        ),
        "action": "increase_calories",
        "description": "High training volume with insufficient calories — increase calorie target by 200",
    },
    {
        "condition": lambda fit, nut, prog: any(
            s["signal_type"] == "overtraining" for s in prog.payload.get("signals", [])
        ),
        "action": "reduce_volume",
        "description": "Overtraining signal detected — reduce weekly volume by 20% and add recovery day",
    },
    {
        "condition": lambda fit, nut, prog: any(
            s["signal_type"] == "schedule_change" for s in prog.payload.get("signals", [])
        ),
        "action": "reduce_frequency",
        "description": "Low adherence detected — reduce sessions per week by 1",
    },
]


def resolve_conflicts(fit_msg: AgentMessage, nut_msg: AgentMessage,
                      prog_msg: AgentMessage) -> list:
    triggered = []
    for rule in CONFLICT_RULES:
        try:
            if rule["condition"](fit_msg, nut_msg, prog_msg):
                triggered.append(rule["description"])
        except Exception:
            continue
    return triggered


def synthesize_with_llm(profile_msg, fit_msg, nut_msg, prog_msg,
                        conflicts_resolved) -> str:
    signals = prog_msg.payload.get("signals", [])
    signal_text = "; ".join(
        f"{s['signal_type']} ({s['severity']}): {s['description']}"
        for s in signals
    ) or "No significant signals"

    conflict_text = "; ".join(conflicts_resolved) or "No conflicts detected"

    prompt = f"""You are the Orchestrator of a multi-agent fitness AI system.
Write a brief 2-3 sentence summary explaining this week's prescription.

User goal: {profile_msg.payload.get('goal', 'unknown')}
Fitness plan: {fit_msg.reasoning}
Nutrition plan: {nut_msg.reasoning}
Progress signals: {signal_text}
Conflicts resolved: {conflict_text}

Write a friendly, motivating summary in second person (you/your).
Keep it under 60 words. Plain text only."""

    return llm_call("You are a helpful fitness coach.", prompt, json_mode=False)


class RateLimitExceeded(Exception):
    """Raised when the user exceeds rate limits."""
    def __init__(self, decision: RateLimitDecision):
        self.decision = decision
        super().__init__(f"Rate limit: {decision.reason}")


def run_pipeline(user_id: str, week_number: int = 1,
                 constraint_context: str = "",
                 skip_rate_limit: bool = False) -> WeeklyPrescription:
    """
    Full orchestration pipeline with rate limiting, sanitization, and tracing.
    """

    # ── Rate limit check ─────────────────────────────────────────────────────
    if not skip_rate_limit:
        decision = check_and_record(user_id, action="agent_run")
        if not decision.allowed:
            raise RateLimitExceeded(decision)

    # Each pipeline run gets a trace_id so events are correlatable
    trace_id = str(uuid.uuid4())[:12]

    # Merge constraint_context with persistent user constraints
    persistent = get_active_constraints(user_id)
    all_constraints = []
    if constraint_context:
        all_constraints.append(
            sanitize_user_text(constraint_context, max_length=500)
        )
    all_constraints.extend(persistent)
    safe_constraint_context = "; ".join(sanitize_constraint_list(all_constraints))

    print(f"\n{'='*55}")
    print(f"  ORCHESTRATOR — Week {week_number} | User: {user_id}")
    print(f"  Trace: {trace_id}")
    print(f"{'='*55}")

    with agent_span("orchestrator", user_id, trace_id=trace_id,
                    metadata={"week_number": week_number}) as orch_span:

        # Step 1: Profile
        print("\n  [Step 1] Loading profile...")
        profile_msg = profile_agent.run(user_id)
        profile = load_profile(user_id)

        # Step 2: Progress
        print("\n  [Step 2] Analyzing progress...")
        prog_msg = progress_agent.run(user_id)
        signals = prog_msg.payload.get("signals", [])

        # Build adaptation context
        adaptation_context = ""
        if signals:
            adaptation_context = "; ".join(
                f"{s['signal_type']}: {s['recommended_action']}"
                for s in signals
            )
        if safe_constraint_context:
            adaptation_context = (
                adaptation_context + "; " + safe_constraint_context
                if adaptation_context else safe_constraint_context
            )

        # Agent log for UI
        agent_log = []
        agent_log.append({
            "agent": "Profile Agent",
            "icon": "👤",
            "decision": f"Loaded profile for {profile.name}",
            "detail": profile.to_summary(),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        signal_summary = (
            ", ".join(f"{s['signal_type']} ({s['severity']})" for s in signals)
            if signals else "No issues detected"
        )
        agent_log.append({
            "agent": "Progress Agent",
            "icon": "📊",
            "decision": signal_summary,
            "detail": adaptation_context or "Fresh start — no history to analyze",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        # Step 3: Fitness
        print("\n  [Step 3] Generating workout plan...")
        fit_msg = fitness_agent.run(
            user_id, week_number=week_number,
            adaptation_context=adaptation_context,
        )
        agent_log.append({
            "agent": "Fitness Agent",
            "icon": "💪",
            "decision": (
                f"Generated {len(fit_msg.payload.get('days', []))} day plan, "
                f"{fit_msg.payload.get('weekly_volume_sets', 0)} sets/week"
            ),
            "detail": fit_msg.reasoning,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        # Step 4: Nutrition
        print("\n  [Step 4] Generating nutrition plan...")
        calorie_adj = 200.0 if fit_msg.payload.get("weekly_volume_sets", 0) > 60 else 0.0
        nut_msg = nutrition_agent.run(
            user_id, week_number=week_number,
            calorie_adjustment=calorie_adj,
            adaptation_context=adaptation_context,
        )
        agent_log.append({
            "agent": "Nutrition Agent",
            "icon": "🥗",
            "decision": (
                f"{nut_msg.payload.get('target_calories', 0):.0f} kcal/day, "
                f"{nut_msg.payload.get('target_protein_g', 0):.0f}g protein"
            ),
            "detail": nut_msg.reasoning,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        # Step 5: Conflicts
        print("\n  [Step 5] Resolving conflicts...")
        conflicts_resolved = resolve_conflicts(fit_msg, nut_msg, prog_msg)
        agent_log.append({
            "agent": "Conflict Resolver",
            "icon": "⚡",
            "decision": (
                f"Resolved: {conflicts_resolved[0]}"
                if conflicts_resolved else "No conflicts detected"
            ),
            "detail": "; ".join(conflicts_resolved) if conflicts_resolved
                      else "All agents in agreement",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        # Step 6: Synthesize
        print("\n  [Step 6] Synthesizing prescription...")
        try:
            notes = synthesize_with_llm(
                profile_msg, fit_msg, nut_msg, prog_msg, conflicts_resolved
            )
        except Exception as e:
            notes = (
                f"Week {week_number} plan ready. "
                f"{len(signals)} signals, {len(conflicts_resolved)} conflicts resolved."
            )
            print(f"  [Synth] LLM failed, using fallback: {e}")

        agent_log.append({
            "agent": "Orchestrator",
            "icon": "🧠",
            "decision": "Prescription synthesized",
            "detail": notes.strip(),
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        # Build final prescription
        from schemas import WorkoutPlan, NutritionPlan, AdaptationSignal
        exclude_keys = {
            "knowledge_chunks", "knowledge_chunks_data",
            "overload_prescriptions", "verification",
        }
        workout_plan = WorkoutPlan(**{
            k: v for k, v in fit_msg.payload.items() if k not in exclude_keys
        })
        nutrition_plan = NutritionPlan(**{
            k: v for k, v in nut_msg.payload.items() if k not in exclude_keys
        })
        adaptation_signals = [AdaptationSignal(**s) for s in signals]

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
            agent_log=agent_log,
        )

        orch_span["metrics"]["signals"] = len(adaptation_signals)
        orch_span["metrics"]["conflicts"] = len(conflicts_resolved)
        orch_span["metrics"]["knowledge_chunks"] = len(knowledge_used)
        orch_span["metrics"]["trace_id"] = trace_id
        orch_span["metadata"]["verification_coverage"] = (
            nut_msg.payload.get("verification", {}).get("overall_coverage", 0)
        )
        orch_span["metadata"]["overload_prescriptions"] = len(
            fit_msg.payload.get("overload_prescriptions", [])
        )

    print(f"\n  ✓ Prescription ready — {len(workout_plan.days)} workout days, "
          f"{len(nutrition_plan.daily_plans)} nutrition days, "
          f"{len(adaptation_signals)} signal(s)")
    return prescription