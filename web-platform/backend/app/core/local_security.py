"""Authentication helpers for the Doka Personal Local Edition.

Local token revocation and refresh rotation are stored in a small SQLite file.
This keeps Personal Local independent of cloud databases/Redis while preserving
logout and one-time refresh semantics across backend restarts and processes.
"""

from datetime import datetime, timedelta, timezone
import secrets
import sqlite3
from pathlib import Path
from typing import Optional
import threading
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt.exceptions import InvalidTokenError as JWTError

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)

_login_guard = threading.Lock()
_login_failures: dict[str, list[float]] = {}


def _connect_token_state() -> sqlite3.Connection:
    path = Path(settings.LOCAL_AUTH_STATE_PATH).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=15)
    connection.execute("PRAGMA busy_timeout = 15000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS local_token_state (
            token_id TEXT PRIMARY KEY,
            state TEXT NOT NULL CHECK (state IN ('revoked', 'used_refresh')),
            expires_at REAL NOT NULL
        )
        """
    )
    return connection


def _login_key(username: str, client_host: str | None) -> str:
    return f"{(username or '').strip().casefold()}|{client_host or 'unknown'}"


def login_is_locked(username: str, client_host: str | None = None) -> bool:
    key = _login_key(username, client_host)
    now = time.monotonic()
    window = max(1, int(settings.LOCKOUT_DURATION_MINUTES)) * 60
    with _login_guard:
        failures = [stamp for stamp in _login_failures.get(key, []) if now - stamp < window]
        if failures:
            _login_failures[key] = failures
        else:
            _login_failures.pop(key, None)
        return len(failures) >= max(1, int(settings.MAX_LOGIN_ATTEMPTS))


def record_login_failure(username: str, client_host: str | None = None) -> None:
    key = _login_key(username, client_host)
    now = time.monotonic()
    window = max(1, int(settings.LOCKOUT_DURATION_MINUTES)) * 60
    with _login_guard:
        failures = [stamp for stamp in _login_failures.get(key, []) if now - stamp < window]
        failures.append(now)
        _login_failures[key] = failures


def clear_login_failures(username: str, client_host: str | None = None) -> None:
    with _login_guard:
        _login_failures.pop(_login_key(username, client_host), None)


def create_local_access_token(username: str) -> str:
    # Fail before issuing credentials if the durable revocation store is unavailable.
    connection = _connect_token_state()
    connection.close()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": username,
            "role": "admin",
            "type": "access",
            "jti": secrets.token_urlsafe(18),
            "sid": secrets.token_urlsafe(24),
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def create_local_refresh_token(username: str) -> str:
    connection = _connect_token_state()
    connection.close()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": username,
            "role": "admin",
            "type": "refresh",
            "jti": secrets.token_urlsafe(18),
            "sid": secrets.token_urlsafe(24),
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def decode_local_token(token: str, expected_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != expected_type or payload.get("role") != "admin":
            return None
        token_id = payload.get("jti")
        session_id = payload.get("sid")
        if not isinstance(token_id, str) or not token_id:
            return None
        now = time.time()
        connection = _connect_token_state()
        try:
            rows = connection.execute(
                "SELECT token_id, state, expires_at FROM local_token_state WHERE token_id IN (?, ?)",
                (f"jti:{token_id}", f"sid:{session_id}" if isinstance(session_id, str) else ""),
            ).fetchall()
            for stored_id, state, expiry in rows:
                if float(expiry) <= now:
                    connection.execute("DELETE FROM local_token_state WHERE token_id = ?", (stored_id,))
                    continue
                if stored_id.startswith("sid:") and state == "revoked":
                    return None
                if stored_id == f"jti:{token_id}" and (
                    state == "revoked" or (expected_type == "refresh" and state == "used_refresh")
                ):
                    return None
        finally:
            connection.close()
        return payload
    except (JWTError, sqlite3.Error, OSError, ValueError, TypeError):
        # Fail closed if durable session state cannot be read.
        return None


def invalidate_local_token(token: str) -> bool:
    """Persist token revocation until the token's natural expiry."""
    payload = decode_local_token(token, expected_type="access")
    if not payload:
        payload = decode_local_token(token, expected_type="refresh")
    if not payload:
        return False
    token_id = payload.get("jti")
    try:
        expiry = float(payload.get("exp"))
    except (TypeError, ValueError):
        return False
    if not isinstance(token_id, str) or not token_id:
        return False

    connection = None
    try:
        connection = _connect_token_state()
        connection.execute("BEGIN IMMEDIATE")
        state_keys = [f"jti:{token_id}"]
        session_id = payload.get("sid")
        if isinstance(session_id, str) and session_id:
            state_keys.append(f"sid:{session_id}")
        for state_key in state_keys:
            connection.execute(
                """
                INSERT INTO local_token_state (token_id, state, expires_at)
                VALUES (?, 'revoked', ?)
                ON CONFLICT(token_id) DO UPDATE SET state = 'revoked', expires_at = excluded.expires_at
                """,
                (state_key, expiry),
            )
        connection.commit()
        return True
    except sqlite3.Error:
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            connection.close()


def consume_local_refresh_token(token: str) -> Optional[dict]:
    """Atomically consume a refresh token once, including across process restarts."""
    payload = decode_local_token(token, expected_type="refresh")
    if not payload:
        return None
    token_id = payload.get("jti")
    try:
        expiry = float(payload.get("exp"))
    except (TypeError, ValueError):
        return None
    if not isinstance(token_id, str) or not token_id:
        return None

    connection = None
    try:
        connection = _connect_token_state()
        connection.execute("BEGIN IMMEDIATE")
        now = time.time()
        connection.execute("DELETE FROM local_token_state WHERE expires_at <= ?", (now,))
        session_id = payload.get("sid")
        if isinstance(session_id, str):
            revoked_session = connection.execute(
                "SELECT 1 FROM local_token_state WHERE token_id = ? AND state = 'revoked' AND expires_at > ?",
                (f"sid:{session_id}", now),
            ).fetchone()
            if revoked_session:
                connection.rollback()
                return None
        existing = connection.execute(
            "SELECT state FROM local_token_state WHERE token_id = ?",
            (f"jti:{token_id}",),
        ).fetchone()
        if existing:
            connection.rollback()
            return None
        connection.execute(
            "INSERT INTO local_token_state (token_id, state, expires_at) VALUES (?, 'used_refresh', ?)",
            (f"jti:{token_id}", expiry),
        )
        connection.commit()
        return payload
    except sqlite3.Error:
        if connection:
            connection.rollback()
        return None
    finally:
        if connection:
            connection.close()


async def require_local_staff(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    payload = decode_local_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return str(payload["sub"])
