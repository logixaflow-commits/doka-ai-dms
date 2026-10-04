"""Supabase Auth verification for protected Doka API routes.

The browser authenticates with Supabase Auth and sends its access token to the
Doka API. The API verifies that token against Supabase Auth's /user endpoint;
the publishable key is safe for this server-to-server verification request.
"""
from __future__ import annotations

import os

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.local_security import bearer, require_local_staff
from app.core.config import settings


def _supabase_configured() -> bool:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        return False
    placeholders = ("your-project-ref", "your_public_key")
    return not any(value in url or value in key for value in placeholders)


async def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    # Production must use Supabase Auth. Local HS256 tokens remain available only
    # for the local/development edition where Supabase is intentionally optional.
    if not _supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth is not configured for this environment.",
        )

    token = credentials.credentials
    base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{base_url}/auth/v1/user",
                headers={
                    "apikey": publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth verification is temporarily unavailable.",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Supabase session.",
        )

    try:
        user = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase Auth response.",
        ) from exc

    user_id = str(user.get("id", "")).strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase session did not contain a user id.",
        )
    return user_id



async def require_local_workspace_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    """Keep filesystem-backed Safe Workspace APIs out of production deployments."""
    if settings.ENVIRONMENT.strip().lower() not in {"development", "local", "test"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Safe Workspace is available only in an explicitly local environment.",
        )
    return await require_local_staff(credentials)
