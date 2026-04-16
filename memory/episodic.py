"""
Episodic memory — SQLite database for user progress logs, workout history,
and meal logs. This is the "what has this user done over time" memory.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import EPISODIC_DB
from schemas import ProgressLog


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(EPISODIC_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist. Safe to call multiple times."""
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

            CREATE INDEX IF NOT EXISTS idx_progress_user_date
                ON progress_logs (user_id, date);
        """)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS exercise_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                exercise_name   TEXT    NOT NULL,
                sets_completed  INTEGER,
                reps_completed  TEXT,
                weight_kg       REAL    DEFAULT 0,
                rpe             INTEGER,
                notes           TEXT    DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_exercise_user
                ON exercise_logs (user_id, exercise_name, date);
        """)
    print("  [DB] ✓ Episodic database initialized")


# ── Progress log CRUD ─────────────────────────────────────────────────────────

def log_progress(entry: ProgressLog):
    """Insert a new progress log entry."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO progress_logs
              (user_id, date, weight_kg, workout_completed, workout_rating, calories_eaten, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.user_id, entry.date, entry.weight_kg,
            int(entry.workout_completed), entry.workout_rating,
            entry.calories_eaten, entry.notes
        ))


def get_recent_logs(user_id: str, days: int = 30) -> List[dict]:
    """Return progress logs for the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM progress_logs
            WHERE user_id = ? AND date >= ?
            ORDER BY date ASC
        """, (user_id, cutoff)).fetchall()
    return [dict(r) for r in rows]


def get_weight_series(user_id: str, days: int = 30) -> List[dict]:
    """Return just date + weight for trend analysis."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, weight_kg FROM progress_logs
            WHERE user_id = ? AND date >= ? AND weight_kg IS NOT NULL
            ORDER BY date ASC
        """, (user_id, cutoff)).fetchall()
    return [dict(r) for r in rows]


# ── Plan storage ──────────────────────────────────────────────────────────────

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


# ── Adaptation event log ──────────────────────────────────────────────────────

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

def clear_user_data(user_id: str):
    """Delete all progress logs for a user. Used for clean demo runs."""
    with get_connection() as conn:
        conn.execute("DELETE FROM progress_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM adaptation_events WHERE user_id = ?", (user_id,))
    print(f"  [DB] ✓ Cleared all data for {user_id}")
# ── Quick test ────────────────────────────────────────────────────────────────
# ── Progressive overload tracking ─────────────────────────────────────────────

def init_exercise_log():
    """Create exercise log table if not exists."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS exercise_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                exercise_name   TEXT    NOT NULL,
                sets_completed  INTEGER,
                reps_completed  TEXT,
                weight_kg       REAL    DEFAULT 0,
                rpe             INTEGER,
                notes           TEXT    DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_exercise_user
                ON exercise_logs (user_id, exercise_name, date);
        """)


def log_exercise(user_id: str, date: str, exercise_name: str,
                 sets: int, reps: str, weight_kg: float = 0,
                 rpe: int = None, notes: str = ""):
    """Log a completed exercise with weight and reps."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO exercise_logs
              (user_id, date, exercise_name, sets_completed,
               reps_completed, weight_kg, rpe, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, exercise_name, sets, reps,
              weight_kg, rpe, notes))


def get_exercise_history(user_id: str, exercise_name: str,
                         days: int = 60) -> list:
    """Get history for a specific exercise."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, sets_completed, reps_completed,
                   weight_kg, rpe, notes
            FROM exercise_logs
            WHERE user_id = ? AND date >= ?
            AND LOWER(exercise_name) LIKE LOWER(?)
            ORDER BY date DESC
            LIMIT 10
        """, (user_id, cutoff, f"%{exercise_name}%")).fetchall()
    return [dict(r) for r in rows]


def get_all_logged_exercises(user_id: str, days: int = 30) -> list:
    """Get all exercises logged recently, deduplicated by name."""
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
    """
    Returns a text summary of recent exercise performance.
    This gets injected into the Fitness Agent prompt.
    """
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

if __name__ == "__main__":
    init_db()

    # Insert a test log
    test_log = ProgressLog(
        user_id="user_001",
        date="2026-04-14",
        weight_kg=75.2,
        workout_completed=True,
        workout_rating=4,
        calories_eaten=2100.0,
        notes="Felt strong today"
    )
    log_progress(test_log)

    # Read it back
    logs = get_recent_logs("user_001", days=7)
    print(f"  Recent logs: {logs}")
    print("  [DB] ✓ Episodic memory test passed")
