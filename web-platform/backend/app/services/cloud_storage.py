from __future__ import annotations

import hashlib
import io
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib.parse import quote

import boto3
import httpx


_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,1023}$")


class StorageError(RuntimeError):
    """Base error for provider-neutral object storage operations."""


class StorageNotConfigured(StorageError):
    """Raised when a requested storage provider has no complete configuration."""


class StorageIntegrityError(StorageError):
    """Raised when an uploaded/downloaded object fails SHA-256 verification."""


class StorageQuotaError(StorageError):
    """Raised before an object would exceed the configured logical quota."""


@dataclass(frozen=True)
class StoredObject:
    key: str
    size: int
    sha256: str
    content_type: str


class ObjectStorage(Protocol):
    def put(self, key: str, body: BinaryIO, *, content_type: str, expected_sha256: str | None = None) -> StoredObject: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def head(self, key: str) -> StoredObject: ...
    def signed_get_url(self, key: str, *, expires_seconds: int = 900) -> str: ...


def normalize_key(key: str) -> str:
    value = str(key or "").strip().replace("\\", "/")
    if value.startswith("/") or value.endswith("/") or "//" in value:
        raise StorageError("Storage key must be a relative object path.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise StorageError("Storage key contains an unsafe path component.")
    if not _KEY_RE.fullmatch(value):
        raise StorageError("Storage key contains unsupported characters or is too long.")
    return value


def _stream_sha256(body: BinaryIO) -> tuple[int, str, bytes]:
    if not body.seekable():
        data = body.read()
    else:
        position = body.tell()
        data = body.read()
        body.seek(position)
    digest = hashlib.sha256(data).hexdigest()
    return len(data), digest, data


class QuotaGuard:
    def __init__(self, *, max_object_bytes: int = 50 * 1024 * 1024, max_total_bytes: int = 0) -> None:
        self.max_object_bytes = max(0, int(max_object_bytes))
        self.max_total_bytes = max(0, int(max_total_bytes))

    def check_object(self, size: int) -> None:
        if self.max_object_bytes and size > self.max_object_bytes:
            raise StorageQuotaError(f"Object exceeds max size of {self.max_object_bytes} bytes.")

    def check_total(self, current_bytes: int, incoming_bytes: int, replacing_bytes: int = 0) -> None:
        if self.max_total_bytes and current_bytes - replacing_bytes + incoming_bytes > self.max_total_bytes:
            raise StorageQuotaError("Configured storage quota would be exceeded.")


class R2ObjectStorage:
    def __init__(self, *, bucket: str, endpoint_url: str, access_key_id: str, secret_access_key: str, quota: QuotaGuard | None = None) -> None:
        if not all([bucket, endpoint_url, access_key_id, secret_access_key]):
            raise StorageNotConfigured("R2 storage configuration is incomplete.")
        self.bucket = bucket
        self.quota = quota or QuotaGuard()
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url.rstrip("/"),
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def put(self, key: str, body: BinaryIO, *, content_type: str, expected_sha256: str | None = None) -> StoredObject:
        key = normalize_key(key)
        size, digest, data = _stream_sha256(body)
        self.quota.check_object(size)
        if expected_sha256 and digest.lower() != expected_sha256.lower():
            raise StorageIntegrityError("Upload content does not match the expected SHA-256.")
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type or "application/octet-stream",
            Metadata={"sha256": digest},
        )
        return StoredObject(key, size, digest, content_type or "application/octet-stream")

    def get(self, key: str) -> bytes:
        key = normalize_key(key)
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        data = response["Body"].read()
        expected = str(response.get("Metadata", {}).get("sha256", "")).lower()
        actual = hashlib.sha256(data).hexdigest()
        if expected and expected != actual:
            raise StorageIntegrityError("Stored object SHA-256 metadata does not match content.")
        return data

    def head(self, key: str) -> StoredObject:
        key = normalize_key(key)
        response = self.client.head_object(Bucket=self.bucket, Key=key)
        metadata = response.get("Metadata", {})
        digest = str(metadata.get("sha256", "")).lower()
        return StoredObject(key, int(response.get("ContentLength", 0)), digest, response.get("ContentType", "application/octet-stream"))

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=normalize_key(key))

    def signed_get_url(self, key: str, *, expires_seconds: int = 900) -> str:
        if not 1 <= expires_seconds <= 604800:
            raise StorageError("Signed URL expiry must be between 1 second and 7 days.")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": normalize_key(key)},
            ExpiresIn=expires_seconds,
        )


