from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


SUPABASE_SOURCE_MAX_BYTES = 50 * 1024 * 1024
CLOUDINARY_DERIVATIVE_MAX_BYTES = 10 * 1000 * 1000
B2_MULTIPART_THRESHOLD_BYTES = 5 * 1024 * 1024 * 1024


class StorageProviderName(StrEnum):
    MOCK = "mock"
    SUPABASE = "supabase"
    B2 = "b2"
    CLOUDINARY = "cloudinary"


class StorageArtifactType(StrEnum):
    SOURCE = "source"
    PREVIEW = "preview"
    THUMBNAIL = "thumbnail"
    COVER = "cover"


@dataclass(frozen=True)
class StorageObjectRef:
    provider: str
    object_key: str
    owner_id: str


@dataclass(frozen=True)
class UploadMetadata:
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    owner_id: str
    artifact_type: StorageArtifactType = StorageArtifactType.SOURCE

    def validate(self) -> None:
        if not self.owner_id or len(self.owner_id) > 255:
            raise ValueError("owner_id is required")
        if not self.filename or len(self.filename) > 255:
            raise ValueError("filename must be 1-255 characters")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256 or ""):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")
        if "/" not in self.content_type or len(self.content_type) > 255:
            raise ValueError("content_type is invalid")


@dataclass(frozen=True)
class SignedUpload:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadSession:
    provider: str
    object_ref: StorageObjectRef
    expires_at: int
    upload: SignedUpload
    warnings: tuple[str, ...] = ()
    session_id: str = ""


@dataclass(frozen=True)
class StoredObjectResult:
    object_ref: StorageObjectRef
    size_bytes: int
    sha256: str
    content_type: str


class StorageProvider(Protocol):
    name: str

    def create_upload_session(self, metadata: UploadMetadata) -> UploadSession: ...
    def complete_upload(self, session: UploadSession, client_result: dict[str, Any]) -> StoredObjectResult: ...
    def get_signed_download(self, object_ref: StorageObjectRef, expires_seconds: int = 900) -> str: ...
    def delete(self, object_ref: StorageObjectRef) -> None: ...
    def head(self, object_ref: StorageObjectRef) -> StoredObjectResult: ...
    def initiateMultipartUpload(self, metadata: UploadMetadata) -> Any: ...
    def uploadPart(self, upload: Any, part_number: int, checksum: str, signed_request: Any) -> Any: ...
    def completeMultipartUpload(self, upload: Any, parts: list[Any]) -> StoredObjectResult: ...
    def abortMultipartUpload(self, upload: Any) -> None: ...


def sha256_for_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_filename(filename: str) -> str:
    value = Path(filename.replace("\\", "/")).name.strip("._")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value[:255] or "document"


def owner_object_key(metadata: UploadMetadata) -> str:
    metadata.validate()
    filename = _safe_filename(metadata.filename)
    digest = metadata.sha256.lower()
    if metadata.artifact_type is StorageArtifactType.SOURCE:
        return f"users/{metadata.owner_id}/documents/{digest}/{filename}"
    return f"users/{metadata.owner_id}/derivatives/{metadata.artifact_type.value}/{digest}/{filename}"


class StorageRouter:
    """Select a provider without allowing provider credentials into callers."""

    def __init__(self, providers: dict[str, StorageProvider], *, provider_mode: str | None = None) -> None:
        self.providers = providers
        self.provider_mode = (provider_mode or os.getenv("STORAGE_PROVIDER", "hybrid")).strip().lower()

    def route(self, metadata: UploadMetadata) -> StorageProvider:
        metadata.validate()
        if self.provider_mode == "mock":
            provider = self.providers.get(StorageProviderName.MOCK.value)
            if provider is None:
                raise RuntimeError("Mock storage provider is not configured")
            return provider
        if self.provider_mode not in {"hybrid", "supabase"}:
            raise ValueError("STORAGE_PROVIDER must be mock, hybrid, or supabase")
        if metadata.artifact_type is not StorageArtifactType.SOURCE:
            if metadata.size_bytes >= CLOUDINARY_DERIVATIVE_MAX_BYTES:
                raise ValueError("Cloudinary derivative artifacts must be smaller than 10 MB")
            if self.provider_mode == "supabase":
                return self._require("supabase")
            return self._require("cloudinary")
        if metadata.size_bytes <= SUPABASE_SOURCE_MAX_BYTES:
            return self._require("supabase")
        return self._require("b2")

    def _require(self, name: str) -> StorageProvider:
        provider = self.providers.get(name)
        if provider is None:
            raise RuntimeError(f"Storage provider {name!r} is not configured")
        return provider

    def route_name(self, metadata: UploadMetadata) -> str:
        return str(self.route(metadata).name)
