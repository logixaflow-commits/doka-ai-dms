"""Doka Cloud API entrypoint for Cloudflare Python Workers.

This Worker intentionally keeps cloud operations stateless. User identity is
verified by Supabase Auth; document metadata and objects remain in Supabase.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from js import Object, Uint8Array, fetch as js_fetch
from pyodide.ffi import to_js
from workers import asgi, env as worker_env

from shared.storage_contracts import StorageArtifactType, UploadMetadata, owner_object_key
from storage_runtime import build_google_drive_provider, build_storage_router, sign_session, verify_session
from cloudflare_worker.storage_b2 import B2PartReceipt, MultipartUpload
from cloudflare_worker.b2_quota import evaluate_b2_quota
from shared.storage_contracts import SignedUpload, StorageObjectRef


bearer = HTTPBearer(auto_error=False)
app = FastAPI(title="Doka Cloud API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)


def _env(request, name: str, default: str = "") -> str:
    bindings = request.scope.get("env")
    if bindings is not None:
        try:
            value = getattr(bindings, name)
        except Exception:
            try:
                value = bindings[name]
            except Exception:
                value = None
        if value is not None:
            return str(value)
    # Cloudflare Python Workers expose bindings through the imported global env
    # object as well as the ASGI scope. Keep both paths for runtime compatibility.
    if worker_env is not None:
        try:
            value = getattr(worker_env, name)
        except Exception:
            try:
                value = worker_env[name]
            except Exception:
                value = None
        if value is not None:
            return str(value)
    return os.getenv(name, default)


def _js_bytes(data: bytes):
    result = Uint8Array.new(len(data))
    for index, value in enumerate(data):
        result[index] = value
    return result


async def _fetch(request, url: str, *, method: str = "GET", headers: dict | None = None, body=None, return_headers: bool = False):
    options = {"method": method, "headers": to_js(headers or {}, dict_converter=Object.fromEntries)}
    if body is not None:
        options["body"] = body
    response = await js_fetch(url, to_js(options, dict_converter=Object.fromEntries))
    if return_headers:
        header_names = ("content-length", "content-type", "etag", "x-amz-meta-sha256", "location")
        result_headers = {}
        for name in header_names:
            value = response.headers.get(name)
            if value is not None:
                result_headers[name] = str(value)
        return int(response.status), result_headers
    raw = str(await response.text())
    try:
        payload = json.loads(raw) if raw else None
    except (TypeError, ValueError):
        payload = raw
    return int(response.status), payload


def _supabase_headers(request, token: str, content_type: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": _env(request, "SUPABASE_PUBLISHABLE_KEY"),
        "Authorization": f"Bearer {token}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    base = _env(request, "SUPABASE_URL").rstrip("/")
    key = _env(request, "SUPABASE_PUBLISHABLE_KEY")
    if not base or not key:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured.")
    status, user = await _fetch(
        request,
        f"{base}/auth/v1/user",
        headers={"apikey": key, "Authorization": f"Bearer {credentials.credentials}"},
    )
    if status != 200 or not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase session.")
    allowed_email = _env(request, "DOKA_SINGLE_USER_EMAIL").strip().casefold()
    if allowed_email:
        user_email = str(user.get("email") or "").strip().casefold()
        if not user_email or user_email != allowed_email:
            raise HTTPException(status_code=403, detail="This Doka instance is restricted to its configured single user.")
    return str(user["id"])


def _base(request) -> str:
    value = _env(request, "SUPABASE_URL").rstrip("/")
    if not value:
        raise HTTPException(status_code=503, detail="Supabase URL is not configured.")
    return value


def _bucket(request) -> str:
    return _env(request, "SUPABASE_STORAGE_BUCKET", "doka-documents")


def _object_key(user_id: str, digest: str, filename: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename.replace("\\", "/").rsplit("/", 1)[-1]).strip("._") or "document"
    return f"users/{user_id}/documents/{digest}/{safe}"


class DocumentUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(active|review|quarantined|archived)$")
    metadata: dict | None = None
    filename: str | None = Field(default=None, min_length=1, max_length=255)
    folder_path: str | None = Field(default=None, max_length=512)


class BulkDocumentAction(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=100)
    action: Literal["status", "trash"]
    status: Literal["active", "review", "quarantined", "archived"] | None = None


@app.get("/health")
async def health():
    return {"status": "healthy", "edition": "cloudflare-workers", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/config")
async def public_config(request: Request):
    # Expose configuration readiness only; never return the publishable key.
    return {
        "edition": "cloud-api",
        "auth": "supabase",
        "storage": "supabase",
        "local_workspace_available": False,
        "supabase_auth_configured": bool(_env(request, "SUPABASE_URL") and _env(request, "SUPABASE_PUBLISHABLE_KEY")),
        "storage_bucket_configured": bool(_env(request, "SUPABASE_STORAGE_BUCKET")),
        "single_user_configured": bool(_env(request, "DOKA_SINGLE_USER_EMAIL").strip()),
    }


@app.get("/api/audit")
async def list_audit(
    request: Request,
    user_id: str = Depends(require_user),
    limit: int = Query(default=100, ge=1, le=500),
):
    base = _base(request)
    token = _token_from_request(request)
    query = f"select=id,document_id,action,filename,metadata,created_at&owner_id=eq.{quote(user_id, safe='')}&order=created_at.desc&limit={limit}"
    status, rows = await _fetch(
        request,
        f"{base}/rest/v1/doka_audit_events?{query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Audit listing failed ({status}).")
    return {"events": rows if isinstance(rows, list) else []}


@app.get("/api/folders")
async def list_document_folders(request: Request, user_id: str = Depends(require_user)):
    query = f"select=folder_path&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&order=folder_path.asc&limit=500"
    status, rows = await _fetch(
        request, f"{_base(request)}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, _token_from_request(request)), "Accept": "application/json"},
    )
    if status >= 300 or not isinstance(rows, list):
        raise HTTPException(status_code=503, detail=f"Folder lookup failed ({status}).")
    folders = sorted({str(row.get("folder_path") or "/") for row in rows})
    if "/" not in folders:
        folders.insert(0, "/")
    return {"folders": folders}


@app.post("/api/documents/bulk")
async def bulk_update_documents(request: Request, action: BulkDocumentAction, user_id: str = Depends(require_user)):
    if len(set(action.document_ids)) != len(action.document_ids):
        raise HTTPException(status_code=400, detail="Duplicate document IDs are not allowed.")
    if action.action == "status" and action.status is None:
        raise HTTPException(status_code=400, detail="A status is required for a bulk status update.")
    token = _token_from_request(request)
    payload = {
        "p_document_ids": action.document_ids,
        "p_action": action.action,
        "p_status": action.status,
    }
    status, rows = await _fetch(
        request, f"{_base(request)}/rest/v1/rpc/doka_bulk_update_documents",
        method="POST",
        headers=_supabase_headers(request, token, "application/json"),
        body=json.dumps(payload),
    )
    if status == 404:
        raise HTTPException(status_code=404, detail="One or more documents are unavailable.")
    if status >= 300 or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail=f"Bulk document action failed ({status}).")
    return {"documents": rows, "updated_count": len(rows)}


@app.get("/api/documents")
async def list_documents(
    request: Request,
    user_id: str = Depends(require_user),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|review|quarantined|archived)$"),
    trash: bool = Query(default=False),
    folder_path: str | None = Query(default=None, max_length=512),
):
    base = _base(request)
    filters = [
        "select=*",
        f"owner_id=eq.{quote(user_id, safe='')}",
        f"deleted_at={'not.is.null' if trash else 'is.null'}",
        "order=created_at.desc",
        f"limit={limit}",
        f"offset={offset}",
    ]
    if status_filter:
        filters.append(f"status=eq.{quote(status_filter, safe='')}")
    if search and search.strip():
        # URL-encode the user value so PostgREST filter syntax cannot be injected.
        filters.append(f"filename=ilike.*{quote(search.strip(), safe='')}*")
    if folder_path is not None:
        normalized_folder = _normalize_folder_path(folder_path)
        filters.append(f"folder_path=eq.{quote(normalized_folder, safe='')}")
    query = "&".join(filters)
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, _token_from_request(request)), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document listing failed ({status}).")
    return {"documents": rows if isinstance(rows, list) else []}


def _normalize_folder_path(value: str) -> str:
    raw = value.strip()
    if not raw or raw == "/":
        return "/"
    if "\x00" in raw or "\\" in raw:
        raise HTTPException(status_code=400, detail="Invalid folder path.")
    segments = [part for part in raw.split("/") if part]
    if not segments or any(part in {".", ".."} for part in segments):
        raise HTTPException(status_code=400, detail="Invalid folder path.")
    return "/" + "/".join(segments)


def _token_from_request(request) -> str:
    value = request.headers.get("authorization", "")
    return value[7:].strip() if value.lower().startswith("bearer ") else ""


def _storage_session_secret(request) -> str:
    secret = _env(request, "DOKA_STORAGE_SESSION_SECRET").strip()
    if not secret:
        # SECRET_KEY is accepted as a deployment convenience; production should
        # still provision a dedicated storage-session secret.
        secret = _env(request, "SECRET_KEY").strip()
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Direct storage session signing is not configured.")
    return secret


def _storage_fetcher(request):
    async def fetcher(url: str, *, method: str = "GET", headers: dict | None = None, body=None, return_headers: bool = False):
        status, payload = await _fetch(request, url, method=method, headers=headers, body=body, return_headers=return_headers)
        return status, payload
    return fetcher


def _provider_for(router, provider: str):
    if provider == "supabase":
        return router.supabase
    if provider == "b2":
        if router.b2 is None:
            raise HTTPException(status_code=503, detail="B2 storage is not configured.")
        return router.b2
    if provider == "cloudinary":
        if router.cloudinary is None:
            raise HTTPException(status_code=503, detail="Cloudinary storage is not configured.")
        return router.cloudinary
    raise HTTPException(status_code=400, detail="Unsupported storage provider.")


def _validate_upload_metadata(request: Request, user_id: str, payload: dict) -> UploadMetadata:
    filename = str(payload.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    content_type = str(payload.get("content_type") or "application/octet-stream").split(";", 1)[0].strip().lower()
    size_bytes = int(payload.get("size_bytes") or 0)
    sha256 = str(payload.get("sha256") or "").lower()
    if (
        not filename or filename in {".", ".."} or len(filename) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in filename)
        or any(character in '<>:"|?*' for character in filename)
    ):
        raise HTTPException(status_code=400, detail="Filename must be a plain file name up to 255 characters.")
    max_bytes = int(_env(request, "DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024)))
    if size_bytes < 1 or size_bytes > max_bytes and size_bytes <= 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Object size is outside the configured limit.")
    if size_bytes > max_bytes:
        # Large objects are permitted only when B2 is configured and the global
        # application limit explicitly exceeds the Supabase 50 MiB boundary.
        if not _env(request, "B2_BUCKET") or size_bytes > 5 * 1024 * 1024 * 1024 * 100:
            raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
    if len(content_type) > 255 or "/" not in content_type:
        raise HTTPException(status_code=400, detail="Invalid content type.")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise HTTPException(status_code=400, detail="sha256 must be a 64-character hexadecimal digest.")
    try:
        artifact_type = StorageArtifactType(str(payload.get("artifact_type") or "source"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported storage artifact type.") from exc
    metadata = UploadMetadata(filename, content_type, size_bytes, sha256, user_id, artifact_type)
    try:
        metadata.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return metadata

async def _check_b2_quota(request: Request, user_id: str, requested_bytes: int) -> dict:
    quota_raw = _env(request, "B2_QUOTA_BYTES").strip()
    if not quota_raw:
        raise HTTPException(status_code=503, detail="B2 quota guard is not configured.")
    try:
        quota_bytes = int(quota_raw)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="B2 quota guard is invalid.") from exc

    query = (
        f"select=size_bytes&owner_id=eq.{quote(user_id, safe='')}"
        "&storage_provider=eq.b2&deleted_at=is.null&limit=10000"
    )
    status, rows = await _fetch(
        request,
        f"{_base(request)}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, _token_from_request(request)), "Accept": "application/json"},
    )
    if status >= 300 or not isinstance(rows, list):
        raise HTTPException(status_code=503, detail="Unable to calculate B2 quota usage.")
    if len(rows) >= 10000:
        raise HTTPException(status_code=503, detail="B2 quota usage is too large to verify safely.")
    used_bytes = sum(max(0, int(row.get("size_bytes") or 0)) for row in rows)
    try:
        decision = evaluate_b2_quota(
            used_bytes=used_bytes,
            requested_bytes=requested_bytes,
            quota_bytes=quota_bytes,
            alert_ratio=float(_env(request, "B2_QUOTA_ALERT_RATIO", "0.80")),
            block_ratio=float(_env(request, "B2_QUOTA_BLOCK_RATIO", "0.95")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if decision.warning:
        print(f"DOKA_B2_QUOTA {decision.warning} used={used_bytes} requested={requested_bytes} quota={quota_bytes} ratio={decision.usage_ratio:.4f}")
        webhook = _env(request, "B2_QUOTA_ALERT_WEBHOOK").strip()
        if webhook and decision.warning == "b2_quota_warning":
            try:
                await _fetch(
                    request,
                    webhook,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    body=json.dumps({
                        "event": decision.warning,
                        "used_bytes": used_bytes,
                        "requested_bytes": requested_bytes,
                        "quota_bytes": quota_bytes,
                        "usage_ratio": decision.usage_ratio,
                    }),
                )
            except Exception:
                pass
    if decision.blocked:
        # Google Drive fallback is deliberately not faked. It becomes active only
        # after a real Google Drive OAuth/provider is configured.
        raise HTTPException(
            status_code=507,
            detail="B2 quota is at the 95% safety threshold; new B2 uploads are blocked until capacity is available or Google Drive fallback is configured.",
        )
    return {
        "quota_bytes": decision.quota_bytes,
        "used_bytes": decision.used_bytes,
        "requested_bytes": decision.requested_bytes,
        "projected_bytes": decision.projected_bytes,
        "usage_ratio": decision.usage_ratio,
        "warning": decision.warning,
    }


async def _audit(request, user_id: str, action: str, document_id: str | None = None, filename: str | None = None, metadata: dict | None = None) -> None:
    """Best-effort owner-scoped audit event; never breaks the primary document action."""
    try:
        base = _base(request)
        token = _token_from_request(request)
        payload = {
            "owner_id": user_id,
            "document_id": document_id,
            "action": action,
            "filename": filename,
            "metadata": metadata or {},
        }
        await _fetch(
            request,
            f"{base}/rest/v1/doka_audit_events",
            method="POST",
            headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=minimal"},
            body=json.dumps(payload),
        )
    except Exception:
        pass


@app.post("/api/documents")
async def create_document(request: Request, file: UploadFile = File(...), user_id: str = Depends(require_user)):
    # Bytes must never be proxied through the Worker. Keep the route for clients
    # that have not upgraded yet, but fail closed instead of buffering the file.
    raise HTTPException(status_code=410, detail="Direct upload is required. Create an upload session first.")


class UploadSessionRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=255)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    artifact_type: Literal["source", "preview", "thumbnail", "cover"] = "source"
    document_id: str | None = None


class DriveExportCompletionRequest(BaseModel):
    session_id: str = Field(min_length=20, max_length=4096)
    file_id: str = Field(min_length=1, max_length=512)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)


class UploadCompletionRequest(BaseModel):
    session_id: str = Field(min_length=20, max_length=4096)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    provider_result: dict = Field(default_factory=dict)


@app.post("/api/storage/multipart/initiate")
async def initiate_storage_multipart(
    request: Request,
    payload: UploadSessionRequest,
    user_id: str = Depends(require_user),
):
    metadata = _validate_upload_metadata(request, user_id, payload.model_dump())
    if metadata.artifact_type is not StorageArtifactType.SOURCE or metadata.size_bytes <= 5 * 1024 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="B2 multipart is reserved for source objects above 5 GiB.")
    router = build_storage_router(request, _token_from_request(request), _storage_fetcher)
    if router.b2 is None:
        raise HTTPException(status_code=503, detail="B2 storage is not configured.")
    upload = await router.b2.initiateMultipartUpload(metadata)
    signed_payload = {
        "owner_id": user_id,
        "provider": "b2",
        "object_key": upload.object_ref.object_key,
        "sha256": metadata.sha256,
        "filename": metadata.filename,
        "content_type": metadata.content_type,
        "size_bytes": metadata.size_bytes,
        "artifact_type": metadata.artifact_type.value,
        "upload_id": upload.upload_id,
        "part_size_bytes": upload.part_size_bytes,
        "expires_at": upload.expires_at,
        "storage_region": _env(request, "B2_REGION", ""),
    }
    return {
        "session_id": sign_session(_storage_session_secret(request), signed_payload),
        "provider": "b2",
        "object_key": upload.object_ref.object_key,
        "upload_id": upload.upload_id,
        "part_size_bytes": upload.part_size_bytes,
        "expires_at": upload.expires_at,
    }


class MultipartPartRequest(BaseModel):
    session_id: str = Field(min_length=20, max_length=4096)
    part_number: int = Field(ge=1, le=10000)
    checksum: str = Field(min_length=64, max_length=64)


@app.post("/api/storage/multipart/part")
async def sign_storage_multipart_part(
    request: Request,
    payload: MultipartPartRequest,
    user_id: str = Depends(require_user),
):
    try:
        signed = verify_session(_storage_session_secret(request), payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if signed.get("owner_id") != user_id or signed.get("provider") != "b2":
        raise HTTPException(status_code=403, detail="Multipart session is not valid for this user.")
    router = build_storage_router(request, _token_from_request(request), _storage_fetcher)
    if router.b2 is None:
        raise HTTPException(status_code=503, detail="B2 storage is not configured.")
    upload = MultipartUpload(
        upload_id=str(signed["upload_id"]),
        object_ref=StorageObjectRef("b2", str(signed["object_key"]), user_id),
        part_size_bytes=int(signed["part_size_bytes"]),
        expires_at=int(signed["expires_at"]),
    )
    receipt = await router.b2.uploadPart(upload, payload.part_number, payload.checksum)
    return {
        "part_number": receipt.part_number,
        "checksum": receipt.checksum,
        "upload": {
            "method": receipt.signed_request.method,
            "url": receipt.signed_request.url,
            "headers": receipt.signed_request.headers,
            "fields": receipt.signed_request.fields,
        },
    }


class MultipartCompletePart(BaseModel):
    part_number: int = Field(ge=1, le=10000)
    etag: str = Field(min_length=1, max_length=1024)
    checksum: str = Field(min_length=64, max_length=64)


class MultipartCompleteRequest(BaseModel):
    session_id: str = Field(min_length=20, max_length=4096)
    parts: list[MultipartCompletePart] = Field(min_length=1, max_length=10000)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)


@app.post("/api/storage/multipart/complete")
async def complete_storage_multipart(
    request: Request,
    payload: MultipartCompleteRequest,
    user_id: str = Depends(require_user),
):
    try:
        signed = verify_session(_storage_session_secret(request), payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if signed.get("owner_id") != user_id or signed.get("provider") != "b2":
        raise HTTPException(status_code=403, detail="Multipart session is not valid for this user.")
    if int(signed.get("size_bytes", 0)) != payload.size_bytes or str(signed.get("sha256", "")).lower() != payload.sha256.lower():
        raise HTTPException(status_code=400, detail="Multipart completion does not match the issued session.")
    router = build_storage_router(request, _token_from_request(request), _storage_fetcher)
    if router.b2 is None:
        raise HTTPException(status_code=503, detail="B2 storage is not configured.")
    upload = MultipartUpload(
        upload_id=str(signed["upload_id"]),
        object_ref=StorageObjectRef("b2", str(signed["object_key"]), user_id),
        part_size_bytes=int(signed["part_size_bytes"]),
        expires_at=int(signed["expires_at"]),
    )
    receipts = [B2PartReceipt(p.part_number, p.etag, p.checksum.lower(), SignedUpload("PUT", "", {}, {})) for p in payload.parts]
    try:
        stored = await router.b2.completeMultipartUpload(upload, receipts)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=f"B2 multipart completion failed: {exc}") from exc
    base = _base(request)
    record = {
        "owner_id": user_id,
        "object_key": stored.object_ref.object_key,
        "filename": str(signed["filename"]),
        "content_type": str(signed["content_type"]),
        "size_bytes": stored.size_bytes,
        "sha256": payload.sha256.lower(),
        "status": "active",
        "metadata": {},
        "storage_provider": "b2",
        "storage_status": "ready",
        "storage_region": str(signed.get("storage_region") or "") or None,
    }
    record = {key: value for key, value in record.items() if value is not None}
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents", method="POST",
        headers={**_supabase_headers(request, _token_from_request(request), "application/json"), "Prefer":"return=representation"},
        body=json.dumps(record),
    )
    if status >= 300 or not isinstance(rows, list) or not rows:
        try:
            await router.b2.delete(stored.object_ref)
        except Exception:
            pass
        raise HTTPException(status_code=503, detail=f"Document metadata creation failed ({status}).")
    await _audit(request, user_id, "upload", str(rows[0].get("id")), rows[0].get("filename"), {
        "size_bytes": stored.size_bytes, "sha256": payload.sha256.lower(), "storage_provider": "b2",
    })
    return {"document": rows[0], "warnings": []}




@app.post("/api/documents/{document_id}/export/google-drive/upload-session")
async def create_google_drive_export_session(
    request: Request,
    document_id: str,
    user_id: str = Depends(require_user),
):
    token = _token_from_request(request)
    query = f"select=id,filename,content_type,size_bytes,sha256,storage_provider,object_key&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
    status, rows = await _fetch(
        request, f"{_base(request)}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document lookup failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    document = rows[0]
    provider = build_google_drive_provider(request, _storage_fetcher)
    if provider is None:
        raise HTTPException(status_code=503, detail="Google Drive OAuth export is not configured.")
    metadata = UploadMetadata(
        filename=str(document["filename"]),
        content_type=str(document["content_type"]),
        size_bytes=int(document["size_bytes"]),
        sha256=str(document["sha256"]).lower(),
        owner_id=user_id,
    )
    try:
        _, upload, expires_at = await provider.create_upload_session(metadata)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    source_provider_name = str(document.get("storage_provider") or "supabase")
    source_router = build_storage_router(request, token, _storage_fetcher)
    source_provider = _provider_for(source_router, source_provider_name)
    try:
        download_url = await source_provider.get_signed_download(
            StorageObjectRef(source_provider_name, str(document["object_key"]), user_id),
            expires_seconds=300,
        )
    except (RuntimeError, ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=503, detail=f"Source download session failed: {exc}") from exc
    session_payload = {
        "owner_id": user_id,
        "document_id": document_id,
        "provider": "google_drive",
        "filename": metadata.filename,
        "content_type": metadata.content_type,
        "size_bytes": metadata.size_bytes,
        "sha256": metadata.sha256,
        "expires_at": expires_at,
    }
    return {
        "session_id": sign_session(_storage_session_secret(request), session_payload),
        "provider": "google_drive",
        "expires_at": expires_at,
        "source_document": {"id": document_id, "size_bytes": metadata.size_bytes, "sha256": metadata.sha256, "download_url": download_url},
        "upload": {"method": upload.method, "url": upload.url, "headers": upload.headers, "fields": upload.fields},
    }


@app.post("/api/documents/{document_id}/export/google-drive/complete")
async def complete_google_drive_export(
    request: Request,
    document_id: str,
    payload: DriveExportCompletionRequest,
    user_id: str = Depends(require_user),
):
    token = _token_from_request(request)
    try:
        signed = verify_session(_storage_session_secret(request), payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if signed.get("owner_id") != user_id or signed.get("document_id") != document_id or signed.get("provider") != "google_drive":
        raise HTTPException(status_code=403, detail="Google Drive export session is not valid for this user/document.")
    if int(signed.get("size_bytes", 0)) != payload.size_bytes or str(signed.get("sha256", "")).lower() != payload.sha256.lower():
        raise HTTPException(status_code=400, detail="Google Drive export completion does not match the issued session.")
    provider = build_google_drive_provider(request, _storage_fetcher)
    if provider is None:
        raise HTTPException(status_code=503, detail="Google Drive OAuth export is not configured.")
    try:
        stored = await provider.verify_completion(
            StorageObjectRef("google_drive", f"pending/{user_id}/{payload.sha256.lower()}", user_id),
            payload.file_id,
            expected_size=payload.size_bytes,
            expected_sha256=payload.sha256.lower(),
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=f"Google Drive export verification failed: {exc}") from exc
    status, rows = await _fetch(
        request,
        f"{_base(request)}/rest/v1/doka_documents?id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}",
        method="PATCH",
        headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=representation"},
        body=json.dumps({"export_provider": "google_drive", "export_reference": stored.object_ref.object_key, "export_status": "ready"}),
    )
    if status >= 300 or not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=503, detail=f"Google Drive export metadata update failed ({status}).")
    await _audit(request, user_id, "export", document_id, str(signed.get("filename")), {
        "provider": "google_drive", "file_id": payload.file_id, "sha256": payload.sha256.lower(),
    })
    return {"document": rows[0]}


@app.post("/api/storage/upload-session")
async def create_storage_upload_session(
    request: Request,
    payload: UploadSessionRequest,
    user_id: str = Depends(require_user),
):
    metadata = _validate_upload_metadata(request, user_id, payload.model_dump())
    document_id = payload.document_id
    if document_id:
        doc_query = f"select=id,object_key,sha256&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
        doc_status, docs = await _fetch(
            request,
            f"{_base(request)}/rest/v1/doka_documents?{doc_query}",
            headers={**_supabase_headers(request, _token_from_request(request)), "Accept": "application/json"},
        )
        if doc_status >= 300:
            raise HTTPException(status_code=503, detail="Unable to validate the target document.")
        if not isinstance(docs, list) or not docs:
            raise HTTPException(status_code=404, detail="Document not found.")
        if str(docs[0].get("object_key") or "") == owner_object_key(metadata):
            raise HTTPException(status_code=409, detail="The uploaded content is identical to the current document.")
    if metadata.artifact_type is StorageArtifactType.SOURCE and metadata.size_bytes > int(_env(request, "DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024))):
        # The configured application limit is the source of truth for B2; a
        # missing/50 MiB default therefore remains safely Supabase-only.
        if not _env(request, "B2_BUCKET").strip():
            raise HTTPException(status_code=503, detail="Large-object storage is not configured.")
    if metadata.artifact_type is StorageArtifactType.SOURCE and metadata.size_bytes > 50 * 1024 * 1024:
        await _check_b2_quota(request, user_id, metadata.size_bytes)

    router = build_storage_router(request, _token_from_request(request), _storage_fetcher)
    try:
        session, decision = await router.create_upload_session(metadata)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        message = str(exc)
        status_code = 503 if message not in {"cloudinary_credit_fallback"} else 200
        raise HTTPException(status_code=status_code, detail=message) from exc

    payload_to_sign = {
        "owner_id": user_id,
        "provider": session.provider,
        "object_key": session.object_ref.object_key,
        "sha256": metadata.sha256,
        "filename": metadata.filename,
        "content_type": metadata.content_type,
        "size_bytes": metadata.size_bytes,
        "artifact_type": metadata.artifact_type.value,
        "document_id": document_id,
        "storage_region": _env(request, "B2_REGION", "") if session.provider == "b2" else "",
        "expires_at": session.expires_at,
    }
    session_token = sign_session(_storage_session_secret(request), payload_to_sign)
    return {
        "session_id": session_token,
        "provider": session.provider,
        "object_key": session.object_ref.object_key,
        "expires_at": session.expires_at,
        "upload": {
            "method": session.upload.method,
            "url": session.upload.url,
            "headers": session.upload.headers,
            "fields": session.upload.fields,
        },
        "warnings": list(decision.warnings or session.warnings),
    }


@app.post("/api/storage/upload-complete")
async def complete_storage_upload(
    request: Request,
    payload: UploadCompletionRequest,
    user_id: str = Depends(require_user),
):
    try:
        signed = verify_session(_storage_session_secret(request), payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if signed.get("owner_id") != user_id:
        raise HTTPException(status_code=403, detail="Upload session belongs to another user.")
    if str(signed.get("sha256", "")).lower() != payload.sha256.lower() or int(signed.get("size_bytes", 0)) != payload.size_bytes:
        raise HTTPException(status_code=400, detail="Upload completion does not match the issued session.")
    metadata = UploadMetadata(
        filename=str(signed["filename"]),
        content_type=str(signed["content_type"]),
        size_bytes=int(signed["size_bytes"]),
        sha256=str(signed["sha256"]).lower(),
        owner_id=user_id,
        artifact_type=StorageArtifactType(str(signed.get("artifact_type", "source"))),
    )
    router = build_storage_router(request, _token_from_request(request), _storage_fetcher)
    provider = _provider_for(router, str(signed["provider"]))
    session = type("CompletedSession", (), {
        "provider": str(signed["provider"]),
        "object_ref": type("ObjectRef", (), {
            "provider": str(signed["provider"]),
            "object_key": str(signed["object_key"]),
            "owner_id": user_id,
        })(),
        "expires_at": int(signed["expires_at"]),
        "upload": type("Signed", (), {"method": "", "url": "", "headers": {}, "fields": {}})(),
        "session_id": payload.session_id,
    })()
    try:
        stored = await provider.complete_upload(session, {
            "size_bytes": payload.size_bytes,
            "sha256": payload.sha256.lower(),
            **payload.provider_result,
        })
    except (RuntimeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=f"Upload verification failed: {exc}") from exc

    if metadata.artifact_type is not StorageArtifactType.SOURCE:
        return {
            "stored": {
                "provider": stored.object_ref.provider,
                "object_key": stored.object_ref.object_key,
                "size_bytes": stored.size_bytes,
                "sha256": stored.sha256,
                "content_type": stored.content_type,
            },
            "warnings": [],
        }

    if signed.get("document_id"):
        rpc_payload = {
            "p_document_id": str(signed["document_id"]),
            "p_object_key": stored.object_ref.object_key,
            "p_filename": metadata.filename,
            "p_content_type": metadata.content_type,
            "p_size_bytes": stored.size_bytes,
            "p_sha256": metadata.sha256,
            "p_storage_provider": stored.object_ref.provider,
            "p_storage_region": str(signed.get("storage_region") or "") or None,
        }
        status, rows = await _fetch(
            request,
            f"{_base(request)}/rest/v1/rpc/doka_replace_document_version_storage",
            method="POST",
            headers=_supabase_headers(request, _token_from_request(request), "application/json"),
            body=json.dumps(rpc_payload),
        )
        if status >= 300 or not isinstance(rows, list) or not rows:
            try:
                await provider.delete(stored.object_ref)
            except Exception:
                pass
            raise HTTPException(status_code=503, detail=f"Version metadata update failed ({status}).")
        document = rows[0]
        await _audit(request, user_id, "version_create", str(signed["document_id"]), metadata.filename, {
            "sha256": metadata.sha256,
            "size_bytes": stored.size_bytes,
            "storage_provider": stored.object_ref.provider,
        })
        return {"document": document, "warnings": []}

    record = {
        "owner_id": user_id,
        "object_key": stored.object_ref.object_key,
        "filename": metadata.filename,
        "content_type": metadata.content_type,
        "size_bytes": stored.size_bytes,
        "sha256": metadata.sha256,
        "status": "active",
        "metadata": {},
        "storage_provider": stored.object_ref.provider,
        "storage_status": "ready",
        "storage_region": _env(request, "B2_REGION", "") if stored.object_ref.provider == "b2" else None,
    }
    # Do not send nullable optional metadata columns if a deployment is still
    # before the storage metadata migration.
    record = {key: value for key, value in record.items() if value is not None}
    base = _base(request)
    token = _token_from_request(request)
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents",
        method="POST",
        headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=representation"},
        body=json.dumps(record),
    )
    if status >= 300 or not isinstance(rows, list) or not rows:
        try:
            await provider.delete(stored.object_ref)
        except Exception:
            pass
        raise HTTPException(status_code=503, detail=f"Document metadata creation failed ({status}).")
    await _audit(request, user_id, "upload", str(rows[0].get("id")), rows[0].get("filename"), {
        "size_bytes": stored.size_bytes,
        "sha256": metadata.sha256,
        "storage_provider": stored.object_ref.provider,
    })
    return {"document": rows[0], "warnings": []}


@app.get("/api/documents/{document_id}/versions")
async def list_document_versions(request: Request, document_id: str, user_id: str = Depends(require_user)):
    base = _base(request)
    token = _token_from_request(request)
    doc_query = f"select=id&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
    status, docs = await _fetch(request, f"{base}/rest/v1/doka_documents?{doc_query}", headers={**_supabase_headers(request, token), "Accept": "application/json"})
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document lookup failed ({status}).")
    if not isinstance(docs, list) or not docs:
        raise HTTPException(status_code=404, detail="Document not found.")
    query = f"select=id,version_no,filename,content_type,size_bytes,sha256,created_at&document_id=eq.{quote(document_id, safe='')}&order=version_no.desc&limit=100"
    status, versions = await _fetch(request, f"{base}/rest/v1/doka_document_versions?{query}", headers={**_supabase_headers(request, token), "Accept": "application/json"})
    if status >= 300 or not isinstance(versions, list):
        raise HTTPException(status_code=503, detail=f"Version history lookup failed ({status}).")
    return {"versions": versions}


@app.post("/api/documents/{document_id}/versions")
async def create_document_version(request: Request, document_id: str, file: UploadFile = File(...), user_id: str = Depends(require_user)):
    raise HTTPException(status_code=410, detail="Direct version upload is required. Create a storage upload session with document_id first.")


@app.post("/api/documents/{document_id}/versions/{version_id}/restore")
async def restore_document_version(request: Request, document_id: str, version_id: str, user_id: str = Depends(require_user)):
    base = _base(request)
    token = _token_from_request(request)
    status, updated = await _fetch(
        request, f"{base}/rest/v1/rpc/doka_restore_document_version",
        method="POST",
        headers=_supabase_headers(request, token, "application/json"),
        body=json.dumps({"p_document_id": document_id, "p_version_id": version_id}),
    )
    if status >= 300:
        if status == 404:
            raise HTTPException(status_code=404, detail="Document or version not found.")
        raise HTTPException(status_code=503, detail=f"Version restore failed ({status}).")
    document = updated[0] if isinstance(updated, list) and updated else updated
    await _audit(request, user_id, "version_restore", document_id, document.get("filename") if isinstance(document, dict) else None, {"version_id": version_id})
    return {"document": document}


@app.get("/api/documents/{document_id}/preview")
async def document_preview(request: Request, document_id: str, user_id: str = Depends(require_user)):
    """Create a short-lived inline URL for safe passive document formats only."""
    base = _base(request)
    token = _token_from_request(request)
    query = f"select=id,object_key,sha256,content_type,filename,storage_provider&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document lookup failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    target = rows[0]
    content_type = str(target.get("content_type") or "").split(";", 1)[0].strip().lower()
    previewable = {
        "application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp",
        "text/plain", "text/csv",
    }
    if content_type not in previewable:
        raise HTTPException(status_code=415, detail="Preview is not available for this file type.")
    router = build_storage_router(request, token, _storage_fetcher)
    provider = _provider_for(router, str(target.get("storage_provider") or "supabase"))
    try:
        signed = await provider.get_signed_download(
            StorageObjectRef(str(target.get("storage_provider") or "supabase"), str(target["object_key"]), user_id),
            expires_seconds=300,
        )
    except (RuntimeError, ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=503, detail=f"Signed preview URL failed: {exc}") from exc
    await _audit(request, user_id, "preview", str(target.get("id")), target.get("filename"), {"content_type": content_type})
    return {"url": signed, "sha256": target.get("sha256", ""), "expires_seconds": 300}


@app.get("/api/documents/{document_id}/download")
async def document_download(request: Request, document_id: str, user_id: str = Depends(require_user)):
    base = _base(request)
    token = _token_from_request(request)
    query = f"select=id,owner_id,object_key,sha256,storage_provider&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document lookup failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    target = rows[0]
    provider_name = str(target.get("storage_provider") or "supabase")
    router = build_storage_router(request, token, _storage_fetcher)
    provider = _provider_for(router, provider_name)
    try:
        signed = await provider.get_signed_download(
            StorageObjectRef(provider_name, str(target["object_key"]), user_id),
            expires_seconds=300,
        )
    except (RuntimeError, ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=503, detail=f"Signed download URL failed: {exc}") from exc
    await _audit(request, user_id, "download", str(target.get("id")), None, {"sha256": target.get("sha256", ""), "storage_provider": provider_name})
    return {"url": signed, "sha256": target.get("sha256", ""), "expires_seconds": 300}


@app.patch("/api/documents/{document_id}")
async def update_document(request: Request, document_id: str, update: DocumentUpdate, user_id: str = Depends(require_user)):
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No document fields were provided.")
    if "filename" in payload:
        filename = payload["filename"].strip()
        if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename or "\x00" in filename:
            raise HTTPException(status_code=400, detail="Filename must be a plain file name.")
        payload["filename"] = filename
    if "folder_path" in payload:
        payload["folder_path"] = _normalize_folder_path(payload["folder_path"])
    result = await _update_document_fields(request, document_id, user_id, payload)
    await _audit(request, user_id, "update", document_id, result["document"].get("filename"), {"fields": sorted(payload.keys())})
    return result


async def _update_document_fields(request: Request, document_id: str, user_id: str, payload: dict):
    base = _base(request)
    token = _token_from_request(request)
    query = f"id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?select=*&{query}",
        method="PATCH",
        headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=representation"},
        body=json.dumps(payload),
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document update failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"document": rows[0]}


@app.delete("/api/documents/{document_id}")
async def trash_document(request: Request, document_id: str, user_id: str = Depends(require_user)):
    result = await _update_document_fields(
        request, document_id, user_id, {"deleted_at": datetime.now(timezone.utc).isoformat()}
    )
    await _audit(request, user_id, "trash", document_id, result["document"].get("filename"))
    return result


@app.post("/api/documents/{document_id}/restore")
async def restore_document(request: Request, document_id: str, user_id: str = Depends(require_user)):
    base = _base(request)
    token = _token_from_request(request)
    query = f"id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=not.is.null"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?select=*&{query}",
        method="PATCH",
        headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=representation"},
        body=json.dumps({"deleted_at": None}),
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document restore failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Trashed document not found.")
    await _audit(request, user_id, "restore", document_id, rows[0].get("filename"))
    return {"document": rows[0]}


@app.delete("/api/documents/{document_id}/permanent")
async def permanently_delete_document(request: Request, document_id: str, user_id: str = Depends(require_user)):
    """Permanently remove a trashed document and all stored versions."""
    base = _base(request)
    token = _token_from_request(request)
    encoded_id = quote(document_id, safe="")
    owner = quote(user_id, safe="")
    query = f"select=id,object_key,filename&id=eq.{encoded_id}&owner_id=eq.{owner}&deleted_at=not.is.null"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Trashed document lookup failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Trashed document not found.")
    document = rows[0]

    version_query = f"select=object_key&document_id=eq.{encoded_id}"
    version_status, versions = await _fetch(
        request, f"{base}/rest/v1/doka_document_versions?{version_query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if version_status >= 300:
        raise HTTPException(status_code=503, detail=f"Document version lookup failed ({version_status}).")

    keys = {str(document["object_key"])}
    if isinstance(versions, list):
        keys.update(str(row["object_key"]) for row in versions if row.get("object_key"))
    bucket = quote(_bucket(request), safe="")
    delete_status, _ = await _fetch(
        request, f"{base}/storage/v1/object/{bucket}", method="DELETE",
        headers=_supabase_headers(request, token, "application/json"),
        body=json.dumps({"prefixes": sorted(keys)}),
    )
    if delete_status >= 300:
        raise HTTPException(status_code=503, detail=f"Stored file cleanup failed ({delete_status}); metadata was retained.")

    delete_query = f"id=eq.{encoded_id}&owner_id=eq.{owner}&deleted_at=not.is.null"
    metadata_status, deleted = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{delete_query}", method="DELETE",
        headers={**_supabase_headers(request, token), "Prefer": "return=representation"},
    )
    if metadata_status >= 300 or not isinstance(deleted, list) or not deleted:
        raise HTTPException(status_code=503, detail=f"Document metadata deletion failed ({metadata_status}); retry cleanup if needed.")

    await _audit(
        request, user_id, "permanent_delete", None, document.get("filename"),
        {"document_id": document_id, "deleted_version_objects": len(keys) - 1},
    )
    return {"deleted": True, "document_id": document_id, "objects_deleted": len(keys)}


origins = ["https://enterprise-ai-dms.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

Default = asgi.entrypoint(app)