class SupabaseObjectStorage:
    def __init__(self, *, project_url: str, bucket: str, access_token: str, api_key: str, quota: QuotaGuard | None = None) -> None:
        if not all([project_url, bucket, access_token, api_key]):
            raise StorageNotConfigured("Supabase Storage configuration is incomplete.")
        self.base_url = project_url.rstrip("/")
        self.bucket = bucket
        self.access_token = access_token
        self.api_key = api_key
        self.quota = quota or QuotaGuard()

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"apikey": self.api_key, "Authorization": f"Bearer {self.access_token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def put(self, key: str, body: BinaryIO, *, content_type: str, expected_sha256: str | None = None) -> StoredObject:
        key = normalize_key(key)
        size, digest, data = _stream_sha256(body)
        self.quota.check_object(size)
        if expected_sha256 and digest.lower() != expected_sha256.lower():
            raise StorageIntegrityError("Upload content does not match the expected SHA-256.")
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}/{quote(key, safe='/')}"
        response = httpx.post(
            url,
            headers={**self._headers(content_type), "x-upsert": "false", "x-metadata": f'{{"sha256":"{digest}"}}'},
            content=data,
            timeout=30.0,
        )
        if response.status_code >= 300:
            raise StorageError(f"Supabase Storage upload failed ({response.status_code}).")
        return StoredObject(key, size, digest, content_type or "application/octet-stream")

    def get(self, key: str) -> bytes:
        key = normalize_key(key)
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}/{quote(key, safe='/')}"
        response = httpx.get(url, headers=self._headers(), timeout=30.0)
        if response.status_code == 404:
            raise StorageError("Stored object was not found.")
        if response.status_code >= 300:
            raise StorageError(f"Supabase Storage download failed ({response.status_code}).")
        return response.content

    def head(self, key: str) -> StoredObject:
        data = self.get(key)
        return StoredObject(key, len(data), hashlib.sha256(data).hexdigest(), "application/octet-stream")

    def delete(self, key: str) -> None:
        url = f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}"
        response = httpx.delete(url, headers=self._headers("application/json"), json={"prefixes": [normalize_key(key)]}, timeout=30.0)
        if response.status_code >= 300:
            raise StorageError(f"Supabase Storage delete failed ({response.status_code}).")

    def signed_get_url(self, key: str, *, expires_seconds: int = 900) -> str:
        if not 1 <= expires_seconds <= 604800:
            raise StorageError("Signed URL expiry must be between 1 second and 7 days.")
        object_key = normalize_key(key)
        url = f"{self.base_url}/storage/v1/object/sign/{quote(self.bucket, safe='')}/{quote(object_key, safe='/')}"
        response = httpx.post(url, headers=self._headers("application/json"), json={"expiresIn": expires_seconds}, timeout=10.0)
        if response.status_code >= 300:
            raise StorageError(f"Supabase Storage signed URL failed ({response.status_code}).")
        value = response.json().get("signedURL") or response.json().get("signedUrl")
        if not value:
            raise StorageError("Supabase Storage did not return a signed URL.")
        return value if value.startswith("http") else f"{self.base_url}/storage/v1{value}"


def build_object_storage(*, access_token: str | None = None) -> ObjectStorage:
    provider = os.getenv("DOKA_STORAGE_PROVIDER", "disabled").strip().lower()
    quota = QuotaGuard(
        max_object_bytes=int(os.getenv("DOKA_STORAGE_MAX_OBJECT_BYTES", str(50 * 1024 * 1024))),
        max_total_bytes=int(os.getenv("DOKA_STORAGE_MAX_TOTAL_BYTES", "0")),
    )
    if provider == "r2":
        return R2ObjectStorage(
            bucket=os.getenv("R2_BUCKET", ""),
            endpoint_url=os.getenv("R2_ENDPOINT_URL", ""),
            access_key_id=os.getenv("R2_ACCESS_KEY_ID", ""),
            secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", ""),
            quota=quota,
        )
    if provider == "supabase":
        return SupabaseObjectStorage(
            project_url=os.getenv("SUPABASE_URL", ""),
            bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "doka-documents"),
            access_token=access_token or os.getenv("SUPABASE_STORAGE_ACCESS_TOKEN", ""),
            api_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
            quota=quota,
        )
    raise StorageNotConfigured("DOKA_STORAGE_PROVIDER must be 'supabase' or 'r2' when cloud storage is enabled.")
