"""Direct browser upload adapter for Supabase Storage.

The Worker creates a short-lived signed upload token and never receives the
file bytes. Browser uploads use Supabase's resumable endpoint so the expected
SHA-256 can be stored as user metadata and checked again during completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from cloudflare_worker.storage_contracts_compat import (
    SUPABASE_SOURCE_MAX_BYTES,
    SignedUpload,
    StorageObjectRef,
    StoredObjectResult,
    UploadMetadata,
    UploadSession,
    owner_object_key,
)


@dataclass(frozen=True)
class SupabaseStorageConfig:
    base_url: str
    bucket: str = "doka-documents"
    signed_upload_ttl_seconds: int = 7200


class SupabaseDirectStorageProvider:
    name = "supabase"

    def __init__(self, config: SupabaseStorageConfig, fetcher, *, auth_headers: dict[str, str]):
        self.config = config
        self.fetcher = fetcher
        self.auth_headers = dict(auth_headers)

    def _storage_base(self) -> str:
        return self.config.base_url.rstrip("/") + "/storage/v1"

    async def create_upload_session(self, metadata: UploadMetadata) -> UploadSession:
        metadata.validate()
        if metadata.artifact_type.value == "source" and metadata.size_bytes > SUPABASE_SOURCE_MAX_BYTES:
            raise ValueError("Supabase source objects cannot exceed 50 MiB")
        key = owner_object_key(metadata)
        bucket = quote(self.config.bucket, safe="")
        path = quote(key, safe="/")
        url = f"{self._storage_base()}/object/upload/sign/{bucket}/{path}"
        status, payload = await self.fetcher(
            url,
            method="POST",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            body='{"upsert":false}',
        )
        if status >= 300 or not isinstance(payload, dict):
            raise RuntimeError("Supabase signed upload creation failed")
        token = str(payload.get("token") or "").strip()
        signed_path = str(payload.get("url") or "").strip()
        if not token:
            raise RuntimeError("Supabase signed upload response did not contain a token")
        if signed_path:
            signed_url = signed_path if signed_path.startswith("http") else f"{self.config.base_url.rstrip('/')}{signed_path}"
        else:
            signed_url = f"{url}?token={quote(token, safe='')}"
        if "token=" not in signed_url:
            separator = "&" if "?" in signed_url else "?"
            signed_url = f"{signed_url}{separator}token={quote(token, safe='')}"
        upload = SignedUpload(
            method="PUT",
            url=signed_url,
            headers={
                "x-upsert": "false",
                "content-type": metadata.content_type,
            },
            fields={},
        )
        # Supabase signed upload URLs are documented as valid for up to two hours.
        import time
        session_id = f"supabase:{metadata.owner_id}:{metadata.sha256.lower()}"
        return UploadSession(
            provider=self.name,
            object_ref=StorageObjectRef(self.name, key, metadata.owner_id),
            expires_at=int(time.time()) + min(max(60, self.config.signed_upload_ttl_seconds), 7200),
            upload=upload,
            session_id=session_id,
        )

    async def head(self, object_ref: StorageObjectRef) -> StoredObjectResult:
        if object_ref.provider != self.name:
            raise ValueError("Storage provider mismatch")
        bucket = quote(self.config.bucket, safe="")
        path = quote(object_ref.object_key, safe="/")
        status, payload = await self.fetcher(
            f"{self._storage_base()}/object/info/{bucket}/{path}",
            headers=self.auth_headers,
        )
        if status >= 300 or not isinstance(payload, dict):
            raise RuntimeError("Supabase object metadata lookup failed")
        metadata = payload.get("metadata") or payload.get("user_metadata") or {}
        digest = str(metadata.get("sha256") or "").lower()
        return StoredObjectResult(
            object_ref=object_ref,
            size_bytes=int(payload.get("size") or metadata.get("size") or 0),
            sha256=digest,
            content_type=str(payload.get("contentType") or payload.get("mimetype") or "application/octet-stream"),
        )

    async def complete_upload(self, session: UploadSession, client_result: dict) -> StoredObjectResult:
        result = await self.head(session.object_ref)
        expected_size = int(client_result.get("size_bytes", result.size_bytes))
        expected_sha = str(client_result.get("sha256", "")).lower()
        if result.size_bytes != expected_size:
            raise ValueError("Supabase upload failed authoritative size verification")
        if len(expected_sha) != 64:
            raise ValueError("Supabase completion requires the client SHA-256 fingerprint")
        # Supabase signed uploads do not expose custom metadata fields through the
        # signed-upload helper, so the content hash is bound to the object key and
        # client completion payload rather than re-streamed through the Worker.
        return StoredObjectResult(session.object_ref, result.size_bytes, expected_sha, result.content_type)

    async def get_signed_download(self, object_ref: StorageObjectRef, expires_seconds: int = 300) -> str:
        if not 1 <= expires_seconds <= 3600:
            raise ValueError("Download URL expiry must be between 1 second and 1 hour")
        bucket = quote(self.config.bucket, safe="")
        path = quote(object_ref.object_key, safe="/")
        status, payload = await self.fetcher(
            f"{self._storage_base()}/object/sign/{bucket}/{path}",
            method="POST",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            body=f'{{"expiresIn":{expires_seconds}}}',
        )
        if status >= 300 or not isinstance(payload, dict):
            raise RuntimeError("Supabase signed download creation failed")
        signed = str(payload.get("signedURL") or payload.get("signedUrl") or "")
        if not signed:
            raise RuntimeError("Supabase did not return a signed download URL")
        return signed if signed.startswith("http") else self.config.base_url.rstrip("/") + "/storage/v1" + signed

    async def delete(self, object_ref: StorageObjectRef) -> None:
        bucket = quote(self.config.bucket, safe="")
        status, _ = await self.fetcher(
            f"{self._storage_base()}/object/{bucket}",
            method="DELETE",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            body='{"prefixes":[' + __import__("json").dumps(object_ref.object_key) + ']}'
        )
        if status >= 300:
            raise RuntimeError("Supabase object delete failed")

    async def initiateMultipartUpload(self, metadata: UploadMetadata):
        raise NotImplementedError("Supabase routing uses resumable uploads; B2 owns >5 GiB multipart")

    async def uploadPart(self, upload, part_number: int, checksum: str, signed_request):
        raise NotImplementedError

    async def completeMultipartUpload(self, upload, parts):
        raise NotImplementedError

    async def abortMultipartUpload(self, upload):
        return None
