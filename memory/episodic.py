"""
Episodic memory v2.

Extensions over v1:
  - `user_constraints` table: persistent physical constraints
    (knee pain, etc.) that survive across sessions.
  - `progress_photos` table: metadata for uploaded progress photos.
  - `detect_weight_plateau()` now delegates to utils.plateau for
    statistical analysis.
  - `log_exercise()` now accepts target_sets/target_reps so progressive
    overload history is complete.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import EPISODIC_DB, PHOTOS_DIR
from schemas import ProgressLog
from utils.plateau import detect_plateau as _statistical_plateau, PlateauResult


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(EPISODIC_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables. Safe to call multiple times."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS progress_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                weight_kg       REAL,
                workout_completed INTEGER DEFAULT 0,
                workout_rating  INTEGER,
                calories_eaten  REAL,
                notes           TEXT    DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS workout_plans (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                week_number     INTEGER NOT NULL,
                plan_json       TEXT    NOT NULL,
                generated_at    TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS nutrition_plans (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                week_number     INTEGER NOT NULL,
                plan_json       TEXT    NOT NULL,
                generated_at    TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS adaptation_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                signal_type     TEXT    NOT NULL,
                description     TEXT    NOT NULL,
                action_taken    TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS exercise_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                exercise_name   TEXT    NOT NULL,
                sets_completed  INTEGER,
                reps_completed  TEXT,
                weight_kg       REAL    DEFAULT 0,
                target_sets     INTEGER,
                target_reps     TEXT,
                rpe             INTEGER,
                notes           TEXT    DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_constraints (
                user_id         TEXT    NOT NULL,
                constraint_text TEXT    NOT NULL,
                category        TEXT    DEFAULT 'injury',
                is_active       INTEGER DEFAULT 1,
                added_at        TEXT    DEFAULT (datetime('now')),
                resolved_at     TEXT,
                PRIMARY KEY (user_id, constraint_text)
            );

            CREATE TABLE IF NOT EXISTS progress_photos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                photo_path      TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                weight_kg       REAL,
                note            TEXT    DEFAULT '',
                uploaded_at     TEXT    DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_progress_user_date
                ON progress_logs (user_id, date);
            CREATE INDEX IF NOT EXISTS idx_exercise_user
                ON exercise_logs (user_id, exercise_name, date);
            CREATE INDEX IF NOT EXISTS idx_constraints_user
                ON user_constraints (user_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_photos_user_date
                ON progress_photos (user_id, date);
        """)

        # Migration: add target columns to exercise_logs if missing
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(exercise_logs)").fetchall()]
        if "target_sets" not in cols:
            conn.execute("ALTER TABLE exercise_logs ADD COLUMN target_sets INTEGER")
        if "target_reps" not in cols:
            conn.execute("ALTER TABLE exercise_logs ADD COLUMN target_reps TEXT")


# ── Progress logs ─────────────────────────────────────────────────────────────

def log_progress(entry: ProgressLog):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO progress_logs
              (user_id, date, weight_kg, workout_completed, workout_rating,
               calories_eaten, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.user_id, entry.date, entry.weight_kg,
            int(entry.workout_completed), entry.workout_rating,
            entry.calories_eaten, entry.notes,
        ))


def get_recent_logs(user_id: str, days: int = 30) -> List[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM progress_logs
            WHERE user_id = ? AND date >= ?
            ORDER BY date ASC
        """, (user_id, cutoff)).fetchall()
    return [dict(r) for r in rows]


def get_weight_series(user_id: str, days: int = 30) -> List[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, weight_kg FROM progress_logs
            WHERE user_id = ? AND date >= ? AND weight_kg IS NOT NULL
            ORDER BY date ASC
        """, (user_id, cutoff)).fetchall()
    return [dict(r) for r in rows]


# ── Plans ─────────────────────────────────────────────────────────────────────

def save_workout_plan(user_id: str, week_number: int, plan_json: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO workout_plans (user_id, week_number, plan_json, generated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, week_number, json.dumps(plan_json), datetime.now().isoformat()))


def save_nutrition_plan(user_id: str, week_number: int, plan_json: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO nutrition_plans (user_id, week_number, plan_json, generated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, week_number, json.dumps(plan_json), datetime.now().isoformat()))


