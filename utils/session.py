"""
Persistent session tokens.

Streamlit's st.session_state is wiped by browser refresh (F5). To survive
refreshes, we store a session token in the URL via st.query_params and
back it with the `sessions` table that utils/auth.py already creates.

Flow:
  1. After successful login, create a session token in SQLite, write it
     to the URL via st.query_params.
  2. On every page load, check if URL has ?session=<token>. If yes and
     the token is valid + unexpired, hydrate session_state from it.
  3. On logout, delete the token from SQLite and clear the URL param.

Tokens expire after 30 days. Cleanup of expired sessions runs on read.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config


SESSION_TTL_DAYS = 30


def _connect() -> sqlite3.Connection:
    db_path = config.AUTH_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema():
    """Create sessions table if it doesn't exist (utils/auth.py already does this,
    but we call it defensively in case session.py is imported before auth.py)."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_token   TEXT    PRIMARY KEY,
                username        TEXT    NOT NULL,
                created_at      TEXT    NOT NULL,
                expires_at      TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at)"
        )


def create_session(username: str) -> str:
    """Create a new session token for a logged-in user. Returns the token."""
    _ensure_schema()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=SESSION_TTL_DAYS)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (session_token, username, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (token, username, now.isoformat(), expires.isoformat()),
        )
    return token


def lookup_session(token: str) -> Optional[dict]:
    """
    Look up a session token. Returns {username, user_id} on hit, None otherwise.
    Also opportunistically deletes expired sessions on each lookup.
    """
    if not token:
        return None
    _ensure_schema()
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        # Sweep expired tokens
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso,))

        row = conn.execute("""
            SELECT s.username, u.user_id
            FROM sessions s
            JOIN users u ON s.username = u.username
            WHERE s.session_token = ? AND s.expires_at > ?
        """, (token, now_iso)).fetchone()

    return dict(row) if row else None


def destroy_session(token: str) -> bool:
    """Delete a session token. Returns True if the token existed."""
    if not token:
        return False
    _ensure_schema()
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM sessions WHERE session_token = ?", (token,)
        )
        return cur.rowcount > 0


def destroy_all_user_sessions(username: str) -> int:
    """Destroy all sessions for a user. Returns count of sessions removed."""
    _ensure_schema()
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM sessions WHERE username = ?", (username,)
        )
        return cur.rowcount


# Self-test
if __name__ == "__main__":
    import tempfile
    config.AUTH_DB = Path(tempfile.mkdtemp()) / "session_test.db"

    # Create a test user first (sessions has a FK reference)
    from utils.auth import init_auth_db, create_account
    init_auth_db()
    create_account("test_session_user", "TestPass123")

    print("── Session token tests ──\n")

    # Create
    token = create_session("test_session_user")
    print(f"  ✓ Created token: {token[:16]}...")

    # Lookup
    info = lookup_session(token)
    assert info is not None
    assert info["username"] == "test_session_user"
    print(f"  ✓ Lookup returns user_id={info['user_id']}")

    # Bad token
    assert lookup_session("not-a-real-token") is None
    print("  ✓ Bad token returns None")

    # Destroy
    assert destroy_session(token) is True
    assert lookup_session(token) is None
    print("  ✓ Destroy works, post-destroy lookup is None")

    # Destroy non-existent
    assert destroy_session("ghost") is False
    print("  ✓ Destroy non-existent returns False")

    print("\n  [Session] Tests passed")