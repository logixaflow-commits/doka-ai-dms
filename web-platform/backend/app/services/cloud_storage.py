from __future__ import annotations

import hashlib
import io
import mimetypes
import os
import re
from dataclasses import dataclass
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
    def total_bytes(self) -> int: ...
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


class CloudinaryObjectStorage:
    """Private Cloudinary raw-asset storage for the Cloud Edition."""

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        quota: QuotaGuard | None = None,
    ) -> None:
        if not all([cloud_name, api_key, api_secret]):
            raise StorageNotConfigured("Cloudinary storage configuration is incomplete.")
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.quota = quota or QuotaGuard()
        self.upload_base_url = f"https://api.cloudinary.com/v1_1/{quote(cloud_name, safe='')}"
        self.admin_base_url = self.upload_base_url

    def _signature(self, params: dict[str, object]) -> str:
        payload = "&".join(
            f"{key}={params[key]}"
            for key in sorted(params)
            if params[key] is not None and str(params[key]) != ""
        )
        return hashlib.sha1((payload + self.api_secret).encode("utf-8")).hexdigest()

    def _signed_params(self, params: dict[str, object]) -> dict[str, str]:
        values = {key: str(value) for key, value in params.items() if value is not None}
        values["api_key"] = self.api_key
        values["signature"] = self._signature(params)
        return values

    def put(
        self,
        key: str,
        body: BinaryIO,
        *,
        content_type: str,
        expected_sha256: str | None = None,
    ) -> StoredObject:
        key = normalize_key(key)
        size, digest, data = _stream_sha256(body)
        self.quota.check_object(size)
        if expected_sha256 and digest.lower() != expected_sha256.lower():
            raise StorageIntegrityError("Upload content does not match the expected SHA-256.")

        timestamp = int(__import__("time").time())
        params: dict[str, object] = {
            "public_id": key,
            "timestamp": timestamp,
            "type": "private",
            "overwrite": "false",
            "context": f"sha256={digest}",
        }
        response = httpx.post(
            f"{self.upload_base_url}/raw/upload",
            data=self._signed_params(params),
            files={"file": (key.rsplit("/", 1)[-1], data, content_type or "application/octet-stream")},
            timeout=60.0,
        )
        if response.status_code >= 300:
            raise StorageError(f"Cloudinary Storage upload failed ({response.status_code}).")
        payload = response.json()
        if str(payload.get("public_id", "")) != key:
            raise StorageIntegrityError("Cloudinary returned an unexpected public ID.")
        return StoredObject(
            key=key,
            size=int(payload.get("bytes", size)),
            sha256=digest,
            content_type=content_type or "application/octet-stream",
        )

    def total_bytes(self) -> int:
        total = 0
        next_cursor: str | None = None
        while True:
            params = {"max_results": "500"}
            if next_cursor:
                params["next_cursor"] = next_cursor
            response = httpx.get(
                f"{self.admin_base_url}/resources/raw/private",
                params=params,
                auth=(self.api_key, self.api_secret),
                timeout=30.0,
            )
            if response.status_code >= 300:
                raise StorageError(f"Cloudinary Storage usage check failed ({response.status_code}).")
            payload = response.json()
            total += sum(int(item.get("bytes", 0) or 0) for item in payload.get("resources", []))
            next_cursor = payload.get("next_cursor")
            if not next_cursor:
                return total

    def _private_download_url(self, key: str, *, expires_seconds: int) -> str:
        if not 1 <= expires_seconds <= 604800:
            raise StorageError("Signed URL expiry must be between 1 second and 7 days.")
        key = normalize_key(key)
        suffix = key.rsplit("/", 1)[-1]
        if "." not in suffix:
            raise StorageError("Cloudinary raw assets require a file extension for private downloads.")
        public_id, file_format = key.rsplit(".", 1)
        timestamp = int(__import__("time").time())
        expires_at = timestamp + expires_seconds
        params: dict[str, object] = {
            "expires_at": expires_at,
            "format": file_format,
            "public_id": public_id,
            "timestamp": timestamp,
        }
        signed = self._signed_params(params)
        from urllib.parse import urlencode
        query = urlencode(signed)
        return f"{self.upload_base_url}/raw/download?{query}"

    def get(self, key: str) -> bytes:
        url = self._private_download_url(key, expires_seconds=60)
        response = httpx.get(url, timeout=60.0)
        if response.status_code == 404:
            raise StorageError("Stored object was not found.")
        if response.status_code >= 300:
            raise StorageError(f"Cloudinary Storage download failed ({response.status_code}).")
        data = response.content
        metadata = self.head(key)
        if metadata.sha256 and metadata.sha256 != hashlib.sha256(data).hexdigest():
            raise StorageIntegrityError("Cloudinary stored object SHA-256 metadata does not match content.")
        return data

    def head(self, key: str) -> StoredObject:
        key = normalize_key(key)
        response = httpx.get(
            f"{self.admin_base_url}/resources/raw/private/{quote(key, safe='/')}",
            auth=(self.api_key, self.api_secret),
            timeout=15.0,
        )
        if response.status_code == 404:
            raise StorageError("Stored object was not found.")
        if response.status_code >= 300:
            raise StorageError(f"Cloudinary Storage metadata lookup failed ({response.status_code}).")
        payload = response.json()
        context = payload.get("context") or {}
        custom = context.get("custom") or {}
        return StoredObject(
            key=key,
            size=int(payload.get("bytes", 0) or 0),
            sha256=str(custom.get("sha256", "")).lower(),
            content_type=str(custom.get("content_type") or mimetypes.guess_type(key)[0] or "application/octet-stream"),
        )

    def delete(self, key: str) -> None:
        key = normalize_key(key)
        timestamp = int(__import__("time").time())
        params: dict[str, object] = {
            "invalidate": "true",
            "public_id": key,
            "timestamp": timestamp,
            "type": "private",
        }
        response = httpx.post(
            f"{self.upload_base_url}/raw/destroy",
            data=self._signed_params(params),
            timeout=30.0,
        )
        if response.status_code >= 300:
            raise StorageError(f"Cloudinary Storage delete failed ({response.status_code}).")
        if response.json().get("result") not in {"ok", "not found"}:
            raise StorageError("Cloudinary Storage delete did not complete successfully.")

    def signed_get_url(self, key: str, *, expires_seconds: int = 900) -> str:
        return self._private_download_url(key, expires_seconds=expires_seconds)


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
        if self.quota.max_total_bytes:
            self.quota.check_total(self.total_bytes(), size, 0)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type or "application/octet-stream",
            Metadata={"sha256": digest},
        )
        return StoredObject(key, size, digest, content_type or "application/octet-stream")

    def total_bytes(self) -> int:
        total = 0
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket):
            total += sum(int(item.get("Size", 0)) for item in page.get("Contents", []))
        return total

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
        if self.quota.max_total_bytes:
            self.quota.check_total(self.total_bytes(), size, 0)
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

    def total_bytes(self) -> int:
        # Storage list results contain immediate children only. Recurse into
        # folder entries so the optional quota covers nested users/<uid>/ paths.
        total = 0
        pending = [""]
        visited: set[str] = set()
        while pending:
            prefix = pending.pop()
            if prefix in visited:
                continue
            visited.add(prefix)
            offset = 0
            while True:
                response = httpx.post(
                    f"{self.base_url}/storage/v1/object/list/{quote(self.bucket, safe='')}",
                    headers=self._headers("application/json"),
                    json={"prefix": prefix, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}},
                    timeout=30.0,
                )
                if response.status_code >= 300:
                    raise StorageError(f"Supabase Storage usage check failed ({response.status_code}).")
                items = response.json()
                for item in items:
                    name = str(item.get("name", ""))
                    if not name:
                        continue
                    if item.get("id") is None:
                        pending.append(f"{prefix}{name}/")
                    else:
                        metadata = item.get("metadata") or {}
                        total += int(metadata.get("size", item.get("size", 0)) or 0)
                if len(items) < 1000:
                    break
                offset += len(items)
        return total

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
    if provider == "cloudinary":
        return CloudinaryObjectStorage(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
            api_key=os.getenv("CLOUDINARY_API_KEY", ""),
            api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
            quota=quota,
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
    raise StorageNotConfigured(
        "DOKA_STORAGE_PROVIDER must be 'cloudinary', 'supabase' or 'r2' when cloud storage is enabled."
    )
