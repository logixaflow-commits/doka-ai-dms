from __future__ import annotations

import hashlib
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response
from pydantic import BaseModel, Field

from app.core.supabase_auth import require_authenticated_user
from app.core.local_security import bearer
from fastapi.security import HTTPAuthorizationCredentials
from app.services.cloud_storage import (
    StorageError,
    StorageNotConfigured,
    build_object_storage,
    normalize_key,
)

router = APIRouter(
    prefix="/api/storage",
    tags=["Cloud Storage"],
    dependencies=[Depends(require_authenticated_user)],
)


class SignedUrlRequest(BaseModel):
    key: str = Field(min_length=1, max_length=1024)
    expires_seconds: int = Field(default=900, ge=1, le=604800)


def _user_key(user_id: str, key: str) -> str:
    safe = normalize_key(key)
    return f"users/{normalize_key(user_id)}/{safe}"


@router.post("/objects")
async def upload_object(
    key: str,
    file: UploadFile = File(...),
    user_id: str = Depends(require_authenticated_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    try:
        object_key = _user_key(user_id, key)
        max_bytes = int(__import__("os").getenv("DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024)))
        if file.size is not None and file.size > max_bytes:
            raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
        digest = hashlib.sha256(data).hexdigest()
        storage = build_object_storage(access_token=credentials.credentials)
        stored = storage.put(
            object_key,
            io.BytesIO(data),
            content_type=file.content_type or "application/octet-stream",
            expected_sha256=digest,
        )
        return {"key": key, "size": stored.size, "sha256": stored.sha256, "content_type": stored.content_type}
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/objects/{key:path}")
async def download_object(key: str, user_id: str = Depends(require_authenticated_user), credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        storage = build_object_storage(access_token=credentials.credentials)
        object_key = _user_key(user_id, key)
        data = storage.get(object_key)
        stored = storage.head(object_key)
        return Response(content=data, media_type=stored.content_type, headers={"Content-Disposition": f'inline; filename="{key.rsplit("/", 1)[-1]}"', "X-Doka-SHA256": hashlib.sha256(data).hexdigest()})
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/signed-url")
async def signed_url(request: SignedUrlRequest, user_id: str = Depends(require_authenticated_user), credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        storage = build_object_storage(access_token=credentials.credentials)
        return {"key": request.key, "url": storage.signed_get_url(_user_key(user_id, request.key), expires_seconds=request.expires_seconds)}
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
