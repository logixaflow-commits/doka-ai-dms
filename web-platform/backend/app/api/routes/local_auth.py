"""Authentication endpoints for the Doka Personal Local Edition."""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.local_security import (
    clear_login_failures,
    create_local_access_token,
    create_local_refresh_token,
    decode_local_token,
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
async def login(credentials: LocalLogin, request: Request | None = None):
    username = credentials.username.strip()
    client_host = request.client.host if request and request.client else None

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
    payload = decode_local_token(body.refresh_token, expected_type="refresh")
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
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = decode_local_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return {"username": payload["sub"], "role": payload["role"]}


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully. Remove the local access token from the client."}
