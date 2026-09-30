"""Personal Local Edition authentication helpers.

This module intentionally does not depend on the deferred enterprise ORM models.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.core.config import settings

bearer = HTTPBearer(auto_error=False)

def create_local_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": username, "role": "admin", "type": "access", "iat": now, "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)}, settings.SECRET_KEY, algorithm="HS256")

def create_local_refresh_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": username, "role": "admin", "type": "refresh", "iat": now, "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)}, settings.SECRET_KEY, algorithm="HS256")

def decode_local_token(token: str, expected_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != expected_type or payload.get("role") != "admin": return None
        return payload
    except JWTError:
        return None

async def require_local_staff(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> str:
    if credentials is None: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    payload = decode_local_token(credentials.credentials)
    if not payload: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return str(payload["sub"])
