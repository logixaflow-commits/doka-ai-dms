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
    }


@app.get("/api/documents/{document_id}/versions")
async def list_document_versions(request: Request, document_id: str, user_id: str = Depends(require_user)):
    base = _base(request); token = _token_from_request(request)
    query = f"select=id,document_id,version_no,filename,content_type,size_bytes,sha256,created_at&document_id=eq.{quote(document_id, safe='')}&order=version_no.desc"
    status, rows = await _fetch(request, f"{base}/rest/v1/doka_document_versions?{query}", headers={**_supabase_headers(request, token), "Accept":"application/json"})
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Version lookup failed ({status}).")
    return {"versions": rows if isinstance(rows, list) else []}

@app.post("/api/documents/{document_id}/versions")
async def create_document_version(request: Request, document_id: str, user_id: str = Depends(require_user)):
    token = _token_from_request(request); base = _base(request)
    form = await request.form()
    file = form.get("file")
    if not hasattr(file, "read"):
        raise HTTPException(status_code=400, detail="Multipart field 'file' is required.")
    data = await file.read()
    if len(data) > int(_env(request, "DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024))):
        raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
    digest = hashlib.sha256(data).hexdigest()
    raw_name = (getattr(file, "filename", None) or "document").replace("\\", "/").rsplit("/", 1)[-1]
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._") or "document"
    object_key = f"users/{user_id}/documents/{digest}/{safe_name}"
    content_type = getattr(file, "content_type", None) or "application/octet-stream"
    bucket = quote(_bucket(request), safe="")
    key = quote(object_key, safe="/")
    put_status, put_payload = await _fetch(request, f"{base}/storage/v1/object/{bucket}/{key}", method="POST", headers=_supabase_headers(request, token, content_type), body=data)
    if put_status >= 300:
        raise HTTPException(status_code=503, detail=f"Version object upload failed ({put_status}).")
    rpc_payload = {"p_document_id": document_id, "p_object_key": object_key, "p_filename": getattr(file, "filename", None) or "document", "p_content_type": content_type, "p_size_bytes": len(data), "p_sha256": digest}
    status, rows = await _fetch(request, f"{base}/rest/v1/rpc/doka_replace_document_version", method="POST", headers=_supabase_headers(request, token, "application/json"), body=json.dumps(rpc_payload))
    if status >= 300:
        try:
            await _fetch(request, f"{base}/storage/v1/object/{bucket}/{key}", method="DELETE", headers=_supabase_headers(request, token))
        except Exception:
            pass
        raise HTTPException(status_code=503, detail=f"Version metadata update failed ({status}).")
    doc = rows[0] if isinstance(rows, list) and rows else rows
    await _audit(request, user_id, "version_create", document_id, getattr(file, "filename", None), {"sha256": digest})
    return {"document": doc}

@app.post("/api/documents/{document_id}/versions/{version_id}/restore")
async def restore_document_version(request: Request, document_id: str, version_id: str, user_id: str = Depends(require_user)):
    token = _token_from_request(request); base = _base(request)
    payload = {"p_document_id": document_id, "p_version_id": version_id}
    status, rows = await _fetch(request, f"{base}/rest/v1/rpc/doka_restore_document_version", method="POST", headers=_supabase_headers(request, token, "application/json"), body=json.dumps(payload))
    if status >= 300:
        raise HTTPException(status_code=404 if status == 404 else 503, detail=f"Version restore failed ({status}).")
    doc = rows[0] if isinstance(rows, list) and rows else rows
    await _audit(request, user_id, "version_restore", document_id, doc.get("filename") if isinstance(doc, dict) else None, {"version_id": version_id})
    return {"document": doc}

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
    await _audit(request, user_id, "upload", str(rows[0].get("id")), rows[0].get("filename"), {"size_bytes": len(data), "sha256": digest})
    return {"document": rows[0]}


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
    base = _base(request)
    token = _token_from_request(request)
    doc_query = f"select=id,object_key,filename,content_type,size_bytes,sha256&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
    status, docs = await _fetch(request, f"{base}/rest/v1/doka_documents?{doc_query}", headers={**_supabase_headers(request, token), "Accept": "application/json"})
    if status >= 300:
        raise HTTPException(status_code=503, detail=f"Document lookup failed ({status}).")
    if not isinstance(docs, list) or not docs:
        raise HTTPException(status_code=404, detail="Document not found.")
    current = docs[0]
    max_bytes = int(_env(request, "DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024)))
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="Object exceeds configured maximum size.")
    digest = hashlib.sha256(data).hexdigest()
    filename = (file.filename or current.get("filename") or "document").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename or len(filename) > 255:
        raise HTTPException(status_code=400, detail="Filename must be a plain file name up to 255 characters.")
    content_type = (file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower() or "application/octet-stream"
    if len(content_type) > 255:
        raise HTTPException(status_code=400, detail="Content type is too long.")
    key = _object_key(user_id, digest, filename)
    if key == current.get("object_key"):
        raise HTTPException(status_code=409, detail="The uploaded content is identical to the current document.")
    bucket = quote(_bucket(request), safe="")
    encoded_key = quote(key, safe="/")
    version_query = f"select=id&document_id=eq.{quote(document_id, safe='')}&object_key=eq.{quote(key, safe='')}&limit=1"
    version_status, existing_versions = await _fetch(
        request, f"{base}/rest/v1/doka_document_versions?{version_query}",
        headers={**_supabase_headers(request, token), "Accept": "application/json"},
    )
    if version_status >= 300 or not isinstance(existing_versions, list):
        raise HTTPException(status_code=503, detail=f"Existing version lookup failed ({version_status}).")
    uploaded_new_object = False
    if not existing_versions:
        upload_headers = _supabase_headers(request, token, content_type)
        upload_headers["x-upsert"] = "false"
        status, _ = await _fetch(request, f"{base}/storage/v1/object/{bucket}/{encoded_key}", method="POST", headers=upload_headers, body=_js_bytes(data))
        if status >= 300:
            raise HTTPException(status_code=503, detail=f"Version object upload failed ({status}).")
        uploaded_new_object = True
    payload = {
        "p_document_id": document_id,
        "p_object_key": key,
        "p_filename": filename,
        "p_content_type": content_type,
        "p_size_bytes": len(data),
        "p_sha256": digest,
    }
    status, updated = await _fetch(request, f"{base}/rest/v1/rpc/doka_replace_document_version", method="POST", headers=_supabase_headers(request, token, "application/json"), body=json.dumps(payload))
    if status >= 300:
        if uploaded_new_object:
            await _fetch(request, f"{base}/storage/v1/object/{bucket}", method="DELETE", headers=_supabase_headers(request, token, "application/json"), body=json.dumps({"prefixes": [key]}))
        raise HTTPException(status_code=503, detail=f"Version metadata update failed ({status}).")
    document = updated[0] if isinstance(updated, list) and updated else updated
    await _audit(request, user_id, "version_create", document_id, filename, {"sha256": digest, "size_bytes": len(data)})
    return {"document": document}


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
    query = f"select=id,object_key,sha256,content_type,filename&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
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
    bucket = quote(_bucket(request), safe="")
    key = quote(str(target["object_key"]), safe="/")
    status, payload = await _fetch(
        request, f"{base}/storage/v1/object/sign/{bucket}/{key}",
        method="POST",
        headers=_supabase_headers(request, token, "application/json"),
        body=json.dumps({"expiresIn": 300}),
    )
    if status >= 300 or not isinstance(payload, dict):
        raise HTTPException(status_code=503, detail=f"Signed preview URL failed ({status}).")
    signed = payload.get("signedURL") or payload.get("signedUrl")
    if not signed:
        raise HTTPException(status_code=503, detail="Supabase Storage did not return a signed URL.")
    if not str(signed).startswith("http"):
        signed = f"{base}/storage/v1{signed}"
    await _audit(request, user_id, "preview", str(target.get("id")), target.get("filename"), {"content_type": content_type})
    return {"url": signed, "sha256": target.get("sha256", ""), "expires_seconds": 300}


@app.get("/api/documents/{document_id}/download")
async def document_download(request: Request, document_id: str, user_id: str = Depends(require_user)):
    base = _base(request)
    token = _token_from_request(request)
    query = f"select=id,owner_id,object_key,sha256&id=eq.{quote(document_id, safe='')}&owner_id=eq.{quote(user_id, safe='')}&deleted_at=is.null&limit=1"
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
    await _audit(request, user_id, "download", str(target.get("id")), None, {"sha256": target.get("sha256", "")})
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
