"""
Statistical plateau detection.

Replaces the naive "last_weight - first_weight < threshold" heuristic with
a proper signal-processing pipeline:

  1. Smooth daily weights with a 7-day rolling mean (removes water-weight noise).
  2. Fit a linear regression to the smoothed series over the evaluation window.
  3. Compare the fitted slope (kg/week) to goal-specific expected ranges.
  4. Classify as: plateau, on_track, overshooting, reversing.

This gives the BTP report a defensible methodology section:
  "Following Hall et al. (2011) and Thomas et al. (2014), we treat body weight
   as a noisy observation of an underlying trend, and use a 7-day moving
   average to attenuate day-to-day fluid variance (typically ±1-2kg) before
   slope estimation."

Why this matters: a 0.3kg/week threshold on raw weights (the v1 approach)
would classify any 2-day reading that landed within normal fluid variance
as a plateau. Real plateaus are defined by the *trend*, not single points.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Literal, Optional


PlateauStatus = Literal[
    "plateau",          # slope ~ 0 for goal that expects change
    "on_track",         # slope matches goal direction
    "overshooting",     # losing faster than healthy, or gaining too fast
    "reversing",        # slope opposite to goal direction
    "insufficient_data" # not enough points
]


@dataclass
class PlateauResult:
    status: PlateauStatus
    slope_kg_per_week: float
    smoothed_values: list[float]
    raw_variance_kg: float
    data_points: int
    first_date: Optional[str]
    last_date: Optional[str]
    goal: str
    expected_slope_range: tuple[float, float]
    confidence: float  # 0-1, based on how many points and how clean the fit
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


# Expected weekly weight change (kg/week) by goal.
# Sources: ACSM position stand on weight management (0.5-1% BW per week safe).
GOAL_EXPECTED_SLOPE: dict[str, tuple[float, float]] = {
    # (min_expected, max_expected)  both signed
    "weight_loss":   (-1.0, -0.25),   # losing 0.25 to 1.0 kg/week
    "muscle_gain":   (0.15, 0.5),     # gaining 0.15 to 0.5 kg/week
    "endurance":     (-0.25, 0.25),   # roughly stable
    "maintenance":   (-0.25, 0.25),   # roughly stable
}


def _rolling_mean(values: list[float], window: int = 7) -> list[float]:
    """Trailing rolling mean. First (window-1) points use all available prior."""
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start: i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """
    Fit y = m*x + c, return (slope, intercept, r_squared).
    Simple OLS — no external dependencies.
    """
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0, 0.0

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0, mean_y, 0.0

    slope = num / den
    intercept = mean_y - slope * mean_x

    # r²
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return slope, intercept, max(0.0, r2)


def detect_plateau(
    weight_series: list[dict],
    goal: str = "maintenance",
    min_points: int = 5,
    window_days: int = 14,
) -> PlateauResult:
    """
    Analyze a weight series and classify the trend relative to the user's goal.

    Args:
        weight_series: list of {"date": "YYYY-MM-DD", "weight_kg": float},
                       expected to be sorted ascending by date.
        goal: one of weight_loss, muscle_gain, endurance, maintenance.
        min_points: minimum data points needed to evaluate.
        window_days: evaluation window length in days.

    Returns:
        PlateauResult with status and supporting statistics.
    """
    expected_range = GOAL_EXPECTED_SLOPE.get(goal, GOAL_EXPECTED_SLOPE["maintenance"])

    if not weight_series or len(weight_series) < min_points:
        return PlateauResult(
            status="insufficient_data",
            slope_kg_per_week=0.0,
            smoothed_values=[],
            raw_variance_kg=0.0,
            data_points=len(weight_series) if weight_series else 0,
            first_date=None,
            last_date=None,
            goal=goal,
            expected_slope_range=expected_range,
            confidence=0.0,
            reason=f"Need at least {min_points} data points, have {len(weight_series) if weight_series else 0}",
        )

    # Use only last `window_days` of data points (approximately)
    recent = weight_series[-min(len(weight_series), window_days + 7):]

    raw_values = [float(p["weight_kg"]) for p in recent]
    dates = [p["date"] for p in recent]

    # Smooth
    smoothed = _rolling_mean(raw_values, window=7)

    # Day indices relative to first point (not just 0..n-1)
    # so gaps in logging are handled correctly
    from datetime import datetime
    first_dt = datetime.strptime(dates[0], "%Y-%m-%d")
    xs = [
        (datetime.strptime(d, "%Y-%m-%d") - first_dt).days
        for d in dates
    ]

    slope_per_day, _, r2 = _linear_regression(xs, smoothed)
    slope_per_week = slope_per_day * 7

    # Raw variance (how noisy is the signal)
    mean_raw = sum(raw_values) / len(raw_values)
    raw_var = math.sqrt(sum((v - mean_raw) ** 2 for v in raw_values) / len(raw_values))

    # Classify
    min_exp, max_exp = expected_range
    status: PlateauStatus
    reason: str

    # Define a "zero" band as a fraction of the expected range
    zero_band = 0.15  # kg/week considered "flat"

    if goal in ("weight_loss", "muscle_gain"):
        if abs(slope_per_week) < zero_band:
            status = "plateau"
            reason = (f"Smoothed weight is essentially flat "
                      f"(slope={slope_per_week:+.2f} kg/week) "
                      f"but goal '{goal}' expects {min_exp:+.2f} to {max_exp:+.2f} kg/week")
        elif (goal == "weight_loss" and slope_per_week > zero_band) or \
             (goal == "muscle_gain" and slope_per_week < -zero_band):
            status = "reversing"
            reason = (f"Trend is moving opposite to goal "
                      f"(slope={slope_per_week:+.2f} kg/week)")
        elif (goal == "weight_loss" and slope_per_week < min_exp) or \
             (goal == "muscle_gain" and slope_per_week > max_exp):
            status = "overshooting"
            reason = (f"Changing too fast for goal "
                      f"(slope={slope_per_week:+.2f} kg/week, "
                      f"healthy range {min_exp:+.2f} to {max_exp:+.2f})")
        else:
            status = "on_track"
            reason = (f"On track (slope={slope_per_week:+.2f} kg/week, "
                      f"target {min_exp:+.2f} to {max_exp:+.2f})")
    else:
        # maintenance / endurance
        if abs(slope_per_week) < zero_band:
            status = "on_track"
            reason = f"Stable within maintenance band (slope={slope_per_week:+.2f} kg/week)"
        elif abs(slope_per_week) > max(abs(min_exp), abs(max_exp)) * 2:
            status = "overshooting"
            reason = f"Drifting too far from maintenance (slope={slope_per_week:+.2f} kg/week)"
        else:
            status = "on_track"
            reason = f"Within maintenance range (slope={slope_per_week:+.2f} kg/week)"

    # Confidence combines sample size and fit quality
    # - r² contributes most when we have many points
    # - min 5 points gives 0.5, 14+ gives 1.0
    size_factor = min(1.0, (len(recent) - min_points) / 10 + 0.5)
    confidence = round(size_factor * (0.5 + 0.5 * r2), 2)

    return PlateauResult(
        status=status,
        slope_kg_per_week=round(slope_per_week, 3),
        smoothed_values=[round(v, 2) for v in smoothed],
        raw_variance_kg=round(raw_var, 2),
        data_points=len(recent),
        first_date=dates[0],
        last_date=dates[-1],
        goal=goal,
        expected_slope_range=expected_range,
        confidence=confidence,
        reason=reason,
    )


# ── Self-test with synthetic data ─────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import datetime, timedelta

    def gen_series(start: float, slope_per_week: float, n_days: int,
                   noise_amplitude: float = 0.8) -> list[dict]:
        """Generate synthetic weight data with realistic daily noise."""
        import random
        random.seed(42)
        base_date = datetime(2026, 4, 1)
        out = []
        for i in range(n_days):
            trend = start + slope_per_week / 7 * i
            noise = random.uniform(-noise_amplitude, noise_amplitude)
            out.append({
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "weight_kg": round(trend + noise, 1),
            })
        return out

    print("── Plateau Detector Tests ──\n")

    scenarios = [
        ("True plateau during weight_loss", gen_series(78, 0.0, 21), "weight_loss", "plateau"),
        ("On track weight loss",            gen_series(78, -0.5, 21), "weight_loss", "on_track"),
        ("Overshooting weight loss",        gen_series(78, -1.5, 21), "weight_loss", "overshooting"),
        ("Reversing weight loss",           gen_series(78, 0.3, 21), "weight_loss", "reversing"),
        ("On track muscle gain",            gen_series(70, 0.3, 21), "muscle_gain", "on_track"),
        ("Plateau during muscle gain",      gen_series(70, 0.0, 21), "muscle_gain", "plateau"),
        ("Maintenance stable",              gen_series(70, 0.0, 21), "maintenance", "on_track"),
        ("Not enough data",                 gen_series(70, 0.0, 3),  "weight_loss", "insufficient_data"),
    ]

    for label, series, goal, expected in scenarios:
        result = detect_plateau(series, goal=goal)
        mark = "✓" if result.status == expected else "✗"
        print(f"  {mark} {label:<38} -> {result.status:<20} "
              f"slope={result.slope_kg_per_week:+.2f} kg/wk, "
              f"conf={result.confidence:.2f}")
        if result.status != expected:
            print(f"      expected {expected}: {result.reason}")

    print("\n  [Plateau detector] Done")