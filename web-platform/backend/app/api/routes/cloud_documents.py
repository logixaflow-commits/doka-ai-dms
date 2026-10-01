from __future__ import annotations

import hashlib
import io
import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import httpx
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.local_security import bearer
from app.core.supabase_auth import require_authenticated_user
from app.services.cloud_documents import CloudDocumentError, build_cloud_document_service
from app.services.cloud_storage import StorageError, StorageNotConfigured, build_object_storage

router = APIRouter(
    prefix="/api/documents",
    tags=["Cloud Documents"],
    dependencies=[Depends(require_authenticated_user)],
)


class DocumentMetadataUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|review|quarantined|archived)$")
    metadata: dict = Field(default_factory=dict)


@router.get("")
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    if not 1 <= limit <= 500 or offset < 0:
        raise HTTPException(status_code=400, detail="Invalid limit/offset.")
    try:
        return {"documents": build_cloud_document_service(credentials.credentials).list_documents(limit=limit, offset=offset)}
    except (CloudDocumentError, StorageNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("")
async def create_document(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    user_id: str = Depends(require_authenticated_user),
):
    max_bytes = int(os.getenv("DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024)))
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")

    digest = hashlib.sha256(data).hexdigest()
    raw_name = (file.filename or "document").replace("\\", "/").rsplit("/", 1)[-1]
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._") or "document"
    object_key = f"users/{user_id}/documents/{digest}/{safe_name}"
    storage = None
    try:
        storage = build_object_storage(access_token=credentials.credentials)
        stored = storage.put(
            object_key,
            io.BytesIO(data),
            content_type=file.content_type or "application/octet-stream",
            expected_sha256=digest,
        )
        service = build_cloud_document_service(credentials.credentials)
        document = service.create_document(
            owner_id=user_id,
            object_key=stored.key,
            filename=file.filename or "document",
            content_type=stored.content_type,
            size_bytes=stored.size,
            sha256=stored.sha256,
        )
        return {"document": document}
    except (StorageError, CloudDocumentError, StorageNotConfigured) as exc:
        if storage is not None:
            try:
                storage.delete(object_key)
            except Exception:
                pass
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    user_id: str = Depends(require_authenticated_user),
):
    try:
        service = build_cloud_document_service(credentials.credentials)
        target = service.get_document(owner_id=user_id, document_id=document_id)
        if not target:
            raise HTTPException(status_code=404, detail="Document not found.")
        storage = build_object_storage(access_token=credentials.credentials)
        url = storage.signed_get_url(target["object_key"], expires_seconds=300)
        return {"url": url, "sha256": target["sha256"], "expires_seconds": 300}
    except HTTPException:
        raise
    except (StorageError, CloudDocumentError, StorageNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    request: DocumentMetadataUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    user_id: str = Depends(require_authenticated_user),
):
    try:
        service = build_cloud_document_service(credentials.credentials)
        target = service.get_document(owner_id=user_id, document_id=document_id)
        if not target:
            raise HTTPException(status_code=404, detail="Document not found.")
        # Update is intentionally limited to status/metadata; object identity and hashes are immutable.
        headers = service._headers()
        payload = {}
        if request.status is not None:
            payload["status"] = request.status
        payload["metadata"] = request.metadata
        response = httpx.patch(
            f"{service.base_url}/rest/v1/doka_documents",
            headers={**headers, "Prefer": "return=representation"},
            params={"id": f"eq.{document_id}", "owner_id": f"eq.{user_id}"},
            json=payload,
            timeout=15.0,
        )
        if response.status_code >= 300:
            raise CloudDocumentError(f"Document update failed ({response.status_code}).")
        rows = response.json()
        if not rows:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"document": rows[0]}
    except HTTPException:
        raise
    except CloudDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
