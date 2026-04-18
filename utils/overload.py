"""
Progressive Overload Engine.

Given an exercise's performance history, compute a deterministic next-session
prescription. This replaces "inject raw history as text and hope the LLM
progresses correctly" with actual coaching logic.

Rules are drawn from standard programming (Rippetoe's double-progression,
Helms's RPE-based undulating progression):

  1. If user completed all target sets & reps @ the prescribed RPE/weight:
       - If bodyweight/unloaded: add 1-2 reps (volume progression).
       - If loaded: add smallest practical load (2.5kg compound, 1.25kg isolation).
  2. If user hit reps but RPE was low (<=7): add weight, drop reps.
  3. If user missed reps on last set: repeat same prescription.
  4. If user missed reps across multiple sets: consider deload (reduce 10%).
  5. If no history: return a reasonable starting prescription.

Output is NOT LLM-generated — it's a deterministic `Prescription` struct
that gets injected into the Fitness Agent prompt. The LLM's job becomes
"explain the prescription" rather than "invent it".
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal, Optional


ProgressionType = Literal["add_weight", "add_reps", "repeat", "deload", "fresh_start"]


@dataclass
class ExerciseHistory:
    """One logged session."""
    date: str
    sets_completed: int
    reps_completed: str       # e.g. "10,10,8" or "10"
    weight_kg: float           # 0 for bodyweight
    target_sets: Optional[int] = None
    target_reps: Optional[str] = None  # e.g. "8-12"
    rpe: Optional[int] = None


@dataclass
class Prescription:
    exercise: str
    sets: int
    reps: str                 # "8-12" or "12"
    weight_kg: float
    rest_seconds: int
    progression_type: ProgressionType
    reasoning: str            # human-readable explanation

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_rep_range(s: str) -> tuple[int, int]:
    """'8-12' -> (8, 12); '10' -> (10, 10)."""
    if not s:
        return (8, 12)
    s = s.strip()
    if "-" in s:
        parts = s.split("-", 1)
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            return (8, 12)
    try:
        n = int(s)
        return (n, n)
    except ValueError:
        return (8, 12)


def _parse_reps_completed(s: str) -> list[int]:
    """'10,10,8' -> [10, 10, 8]; '10' -> [10]."""
    if not s:
        return []
    out = []
    for part in s.split(","):
        try:
            out.append(int(part.strip()))
        except ValueError:
            pass
    return out


def _smallest_increment_kg(weight: float, is_compound: bool) -> float:
    """Smallest practical weight jump."""
    if weight == 0:
        return 0  # bodyweight — use rep progression instead
    return 2.5 if is_compound else 1.25


def _is_compound(exercise_name: str) -> bool:
    """Heuristic: is this a compound (multi-joint) movement?"""
    name = exercise_name.lower()
    compound_keywords = [
        "squat", "deadlift", "bench", "press", "row", "pull-up", "pullup",
        "chin-up", "dip", "lunge", "clean", "snatch", "thrust", "hip thrust",
    ]
    isolation_keywords = [
        "curl", "extension", "raise", "fly", "flye", "kickback", "shrug",
    ]
    if any(k in name for k in isolation_keywords):
        return False
    return any(k in name for k in compound_keywords)


def _is_bodyweight(exercise_name: str, weight_kg: float) -> bool:
    """Detects bodyweight exercises where rep-progression is primary."""
    if weight_kg > 0:
        return False
    name = exercise_name.lower()
    return any(k in name for k in [
        "push-up", "pushup", "pull-up", "pullup", "chin-up", "dip",
        "bodyweight", "plank", "squat" if weight_kg == 0 else ""
    ])


# ── Main progression logic ────────────────────────────────────────────────────

def prescribe_next_session(
    exercise_name: str,
    history: list[ExerciseHistory],
    default_sets: int = 3,
    default_reps: str = "8-12",
    default_rest: int = 90,
) -> Prescription:
    """
    Compute the next session's prescription given historical performance.

    Args:
        exercise_name: canonical exercise name
        history: list of past sessions, most recent LAST (ascending by date)
        default_sets / default_reps / default_rest: fallback values
    """
    if not history:
        return Prescription(
            exercise=exercise_name,
            sets=default_sets,
            reps=default_reps,
            weight_kg=0.0,
            rest_seconds=default_rest,
            progression_type="fresh_start",
            reasoning="No prior history. Starting with default prescription.",
        )

    last = history[-1]
    compound = _is_compound(exercise_name)
    bodyweight = _is_bodyweight(exercise_name, last.weight_kg)

    last_reps = _parse_reps_completed(last.reps_completed)
    target_lo, target_hi = _parse_rep_range(last.target_reps or default_reps)
    target_sets = last.target_sets or default_sets

    # Completion: did they hit target reps on all sets?
    if not last_reps:
        # No rep data — repeat
        return Prescription(
            exercise=exercise_name,
            sets=target_sets,
            reps=last.target_reps or default_reps,
            weight_kg=last.weight_kg,
            rest_seconds=default_rest,
            progression_type="repeat",
            reasoning="No rep data recorded last session. Repeat same prescription.",
        )

    all_sets_hit_top = (
        len(last_reps) >= target_sets
        and all(r >= target_hi for r in last_reps[:target_sets])
    )
    some_sets_missed = any(r < target_lo for r in last_reps)
    heavy_miss = sum(1 for r in last_reps if r < target_lo) >= 2

    # ── Rule 4: multi-set failure -> deload ──
    if heavy_miss:
        deload_weight = round(last.weight_kg * 0.9 / 2.5) * 2.5 if last.weight_kg > 0 else 0
        return Prescription(
            exercise=exercise_name,
            sets=target_sets,
            reps=last.target_reps or default_reps,
            weight_kg=deload_weight,
            rest_seconds=default_rest,
            progression_type="deload",
            reasoning=(
                f"Missed target reps on {sum(1 for r in last_reps if r < target_lo)} sets "
                f"last session. Deloading to {deload_weight}kg (90% of previous) "
                f"to rebuild form and confidence."
            ),
        )

    # ── Rule 3: single-set miss -> repeat ──
    if some_sets_missed and not all_sets_hit_top:
        return Prescription(
            exercise=exercise_name,
            sets=target_sets,
            reps=last.target_reps or default_reps,
            weight_kg=last.weight_kg,
            rest_seconds=default_rest,
            progression_type="repeat",
            reasoning=(
                f"Completed {last_reps} on target {target_lo}-{target_hi}. "
                "Repeating same weight until all sets hit the top of the range."
            ),
        )

    # ── Rule 1/2: all sets hit top -> progress ──
    if all_sets_hit_top:
        if bodyweight:
            new_hi = target_hi + 2
            new_lo = max(target_lo + 1, new_hi - 3)
            return Prescription(
                exercise=exercise_name,
                sets=target_sets,
                reps=f"{new_lo}-{new_hi}",
                weight_kg=0.0,
                rest_seconds=default_rest,
                progression_type="add_reps",
                reasoning=(
                    f"Cleared {target_lo}-{target_hi} on all sets. "
                    f"Bodyweight progression: target {new_lo}-{new_hi} reps."
                ),
            )
        if last.weight_kg == 0:
            # No weight tracked but not explicitly bodyweight — add reps
            new_hi = target_hi + 2
            return Prescription(
                exercise=exercise_name,
                sets=target_sets,
                reps=f"{target_lo + 1}-{new_hi}",
                weight_kg=0.0,
                rest_seconds=default_rest,
                progression_type="add_reps",
                reasoning="All sets hit top of range. Increasing rep target.",
            )
        # Loaded exercise — add weight, reset reps
        inc = _smallest_increment_kg(last.weight_kg, compound)
        new_weight = round((last.weight_kg + inc) / 2.5) * 2.5
        return Prescription(
            exercise=exercise_name,
            sets=target_sets,
            reps=last.target_reps or default_reps,
            weight_kg=new_weight,
            rest_seconds=default_rest,
            progression_type="add_weight",
            reasoning=(
                f"Cleared {target_hi} reps on all {target_sets} sets at "
                f"{last.weight_kg}kg. Adding {inc}kg -> {new_weight}kg."
            ),
        )

    # ── Fallback: some progress, not all top ──
    return Prescription(
        exercise=exercise_name,
        sets=target_sets,
        reps=last.target_reps or default_reps,
        weight_kg=last.weight_kg,
        rest_seconds=default_rest,
        progression_type="repeat",
        reasoning=(
            f"Partial progress last session ({last_reps}). "
            "Repeat to consolidate."
        ),
    )


def format_prescriptions_for_prompt(prescriptions: list[Prescription]) -> str:
    """Format a list of prescriptions for injection into the Fitness Agent prompt."""
    if not prescriptions:
        return ""
    lines = [
        "── PROGRESSIVE OVERLOAD PRESCRIPTIONS (use exactly as specified) ──",
    ]
    for p in prescriptions:
        w = f"{p.weight_kg}kg" if p.weight_kg > 0 else "bodyweight"
        lines.append(
            f"  • {p.exercise}: {p.sets}×{p.reps} @ {w} "
            f"(rest {p.rest_seconds}s) — {p.progression_type}"
        )
        lines.append(f"    reasoning: {p.reasoning}")
    lines.append("── END PRESCRIPTIONS ──")
    return "\n".join(lines)


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("── Progressive Overload Engine Tests ──\n")

    # Test 1: No history
    p = prescribe_next_session("Squat", [])
    assert p.progression_type == "fresh_start"
    print(f"  ✓ No history: {p.progression_type}")

    # Test 2: User hit all top reps -> add weight
    hist = [ExerciseHistory(
        date="2026-04-15",
        sets_completed=3, reps_completed="12,12,12",
        weight_kg=60, target_sets=3, target_reps="8-12",
    )]
    p = prescribe_next_session("Barbell Squat", hist)
    assert p.progression_type == "add_weight"
    assert p.weight_kg == 62.5
    print(f"  ✓ All top reps on loaded compound: add weight 60kg -> {p.weight_kg}kg")

    # Test 3: User hit all top reps on bodyweight -> add reps
    hist = [ExerciseHistory(
        date="2026-04-15",
        sets_completed=3, reps_completed="12,12,12",
        weight_kg=0, target_sets=3, target_reps="8-12",
    )]
    p = prescribe_next_session("Push-ups", hist)
    assert p.progression_type == "add_reps"
    print(f"  ✓ Bodyweight top reps: add reps -> {p.reps}")

    # Test 4: Missed reps on one set -> repeat
    hist = [ExerciseHistory(
        date="2026-04-15",
        sets_completed=3, reps_completed="12,10,7",
        weight_kg=60, target_sets=3, target_reps="8-12",
    )]
    p = prescribe_next_session("Barbell Squat", hist)
    assert p.progression_type == "repeat"
    print(f"  ✓ One set missed: {p.progression_type} @ {p.weight_kg}kg")

    # Test 5: Heavy miss on multiple sets -> deload
    hist = [ExerciseHistory(
        date="2026-04-15",
        sets_completed=3, reps_completed="7,6,5",
        weight_kg=70, target_sets=3, target_reps="8-12",
    )]
    p = prescribe_next_session("Barbell Squat", hist)
    assert p.progression_type == "deload"
    assert p.weight_kg == 62.5  # 70 * 0.9 = 63 -> 62.5 (rounded to nearest 2.5)
    print(f"  ✓ Multi-set miss: deload 70kg -> {p.weight_kg}kg")

    # Test 6: Isolation exercise (1.25kg increment)
    hist = [ExerciseHistory(
        date="2026-04-15",
        sets_completed=3, reps_completed="12,12,12",
        weight_kg=15, target_sets=3, target_reps="10-12",
    )]
    p = prescribe_next_session("Dumbbell Bicep Curl", hist)
    assert p.progression_type == "add_weight"
    print(f"  ✓ Isolation add weight: 15kg -> {p.weight_kg}kg")

    print("\n── Sample prompt formatting ──")
    all_prescriptions = [
        prescribe_next_session("Barbell Squat", [ExerciseHistory(
            date="2026-04-15", sets_completed=3, reps_completed="12,12,12",
            weight_kg=60, target_sets=3, target_reps="8-12",
        )]),
        prescribe_next_session("Push-ups", [ExerciseHistory(
            date="2026-04-15", sets_completed=3, reps_completed="15,14,12",
            weight_kg=0, target_sets=3, target_reps="10-15",
        )]),
    ]
    print(format_prescriptions_for_prompt(all_prescriptions))