"""
Per-user rate limiting.

Two limits enforced:
  1. Cooldown: minimum seconds between consecutive agent runs
     (prevents rapid-fire spam)
  2. Daily cap: max agent runs per user per 24 hours
     (prevents API quota abuse)

Backed by SQLite for durability across Streamlit reruns. Uses a sliding
window rather than fixed day boundaries so a user can't burn through
20 runs at 23:59 and another 20 at 00:01.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config


def _connect() -> sqlite3.Connection:
    """Read EPISODIC_DB from config at call time — respects test overrides."""
    db_path = config.EPISODIC_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                action      TEXT    NOT NULL,
                ts          REAL    NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rl_user_action_ts
            ON rate_limit_events (user_id, action, ts)
        """)


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str = ""
    retry_after_seconds: int = 0
    remaining_today: int = 0


def check_and_record(
    user_id: str,
    action: str = "agent_run",
    cooldown_seconds: int = None,
    daily_limit: int = None,
) -> RateLimitDecision:
    """
    Check rate limits and record the attempt atomically.

    If allowed=True, the event is recorded. If allowed=False, nothing is
    recorded (user can't use repeated rejected attempts to skew counts).
    """
    # Read defaults from config at call time (testable)
    if cooldown_seconds is None:
        cooldown_seconds = config.AGENT_RUN_COOLDOWN_SECONDS
    if daily_limit is None:
        daily_limit = config.MAX_AGENT_RUNS_PER_DAY

    _init_schema()
    now = time.time()
    one_day_ago = now - 86400

    with _connect() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS cnt, MAX(ts) AS last_ts
            FROM rate_limit_events
            WHERE user_id = ? AND action = ? AND ts > ?
        """, (user_id, action, one_day_ago)).fetchone()

        count = row["cnt"] or 0
        last_ts = row["last_ts"] or 0

        since_last = now - last_ts
        if last_ts and since_last < cooldown_seconds:
            return RateLimitDecision(
                allowed=False,
                reason="cooldown",
                retry_after_seconds=int(cooldown_seconds - since_last) + 1,
                remaining_today=max(0, daily_limit - count),
            )

        if count >= daily_limit:
            oldest = conn.execute("""
                SELECT MIN(ts) AS oldest FROM rate_limit_events
                WHERE user_id = ? AND action = ? AND ts > ?
            """, (user_id, action, one_day_ago)).fetchone()["oldest"]
            retry_after = int((oldest + 86400) - now) + 1 if oldest else 3600
            return RateLimitDecision(
                allowed=False,
                reason="daily_limit",
                retry_after_seconds=retry_after,
                remaining_today=0,
            )

        conn.execute("""
            INSERT INTO rate_limit_events (user_id, action, ts) VALUES (?, ?, ?)
        """, (user_id, action, now))

    return RateLimitDecision(
        allowed=True,
        remaining_today=daily_limit - count - 1,
    )


def get_usage_stats(user_id: str, action: str = "agent_run") -> dict:
    """Return usage stats for display to the user."""
    _init_schema()
    now = time.time()
    one_day_ago = now - 86400
    one_hour_ago = now - 3600

    with _connect() as conn:
        today = conn.execute("""
            SELECT COUNT(*) AS cnt FROM rate_limit_events
            WHERE user_id = ? AND action = ? AND ts > ?
        """, (user_id, action, one_day_ago)).fetchone()["cnt"] or 0
        hour = conn.execute("""
            SELECT COUNT(*) AS cnt FROM rate_limit_events
            WHERE user_id = ? AND action = ? AND ts > ?
        """, (user_id, action, one_hour_ago)).fetchone()["cnt"] or 0

    return {
        "used_today": today,
        "used_this_hour": hour,
        "remaining_today": max(0, config.MAX_AGENT_RUNS_PER_DAY - today),
        "daily_limit": config.MAX_AGENT_RUNS_PER_DAY,
    }


# Self-test
if __name__ == "__main__":
    import tempfile

    # Override config at call time — _connect() reads it fresh
    config.EPISODIC_DB = Path(tempfile.mkdtemp()) / "test.db"

    print("── Rate Limit Tests ──\n")

    d = check_and_record("test_user", cooldown_seconds=5, daily_limit=3)
    assert d.allowed, d.reason
    print(f"  ✓ First request allowed (remaining={d.remaining_today})")

    d = check_and_record("test_user", cooldown_seconds=5, daily_limit=3)
    assert not d.allowed
    assert d.reason == "cooldown"
    print(f"  ✓ Cooldown blocks 2nd request (retry in {d.retry_after_seconds}s)")

    time.sleep(5.5)
    d = check_and_record("test_user", cooldown_seconds=5, daily_limit=3)
    assert d.allowed
    print(f"  ✓ 2nd request allowed after cooldown (remaining={d.remaining_today})")

    time.sleep(5.5)
    d = check_and_record("test_user", cooldown_seconds=5, daily_limit=3)
    assert d.allowed
    print(f"  ✓ 3rd request allowed (remaining={d.remaining_today})")

    time.sleep(5.5)
    d = check_and_record("test_user", cooldown_seconds=5, daily_limit=3)
    assert not d.allowed
    assert d.reason == "daily_limit"
    print(f"  ✓ 4th request blocked by daily cap (retry in {d.retry_after_seconds}s)")

    print("\n  [Rate limit] Tests passed")