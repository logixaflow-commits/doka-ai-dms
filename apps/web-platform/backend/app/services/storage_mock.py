from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .storage_router import SignedUpload, StorageObjectRef, StoredObjectResult, UploadMetadata, UploadSession, owner_object_key


@dataclass
class _MockEntry:
    data: bytes
    content_type: str
    sha256: str


class MockStorageProvider:
    """Credential-free provider for local tests and deterministic CI."""

    name = "mock"

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else None
        self.objects: dict[str, _MockEntry] = {}
        self.sessions: dict[str, UploadMetadata] = {}
        if self.root:
            self.root.mkdir(parents=True, exist_ok=True)

    def create_upload_session(self, metadata: UploadMetadata) -> UploadSession:
        metadata.validate()
        key = owner_object_key(metadata)
        session_id = uuid.uuid5(uuid.NAMESPACE_URL, f"doka-mock:{metadata.owner_id}:{key}").hex
        self.sessions[session_id] = metadata
        return UploadSession(
            provider=self.name,
            object_ref=StorageObjectRef(self.name, key, metadata.owner_id),
            expires_at=int(time.time()) + 900,
            upload=SignedUpload(method="PUT", url=f"mock://upload/{session_id}"),
            session_id=session_id,
        )

    def put_bytes(self, session_id: str, data: bytes) -> StoredObjectResult:
        metadata = self.sessions[session_id]
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != metadata.size_bytes or digest != metadata.sha256.lower():
            raise ValueError("Mock upload failed size/SHA-256 verification")
        key = owner_object_key(metadata)
        self.objects[key] = _MockEntry(data, metadata.content_type, digest)
        if self.root:
            path = self.root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return self.head(StorageObjectRef(self.name, key, metadata.owner_id))

    def complete_upload(self, session: UploadSession, client_result: dict[str, Any]) -> StoredObjectResult:
        expected = self.sessions.get(session.session_id)
        if expected is None:
            raise ValueError("Unknown mock upload session")
        data = client_result.get("data")
        if not isinstance(data, bytes):
            raise ValueError("Mock completion requires bytes")
        return self.put_bytes(session.session_id, data)

    def get_signed_download(self, object_ref: StorageObjectRef, expires_seconds: int = 900) -> str:
        if object_ref.owner_id not in object_ref.object_key:
            raise PermissionError("Owner-scoped object key mismatch")
        if object_ref.object_key not in self.objects:
            raise KeyError(object_ref.object_key)
        return f"mock://download/{object_ref.object_key}?expires={max(1, int(expires_seconds))}"

    def delete(self, object_ref: StorageObjectRef) -> None:
        self.objects.pop(object_ref.object_key, None)
        if self.root:
            path = self.root / object_ref.object_key
            if path.exists():
                path.unlink()

    def head(self, object_ref: StorageObjectRef) -> StoredObjectResult:
        entry = self.objects[object_ref.object_key]
        return StoredObjectResult(object_ref, len(entry.data), entry.sha256, entry.content_type)

    def initiateMultipartUpload(self, metadata: UploadMetadata) -> dict[str, Any]:
        raise NotImplementedError("Mock multipart is intentionally not required for local source routing")

    def uploadPart(self, upload: Any, part_number: int, checksum: str, signed_request: Any) -> Any:
        raise NotImplementedError

    def completeMultipartUpload(self, upload: Any, parts: list[Any]) -> StoredObjectResult:
        raise NotImplementedError

    def abortMultipartUpload(self, upload: Any) -> None:
        return None