def get_latest_workout_plan(user_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT plan_json FROM workout_plans
            WHERE user_id = ?
            ORDER BY week_number DESC, generated_at DESC
            LIMIT 1
        """, (user_id,)).fetchone()
    return json.loads(row["plan_json"]) if row else None


# ── Adaptation ────────────────────────────────────────────────────────────────

def log_adaptation_event(user_id: str, signal_type: str, description: str, action: str = ""):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO adaptation_events (user_id, date, signal_type, description, action_taken)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, datetime.now().strftime("%Y-%m-%d"), signal_type, description, action))


def get_adaptation_history(user_id: str) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM adaptation_events
            WHERE user_id = ?
            ORDER BY date DESC
        """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


# ── Plateau detection (delegates to utils.plateau) ────────────────────────────

def detect_weight_plateau(user_id: str, goal: str = "maintenance",
                           window_days: int = 14) -> dict:
    """
    Statistical plateau detection.
    Returns a dict (backward-compatible with v1 callers) plus richer
    fields from the new engine.
    """
    series = get_weight_series(user_id, days=window_days + 7)  # extra for rolling window
    result: PlateauResult = _statistical_plateau(
        series, goal=goal, window_days=window_days
    )

    return {
        # v1 compatibility fields
        "plateau": result.status == "plateau",
        "change_kg": round(
            (series[-1]["weight_kg"] - series[0]["weight_kg"]) if series else 0, 2
        ),
        "data_points": result.data_points,
        # v2 richer fields
        "status": result.status,
        "slope_kg_per_week": result.slope_kg_per_week,
        "confidence": result.confidence,
        "reason": result.reason,
        "first_date": result.first_date,
        "last_date": result.last_date,
        "expected_slope_range": result.expected_slope_range,
    }


def clear_user_data(user_id: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM progress_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM adaptation_events WHERE user_id = ?", (user_id,))


# ── Exercise history (progressive overload) ───────────────────────────────────

def log_exercise(
    user_id: str,
    date: str,
    exercise_name: str,
    sets: int,
    reps: str,
    weight_kg: float = 0,
    target_sets: Optional[int] = None,
    target_reps: Optional[str] = None,
    rpe: Optional[int] = None,
    notes: str = "",
):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO exercise_logs
              (user_id, date, exercise_name, sets_completed, reps_completed,
               weight_kg, target_sets, target_reps, rpe, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, exercise_name, sets, reps, weight_kg,
              target_sets, target_reps, rpe, notes))


def get_exercise_history(
    user_id: str,
    exercise_name: str,
    days: int = 60,
    limit: int = 10,
) -> list:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, sets_completed, reps_completed, weight_kg,
                   target_sets, target_reps, rpe, notes
            FROM exercise_logs
            WHERE user_id = ? AND date >= ?
            AND LOWER(exercise_name) LIKE LOWER(?)
            ORDER BY date ASC
            LIMIT ?
        """, (user_id, cutoff, f"%{exercise_name}%", limit)).fetchall()
    return [dict(r) for r in rows]


def get_all_logged_exercises(user_id: str, days: int = 30) -> list:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT exercise_name
            FROM exercise_logs
            WHERE user_id = ? AND date >= ?
            ORDER BY exercise_name
        """, (user_id, cutoff)).fetchall()
    return [r["exercise_name"] for r in rows]


