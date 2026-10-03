"""Authentication helpers for the Doka Personal Local Edition.

The local edition intentionally keeps authentication state in process memory.
A database/Redis-backed session architecture belongs to the later multi-user edition.
"""

from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional
import threading
import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt.exceptions import InvalidTokenError as JWTError

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)

_login_guard = threading.Lock()
_login_failures: dict[str, list[float]] = {}
_refresh_guard = threading.Lock()
_used_refresh_tokens: dict[str, float] = {}
_invalid_token_ids: dict[str, float] = {}


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
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": username,
            "role": "admin",
            "type": "access",
            "jti": secrets.token_urlsafe(18),
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def create_local_refresh_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": username,
            "role": "admin",
            "type": "refresh",
            "jti": secrets.token_urlsafe(18),
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
        if payload.get("jti") in _invalid_token_ids:
            return None
        return payload
    except JWTError:
        return None


def invalidate_local_token(token: str) -> bool:
    """Invalidate a local token until its natural expiry."""
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
    with _refresh_guard:
        _invalid_token_ids[token_id] = expiry
    return True


def consume_local_refresh_token(token: str) -> Optional[dict]:
    """Validate and consume a refresh token once to prevent replay within this process."""
    payload = decode_local_token(token, expected_type="refresh")
    if not payload:
        return None
    token_id = payload.get("jti")
    expires_at = payload.get("exp")
    if not isinstance(token_id, str) or not token_id:
        return None
    try:
        expiry = float(expires_at)
    except (TypeError, ValueError):
        return None

    now = time.time()
    with _refresh_guard:
        expired = [key for key, value in _used_refresh_tokens.items() if value <= now]
        for key in expired:
            _used_refresh_tokens.pop(key, None)
        if token_id in _used_refresh_tokens:
            return None
        _used_refresh_tokens[token_id] = expiry
    return payload


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
