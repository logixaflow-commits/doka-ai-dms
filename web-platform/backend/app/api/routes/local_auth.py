"""Authentication endpoints for the Doka Personal Local Edition."""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.local_security import (
    clear_login_failures,
    create_local_access_token,
    create_local_refresh_token,
    decode_local_token,
    consume_local_refresh_token,
    invalidate_local_token,
    login_is_locked,
    record_login_failure,
)

router = APIRouter()


class LocalLogin(BaseModel):
    username: str
    password: str


class LocalRefresh(BaseModel):
    refresh_token: str


@router.post("/login")
async def login(credentials: LocalLogin, request: Request):
    if settings.ENVIRONMENT.strip().lower() not in {"development", "local", "test"}:
        raise HTTPException(status_code=404, detail="Local password authentication is disabled outside local environments.")
    username = credentials.username.strip()
    client_host = request.client.host if request.client else None

    if login_is_locked(username, client_host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )

    configured = settings.BOOTSTRAP_ADMIN_PASSWORD
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="Local admin password is not configured. Set BOOTSTRAP_ADMIN_PASSWORD.",
        )

    if username != settings.LOCAL_ADMIN_USERNAME or credentials.password != configured:
        record_login_failure(username, client_host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    clear_login_failures(username, client_host)
    return {
        "access_token": create_local_access_token(username),
        "refresh_token": create_local_refresh_token(username),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh")
async def refresh(body: LocalRefresh):
    if settings.ENVIRONMENT.strip().lower() not in {"development", "local", "test"}:
        raise HTTPException(status_code=404, detail="Local password authentication is disabled outside local environments.")
    payload = consume_local_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    username = str(payload["sub"])
    return {
        "access_token": create_local_access_token(username),
        "refresh_token": create_local_refresh_token(username),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me")
async def me(request: Request):
    if settings.ENVIRONMENT.strip().lower() not in {"development", "local", "test"}:
        raise HTTPException(status_code=404, detail="Local password authentication is disabled outside local environments.")
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_local_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return {"username": payload["sub"], "role": payload["role"]}


@router.post("/logout")
async def logout(request: Request):
    if settings.ENVIRONMENT.strip().lower() not in {"development", "local", "test"}:
        raise HTTPException(status_code=404, detail="Local password authentication is disabled outside local environments.")

    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        invalidate_local_token(authorization[7:])

    try:
        body = await request.json()
    except Exception:
        body = {}
    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    if isinstance(refresh_token, str) and refresh_token:
        invalidate_local_token(refresh_token)

    return {"message": "Local session ended."}
