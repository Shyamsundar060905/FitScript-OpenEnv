"""
Authentication v2 — bcrypt password hashing + SQLite user store.

Replaces the v1 SHA-256 + auth.json approach. SHA-256 is a fast hash,
unsuitable for passwords — an attacker with the file can brute-force
billions of guesses per second on a GPU. bcrypt is adaptive (configurable
cost factor) and designed specifically for password storage.

Migration:
  If a legacy data/users/auth.json exists, we migrate it on first run:
  SHA-256 hashes become "legacy:<hex>" placeholders. Users must log in
  once (which re-hashes) before the legacy hash is replaced. This avoids
  forced password resets while still upgrading users over time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


# ── Schema ────────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    """Read AUTH_DB from config at call time — respects test overrides."""
    db_path = config.AUTH_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """Create tables if not exist. Safe to call multiple times."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username        TEXT    PRIMARY KEY,
                user_id         TEXT    UNIQUE NOT NULL,
                password_hash   TEXT    NOT NULL,
                created_at      TEXT    NOT NULL,
                last_login_at   TEXT,
                failed_attempts INTEGER DEFAULT 0,
                locked_until    TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_token   TEXT    PRIMARY KEY,
                username        TEXT    NOT NULL,
                created_at      TEXT    NOT NULL,
                expires_at      TEXT    NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
        """)
    _migrate_legacy_auth()


def _migrate_legacy_auth():
    """Pull in users from the old auth.json if it exists."""
    legacy = config.USERS_DIR / "auth.json"
    if not legacy.exists():
        return
    try:
        data = json.loads(legacy.read_text())
    except Exception:
        return

    with _connect() as conn:
        for username, info in data.items():
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            ).fetchone()
            if exists:
                continue
            conn.execute("""
                INSERT INTO users (username, user_id, password_hash, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                username,
                info.get("user_id", f"user_{username.lower()}"),
                f"legacy:{info.get('password', '')}",
                info.get("created_at", ""),
            ))
    try:
        legacy.rename(legacy.with_suffix(".json.migrated"))
    except Exception:
        pass


# ── Password hashing ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash a password using bcrypt (cost 12)."""
    if not HAS_BCRYPT:
        raise RuntimeError(
            "bcrypt is required. Install with: pip install bcrypt"
        )
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash. Handles legacy SHA-256."""
    if stored_hash.startswith("legacy:"):
        legacy_hex = stored_hash[len("legacy:"):]
        return hashlib.sha256(password.encode()).hexdigest() == legacy_hex
    if not HAS_BCRYPT:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


# ── Validation ────────────────────────────────────────────────────────────────

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.-]{3,32}$')


def _validate_username(username: str) -> Optional[str]:
    if not username:
        return "Username is required"
    if not USERNAME_RE.match(username):
        return "Username must be 3-32 chars: letters, digits, _ . -"
    return None


def _validate_password(password: str) -> Optional[str]:
    if not password or len(password) < 8:
        return "Password must be at least 8 characters"
    if len(password) > 128:
        return "Password is too long (max 128 chars)"
    classes = sum([
        bool(re.search(r'[a-z]', password)),
        bool(re.search(r'[A-Z]', password)),
        bool(re.search(r'\d', password)),
        bool(re.search(r'[^a-zA-Z0-9]', password)),
    ])
    if classes < 2:
        return "Password must include at least two of: lowercase, uppercase, digit, symbol"
    return None


# ── Public API ────────────────────────────────────────────────────────────────

class AuthError(Exception):
    """Raised on auth failures with user-safe messages."""


def create_account(username: str, password: str) -> str:
    """Create a new account. Returns user_id on success."""
    init_auth_db()
    err = _validate_username(username)
    if err:
        raise AuthError(err)
    err = _validate_password(password)
    if err:
        raise AuthError(err)

    user_id = f"user_{username.lower().replace(' ', '_')}"
    pw_hash = _hash_password(password)

    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO users (username, user_id, password_hash, created_at)
                VALUES (?, ?, ?, ?)
            """, (username, user_id, pw_hash, _iso_now()))
    except sqlite3.IntegrityError:
        raise AuthError("Username already taken")

    return user_id


def verify_login(username: str, password: str) -> Optional[str]:
    """Verify credentials. Returns user_id on success, None on failure."""
    init_auth_db()
    err = _validate_username(username)
    if err:
        return None

    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if not row:
            _hash_password("decoy-" + secrets.token_hex(8))
            return None

        if row["locked_until"]:
            if row["locked_until"] > _iso_now():
                return None
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
                (username,),
            )

        if not _verify_password(password, row["password_hash"]):
            attempts = (row["failed_attempts"] or 0) + 1
            lock_until = None
            if attempts >= 5:
                from datetime import datetime, timedelta, timezone
                lock_until = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            conn.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?",
                (attempts, lock_until, username),
            )
            return None

        if row["password_hash"].startswith("legacy:"):
            new_hash = _hash_password(password)
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (new_hash, username),
            )

        conn.execute("""
            UPDATE users
            SET last_login_at = ?, failed_attempts = 0, locked_until = NULL
            WHERE username = ?
        """, (_iso_now(), username))

        return row["user_id"]


def change_password(username: str, old_password: str, new_password: str) -> None:
    init_auth_db()
    uid = verify_login(username, old_password)
    if not uid:
        raise AuthError("Current password is incorrect")

    err = _validate_password(new_password)
    if err:
        raise AuthError(err)

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (_hash_password(new_password), username),
        )


def get_user_info(username: str) -> Optional[dict]:
    init_auth_db()
    with _connect() as conn:
        row = conn.execute("""
            SELECT username, user_id, created_at, last_login_at
            FROM users WHERE username = ?
        """, (username,)).fetchone()
    return dict(row) if row else None


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    # Point config.AUTH_DB at a fresh temp file. _connect() reads this at
    # call time so the override takes effect without any global juggling.
    config.AUTH_DB = Path(tempfile.mkdtemp()) / "auth_test.db"

    # Use a random username so repeated test runs don't collide
    test_username = f"testuser_{secrets.token_hex(4)}"

    print("── Auth v2 Tests ──\n")

    # Short username
    try:
        create_account("ab", "Password123!")
        print("  ✗ Should reject short username")
    except AuthError as e:
        print(f"  ✓ Rejects short username: {e}")

    # Weak password
    try:
        create_account(test_username, "short")
        print("  ✗ Should reject short password")
    except AuthError as e:
        print(f"  ✓ Rejects weak password: {e}")

    # Valid creation
    try:
        create_account(test_username, "ValidPass123")
        uid = verify_login(test_username, "ValidPass123")
        assert uid == f"user_{test_username}"
        print(f"  ✓ Creates valid account -> {uid}")
    except AuthError as e:
        print(f"  ✗ Valid creation failed: {e}")

    # Duplicate
    try:
        create_account(test_username, "DifferentPass123")
        print("  ✗ Should reject duplicate")
    except AuthError as e:
        print(f"  ✓ Rejects duplicate username: {e}")

    # Wrong password
    assert verify_login(test_username, "WrongPassword123") is None
    print("  ✓ Rejects wrong password")

    # Lockout — 5 bad attempts, then a good one that should still fail
    for i in range(5):
        verify_login(test_username, f"BadPass{i}1!")
    assert verify_login(test_username, "ValidPass123") is None
    print("  ✓ Locks out after 5 failed attempts")

    print("\n  [Auth v2] Tests passed")