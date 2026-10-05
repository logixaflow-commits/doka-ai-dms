"""Direct browser upload adapter for Supabase Storage.

The Worker creates a short-lived signed upload token and never receives the
file bytes. Browser uploads use Supabase's resumable endpoint so the expected
SHA-256 can be stored as user metadata and checked again during completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from shared.storage_contracts import (
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
        if not token:
            raise RuntimeError("Supabase signed upload response did not contain a token")
        resumable = f"{self._storage_base()}/upload/resumable"
        upload = SignedUpload(
            method="PATCH",
            url=resumable,
            headers={
                "x-signature": token,
                "x-upsert": "false",
                "x-storage-bucket": self.config.bucket,
            },
            fields={
                "bucketName": self.config.bucket,
                "objectName": key,
                "contentType": metadata.content_type,
                "metadata": f'{{"sha256":"{metadata.sha256.lower()}","expectedSize":{metadata.size_bytes}}}',
            },
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
        if len(digest) != 64:
            raise RuntimeError("Supabase object is missing authoritative SHA-256 metadata")
        return StoredObjectResult(
            object_ref=object_ref,
            size_bytes=int(payload.get("size") or metadata.get("size") or 0),
            sha256=digest,
            content_type=str(payload.get("contentType") or payload.get("mimetype") or "application/octet-stream"),
        )

    async def complete_upload(self, session: UploadSession, client_result: dict) -> StoredObjectResult:
        result = await self.head(session.object_ref)
        expected_size = int(client_result.get("size_bytes", result.size_bytes))
        expected_sha = str(client_result.get("sha256", result.sha256)).lower()
        if result.size_bytes != expected_size or result.sha256 != expected_sha:
            raise ValueError("Supabase upload failed authoritative size/SHA-256 verification")
        return result

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