def get_recent_exercise_summary(user_id: str, days: int = 14) -> str:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT exercise_name,
                   MAX(date) as last_date,
                   sets_completed, reps_completed, weight_kg
            FROM exercise_logs
            WHERE user_id = ? AND date >= ?
            GROUP BY exercise_name
            ORDER BY last_date DESC
            LIMIT 15
        """, (user_id, cutoff)).fetchall()

    if not rows:
        return ""

    lines = ["Recent exercise performance (use for progressive overload):"]
    for r in rows:
        weight_str = f" at {r['weight_kg']}kg" if r['weight_kg'] > 0 else " (bodyweight)"
        lines.append(
            f"- {r['exercise_name']}: {r['sets_completed']}×{r['reps_completed']}"
            f"{weight_str} on {r['last_date']}"
        )
    return "\n".join(lines)


# ── User constraints (persistent) ─────────────────────────────────────────────

def add_constraint(user_id: str, constraint_text: str, category: str = "injury"):
    """Add or reactivate a user constraint."""
    init_db()
    with get_connection() as conn:
        # Upsert: reactivate if exists
        existing = conn.execute("""
            SELECT is_active FROM user_constraints
            WHERE user_id = ? AND constraint_text = ?
        """, (user_id, constraint_text)).fetchone()
        if existing:
            conn.execute("""
                UPDATE user_constraints
                SET is_active = 1, resolved_at = NULL
                WHERE user_id = ? AND constraint_text = ?
            """, (user_id, constraint_text))
        else:
            conn.execute("""
                INSERT INTO user_constraints (user_id, constraint_text, category)
                VALUES (?, ?, ?)
            """, (user_id, constraint_text, category))


def resolve_constraint(user_id: str, constraint_text: str):
    """Mark a constraint as resolved."""
    init_db()
    with get_connection() as conn:
        conn.execute("""
            UPDATE user_constraints
            SET is_active = 0, resolved_at = datetime('now')
            WHERE user_id = ? AND constraint_text = ?
        """, (user_id, constraint_text))


def get_active_constraints(user_id: str) -> list[str]:
    """Return list of active constraint texts for this user."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT constraint_text FROM user_constraints
            WHERE user_id = ? AND is_active = 1
            ORDER BY added_at DESC
        """, (user_id,)).fetchall()
    return [r["constraint_text"] for r in rows]


def set_constraints(user_id: str, constraints: list[str]):
    """Replace all active constraints for this user. Resolves anything not in the new set."""
    init_db()
    with get_connection() as conn:
        conn.execute("""
            UPDATE user_constraints SET is_active = 0, resolved_at = datetime('now')
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        for c in constraints:
            if not c or not c.strip():
                continue
            existing = conn.execute("""
                SELECT 1 FROM user_constraints
                WHERE user_id = ? AND constraint_text = ?
            """, (user_id, c)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE user_constraints
                    SET is_active = 1, resolved_at = NULL
                    WHERE user_id = ? AND constraint_text = ?
                """, (user_id, c))
            else:
                conn.execute("""
                    INSERT INTO user_constraints (user_id, constraint_text, category)
                    VALUES (?, ?, 'injury')
                """, (user_id, c))


# ── Progress photos ───────────────────────────────────────────────────────────

def save_photo_metadata(user_id: str, photo_path: str, date: str,
                         weight_kg: Optional[float] = None, note: str = "") -> int:
    """Record that a photo was saved. Returns the row id."""
    init_db()
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO progress_photos (user_id, photo_path, date, weight_kg, note)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, photo_path, date, weight_kg, note))
        return cur.lastrowid


def get_photos(user_id: str, limit: int = 20) -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM progress_photos
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def delete_photo(user_id: str, photo_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        row = conn.execute("""
            SELECT photo_path FROM progress_photos
            WHERE id = ? AND user_id = ?
        """, (photo_id, user_id)).fetchone()
        if not row:
            return False
        try:
            p = Path(row["photo_path"])
            if p.exists():
                p.unlink()
        except Exception:
            pass
        conn.execute("DELETE FROM progress_photos WHERE id = ?", (photo_id,))
    return True


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("── Episodic v2 Tests ──\n")

    # Constraints
    set_constraints("u1", ["knee pain — avoid squats", "shoulder pain"])
    active = get_active_constraints("u1")
    assert len(active) == 2
    print(f"  ✓ Set 2 constraints -> {active}")

    resolve_constraint("u1", "shoulder pain")
    active = get_active_constraints("u1")
    assert len(active) == 1
    print(f"  ✓ Resolve one -> {active}")

    set_constraints("u1", [])
    assert get_active_constraints("u1") == []
    print("  ✓ Set empty list clears all")

    # Plateau detection
    from datetime import datetime as _dt, timedelta as _td
    base = _dt.now() - _td(days=21)
    for i in range(21):
        log_progress(ProgressLog(
            user_id="u_plateau",
            date=(base + _td(days=i)).strftime("%Y-%m-%d"),
            weight_kg=78.0 + (i * 0.02) + (0.3 if i % 3 == 0 else -0.2),
        ))
    result = detect_weight_plateau("u_plateau", goal="weight_loss")
    print(f"  ✓ Plateau detection: status={result['status']} "
          f"slope={result['slope_kg_per_week']:+.2f} kg/wk "
          f"conf={result['confidence']}")

    print("\n  [Episodic v2] Tests passed")