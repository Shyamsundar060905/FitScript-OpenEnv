"""
Export utilities — PDF reports and ICS (calendar) export.

PDF: uses reportlab to lay out a clean multi-page prescription report.
ICS: emits standard iCalendar events for each workout day so users can
     subscribe to their plan in Google Calendar, Apple Calendar, Outlook.

Both export functions take a `WeeklyPrescription` object (from schemas)
and write to a file path. They return the path on success.

Dependencies: reportlab (optional — ICS works without it).
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from schemas import WeeklyPrescription


# ── PDF export ────────────────────────────────────────────────────────────────

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def export_prescription_to_pdf(
    prescription: WeeklyPrescription,
    output_path: str | Path,
    user_name: str = "User",
) -> Path:
    """
    Render a WeeklyPrescription as a formatted PDF.

    Raises ImportError if reportlab is not installed.
    """
    if not HAS_REPORTLAB:
        raise ImportError(
            "PDF export requires reportlab. Install with: pip install reportlab"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"FitAgent Plan — Week {prescription.week_number}",
        author="FitAgent AI",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Brand",
        fontSize=20, textColor=colors.HexColor("#E85D26"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=13, textColor=colors.HexColor("#1a1a2e"),
        spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SubHeader",
        fontSize=11, textColor=colors.HexColor("#374151"),
        spaceBefore=6, spaceAfter=4, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="Note",
        fontSize=9, textColor=colors.HexColor("#6B7280"),
        spaceAfter=4, leading=12,
    ))

    story = []

    # ── Header ──
    story.append(Paragraph("FitAgent AI", styles["Brand"]))
    story.append(Paragraph(
        f"Weekly Prescription for {user_name} — Week {prescription.week_number}",
        styles["Heading3"],
    ))
    story.append(Paragraph(
        f"Generated {prescription.generated_at[:10]}",
        styles["Note"],
    ))
    story.append(Spacer(1, 8))

    # ── Summary ──
    if prescription.orchestrator_notes:
        story.append(Paragraph("Coach's Summary", styles["SectionHeader"]))
        story.append(Paragraph(
            prescription.orchestrator_notes,
            styles["BodyText"],
        ))

    # ── Adaptation signals ──
    if prescription.adaptation_signals:
        story.append(Paragraph("Progress Signals", styles["SectionHeader"]))
        rows = [["Type", "Severity", "Description", "Action"]]
        for s in prescription.adaptation_signals:
            rows.append([
                s.signal_type.replace("_", " ").title(),
                s.severity.upper(),
                Paragraph(s.description, styles["BodyText"]),
                Paragraph(s.recommended_action, styles["BodyText"]),
            ])
        t = Table(rows, colWidths=[25 * mm, 18 * mm, 65 * mm, 65 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E85D26")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ]))
        story.append(t)

    # ── Workout plan ──
    story.append(PageBreak())
    story.append(Paragraph(
        f"Workout Plan — {prescription.workout_plan.weekly_volume_sets} sets/week",
        styles["SectionHeader"],
    ))
    if prescription.workout_plan.notes:
        story.append(Paragraph(prescription.workout_plan.notes, styles["Note"]))

    for day in prescription.workout_plan.days:
        story.append(Paragraph(
            f"{day.day_name} — {day.focus} "
            f"(~{day.estimated_duration_minutes} min)",
            styles["SubHeader"],
        ))
        ex_rows = [["Exercise", "Sets × Reps", "Rest", "Notes"]]
        for ex in day.exercises:
            reps = ex.reps or f"{ex.duration_minutes} min" if ex.duration_minutes else "?"
            sets = ex.sets or "—"
            ex_rows.append([
                ex.name,
                f"{sets} × {reps}",
                f"{ex.rest_seconds}s",
                Paragraph(ex.notes or "", styles["Note"]),
            ])
        t = Table(ex_rows, colWidths=[55 * mm, 30 * mm, 18 * mm, 70 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    # ── Nutrition plan ──
    story.append(PageBreak())
    story.append(Paragraph(
        f"Nutrition Plan — {prescription.nutrition_plan.target_calories:.0f} kcal/day · "
        f"{prescription.nutrition_plan.target_protein_g:.0f}g protein",
        styles["SectionHeader"],
    ))
    if prescription.nutrition_plan.notes:
        story.append(Paragraph(prescription.nutrition_plan.notes, styles["Note"]))

    for day in prescription.nutrition_plan.daily_plans:
        story.append(Paragraph(
            f"{day.day_name} — {day.total_calories:.0f} kcal · "
            f"P:{day.total_protein_g:.0f}g · "
            f"C:{day.total_carbs_g:.0f}g · "
            f"F:{day.total_fats_g:.0f}g",
            styles["SubHeader"],
        ))
        meal_rows = [["Meal", "Foods", "kcal", "Protein"]]
        for meal in day.meals:
            meal_rows.append([
                meal.meal_name,
                Paragraph("<br/>".join(f"• {f}" for f in meal.foods), styles["BodyText"]),
                f"{meal.calories:.0f}",
                f"{meal.protein_g:.0f}g",
            ])
        t = Table(meal_rows, colWidths=[25 * mm, 95 * mm, 20 * mm, 20 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    # ── Footer / attribution ──
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This plan was generated by FitAgent AI, a multi-agent fitness "
        "advisory system. Nutrition values are sourced from the Indian Food "
        "Composition Tables (IFCT) 2017 and USDA FoodData Central where "
        "available. This is for informational use only and is not medical advice.",
        styles["Note"],
    ))

    doc.build(story)
    return output_path


# ── ICS calendar export ───────────────────────────────────────────────────────

# Map day_name strings to weekday offsets (0=Monday)
_DAY_OFFSETS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "day 1": 0, "day 2": 1, "day 3": 2, "day 4": 3,
    "day 5": 4, "day 6": 5, "day 7": 6,
}


def _parse_day_offset(day_name: str) -> int:
    """Best-effort parse of 'Monday', 'Day 1 - Monday', etc. to 0-6."""
    name = day_name.lower()
    for key, offset in _DAY_OFFSETS.items():
        if key in name:
            return offset
    return 0


def _ics_escape(text: str) -> str:
    """Escape text for ICS field values per RFC 5545."""
    return (
        text.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
            .replace("\r", "")
    )


def _fold_line(line: str) -> str:
    """RFC 5545 line folding — break at 75 octets, continuation starts with space."""
    if len(line) <= 75:
        return line
    out = [line[:75]]
    remaining = line[75:]
    while remaining:
        out.append(" " + remaining[:74])
        remaining = remaining[74:]
    return "\r\n".join(out)


def export_prescription_to_ics(
    prescription: WeeklyPrescription,
    output_path: str | Path,
    start_date: Optional[datetime] = None,
    event_time: str = "07:00",
    duration_minutes: int = 60,
    user_name: str = "User",
) -> Path:
    """
    Emit an .ics calendar file with one event per workout day for the week.

    Args:
        prescription: the WeeklyPrescription to export
        output_path: where to write the .ics file
        start_date: Monday of the target week (defaults to next Monday)
        event_time: HH:MM start time for each workout
        duration_minutes: event length
        user_name: embedded in event descriptions
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Default to next Monday
    if start_date is None:
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7 or 7
        start_date = today + timedelta(days=days_until_monday)
    start_date = start_date.replace(
        hour=int(event_time.split(":")[0]),
        minute=int(event_time.split(":")[1]),
        second=0, microsecond=0,
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FitAgent AI//Weekly Prescription//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:FitAgent Week {prescription.week_number} — {user_name}",
        "X-WR-TIMEZONE:Asia/Kolkata",
    ]

    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    week_id = hashlib.sha1(
        f"{prescription.user_id}-{prescription.week_number}".encode()
    ).hexdigest()[:12]

    for day in prescription.workout_plan.days:
        offset = _parse_day_offset(day.day_name)
        day_start = start_date + timedelta(days=offset)
        day_end = day_start + timedelta(minutes=duration_minutes)

        # Build description — list of exercises
        desc_lines = [f"Focus: {day.focus}", ""]
        for ex in day.exercises:
            reps = ex.reps or (f"{ex.duration_minutes} min" if ex.duration_minutes else "?")
            sets = ex.sets or 1
            desc_lines.append(f"• {ex.name} — {sets}×{reps} (rest {ex.rest_seconds}s)")
        description = _ics_escape("\n".join(desc_lines))

        summary = _ics_escape(f"💪 {day.focus} — FitAgent Week {prescription.week_number}")
        uid = f"{week_id}-{offset}@fitagent.ai"

        lines.extend([
            "BEGIN:VEVENT",
            _fold_line(f"UID:{uid}"),
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{day_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{day_end.strftime('%Y%m%dT%H%M%S')}",
            _fold_line(f"SUMMARY:{summary}"),
            _fold_line(f"DESCRIPTION:{description}"),
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:FitAgent workout reminder",
            "TRIGGER:-PT30M",
            "END:VALARM",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    # ICS uses CRLF line endings per spec
    output_path.write_text("\r\n".join(lines), encoding="utf-8")
    return output_path


# ── Self-test with a dummy prescription ───────────────────────────────────────

if __name__ == "__main__":
    from schemas import (
        WorkoutPlan, WorkoutDay, Exercise,
        NutritionPlan, DailyNutritionPlan, Meal,
        AdaptationSignal,
    )

    # Build a sample prescription
    wp = WorkoutPlan(
        user_id="test_user",
        week_number=1,
        weekly_volume_sets=48,
        notes="Push/Pull/Legs split with progressive overload",
        days=[
            WorkoutDay(
                day_name="Monday", focus="Push",
                exercises=[
                    Exercise(name="Bench Press", sets=4, reps="8-12", rest_seconds=90),
                    Exercise(name="Overhead Press", sets=3, reps="10-12", rest_seconds=90),
                ],
            ),
            WorkoutDay(
                day_name="Wednesday", focus="Pull",
                exercises=[
                    Exercise(name="Pull-ups", sets=4, reps="6-10", rest_seconds=120),
                    Exercise(name="Bent Over Row", sets=3, reps="8-12", rest_seconds=90),
                ],
            ),
        ],
    )
    np = NutritionPlan(
        user_id="test_user",
        week_number=1,
        target_calories=2600,
        target_protein_g=140,
        notes="High-protein vegetarian",
        daily_plans=[
            DailyNutritionPlan(
                day_name="Monday",
                total_calories=2620, total_protein_g=140,
                total_carbs_g=300, total_fats_g=75,
                meals=[
                    Meal(
                        meal_name="Breakfast",
                        foods=["100g oats", "200ml milk", "1 banana"],
                        calories=450, protein_g=18, carbs_g=70, fats_g=8,
                    ),
                    Meal(
                        meal_name="Lunch",
                        foods=["150g rajma", "1 cup brown rice", "100g curd"],
                        calories=650, protein_g=30, carbs_g=100, fats_g=10,
                    ),
                ],
            ),
        ],
    )
    p = WeeklyPrescription(
        user_id="test_user",
        week_number=1,
        workout_plan=wp, nutrition_plan=np,
        orchestrator_notes=(
            "Week 1 is about building the base. Focus on form over load, "
            "hit all meals, and log every session so we can adapt next week."
        ),
        adaptation_signals=[
            AdaptationSignal(
                user_id="test_user",
                signal_type="progress",
                severity="low",
                description="Fresh start — no history yet",
                recommended_action="Log consistently for 2 weeks",
            ),
        ],
    )

    print("── Export Tests ──\n")

    # ICS — no dependencies
    ics_path = Path(__file__).parent.parent / "data" / "exports" / "test.ics"
    export_prescription_to_ics(p, ics_path, user_name="Coffeine")
    print(f"  ✓ ICS written: {ics_path}  ({ics_path.stat().st_size} bytes)")

    # PDF — requires reportlab
    if HAS_REPORTLAB:
        pdf_path = Path(__file__).parent.parent / "data" / "exports" / "test.pdf"
        export_prescription_to_pdf(p, pdf_path, user_name="Coffeine")
        print(f"  ✓ PDF written: {pdf_path}  ({pdf_path.stat().st_size} bytes)")
    else:
        print("  ⚠ PDF skipped (install reportlab: pip install reportlab)")

    print("\n  [Export] Tests passed")