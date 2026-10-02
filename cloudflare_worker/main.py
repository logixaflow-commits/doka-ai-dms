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
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from js import Object, Uint8Array, fetch as js_fetch
from pyodide.ffi import to_js
from workers import asgi, env as worker_env


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


async def _fetch(request, url: str, *, method: str = "GET", headers: dict | None = None, body=None):
    options = {"method": method, "headers": to_js(headers or {}, dict_converter=Object.fromEntries)}
    if body is not None:
        options["body"] = body
    response = await js_fetch(url, to_js(options, dict_converter=Object.fromEntries))
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
    }


@app.get("/api/documents")
async def list_documents(
    request: Request,
    user_id: str = Depends(require_user),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    base = _base(request)
    query = f"select=*&owner_id=eq.{quote(user_id, safe='')}&order=created_at.desc&limit={limit}&offset={offset}"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, _token_from_request(request)), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document listing failed ({status}).")
    return {"documents": rows if isinstance(rows, list) else []}


def _token_from_request(request) -> str:
    value = request.headers.get("authorization", "")
    return value[7:].strip() if value.lower().startswith("bearer ") else ""


@app.post("/api/documents")
async def create_document(request: Request, file: UploadFile = File(...), user_id: str = Depends(require_user)):
    max_bytes = int(_env(request, "DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024)))
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
    digest = hashlib.sha256(data).hexdigest()
    key = _object_key(user_id, digest, file.filename or "document")
    base = _base(request)
    bucket = quote(_bucket(request), safe="")
    object_path = quote(key, safe="/")
    token = _token_from_request(request)
    storage_headers = _supabase_headers(request, token, file.content_type or "application/octet-stream")
    storage_headers["x-upsert"] = "false"
    status, result = await _fetch(
        request, f"{base}/storage/v1/object/{bucket}/{object_path}",
        method="POST", headers=storage_headers, body=_js_bytes(data),
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Supabase Storage upload failed ({status}).")
    record = {
        "owner_id": user_id,
        "object_key": key,
        "filename": file.filename or "document",
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(data),
        "sha256": digest,
        "status": "active",
        "metadata": {},
    }
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents",
        method="POST",
        headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=representation"},
        body=json.dumps(record),
    )
    if status >= 300 or not isinstance(rows, list) or not rows:
        # Best-effort cleanup of the newly uploaded object only.
        await _fetch(
            request, f"{base}/storage/v1/object/{bucket}",
            method="DELETE",
            headers=_supabase_headers(request, token, "application/json"),
            body=json.dumps({"prefixes": [key]}),
        )
        raise HTTPException(status_code=503, detail=f"Document metadata creation failed ({status}).")
    return {"document": rows[0]}


@app.get("/api/documents/{document_id}/download")
async def document_download(request: Request, document_id: str, user_id: str = Depends(require_user)):
    base = _base(request)
    token = _token_from_request(request)
    query = f"select=id,owner_id,object_key,sha256&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&limit=1"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?{query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document lookup failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    target = rows[0]
    bucket = quote(_bucket(request), safe="")
    key = quote(str(target["object_key"]), safe="/")
    status, payload = await _fetch(
        request, f"{base}/storage/v1/object/sign/{bucket}/{key}",
        method="POST",
        headers=_supabase_headers(request, token, "application/json"),
        body=json.dumps({"expiresIn": 300}),
    )
    if status >= 300 or not isinstance(payload, dict):
        raise HTTPException(status_code=503, detail=f"Signed download URL failed ({status}).")
    signed = payload.get("signedURL") or payload.get("signedUrl")
    if not signed:
        raise HTTPException(status_code=503, detail="Supabase Storage did not return a signed URL.")
    if not str(signed).startswith("http"):
        signed = f"{base}/storage/v1{signed}"
    return {"url": signed, "sha256": target.get("sha256", ""), "expires_seconds": 300}


@app.patch("/api/documents/{document_id}")
async def update_document(request: Request, document_id: str, update: DocumentUpdate, user_id: str = Depends(require_user)):
    if update.status is None and update.metadata is None:
        raise HTTPException(status_code=400, detail="No document fields were provided.")
    base = _base(request)
    token = _token_from_request(request)
    query = f"id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}"
    status, rows = await _fetch(
        request, f"{base}/rest/v1/doka_documents?select=*&{query}",
        method="PATCH",
        headers={**_supabase_headers(request, token, "application/json"), "Prefer": "return=representation"},
        body=json.dumps(update.model_dump(exclude_none=True)),
    )
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document update failed ({status}).")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"document": rows[0]}


origins = ["https://enterprise-ai-dms.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

Default = asgi.entrypoint(app)
