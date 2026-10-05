"""Google Drive user-owned export/backup adapter.

The Worker only initiates the Drive resumable session and verifies completion.
Document bytes are uploaded by the browser directly to the Drive session URL.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import quote

from shared.storage_contracts import SignedUpload, StorageObjectRef, StoredObjectResult, UploadMetadata


@dataclass(frozen=True)
class GoogleDriveConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    folder_id: str = ""


class GoogleDriveExportProvider:
    name = "google_drive"

    def __init__(self, config: GoogleDriveConfig, fetcher):
        if not all((config.client_id, config.client_secret, config.refresh_token)):
            raise ValueError("Google Drive OAuth configuration is incomplete")
        self.config = config
        self.fetcher = fetcher

    async def _access_token(self) -> str:
        status, payload = await self.fetcher(
            "https://oauth2.googleapis.com/token",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=(
                "client_id=" + quote(self.config.client_id, safe="") +
                "&client_secret=" + quote(self.config.client_secret, safe="") +
                "&refresh_token=" + quote(self.config.refresh_token, safe="") +
                "&grant_type=refresh_token"
            ),
        )
        if status >= 300 or not isinstance(payload, dict):
            raise RuntimeError("Google Drive OAuth token refresh failed")
        token = str(payload.get("access_token") or "")
        if not token:
            raise RuntimeError("Google Drive OAuth response did not contain an access token")
        return token

    async def create_upload_session(self, metadata: UploadMetadata) -> tuple[StorageObjectRef, SignedUpload, int]:
        metadata.validate()
        token = await self._access_token()
        parents = [self.config.folder_id] if self.config.folder_id else []
        drive_metadata = {
            "name": f"Doka Backup - {metadata.filename}",
            "mimeType": metadata.content_type,
            "appProperties": {
                "doka_sha256": metadata.sha256.lower(),
                "doka_size_bytes": str(metadata.size_bytes),
                "doka_owner_id": metadata.owner_id,
            },
        }
        if parents:
            drive_metadata["parents"] = parents
        status, headers = await self.fetcher(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": metadata.content_type,
                "X-Upload-Content-Length": str(metadata.size_bytes),
            },
            body=json.dumps(drive_metadata),
            return_headers=True,
        )
        if status >= 300 or not isinstance(headers, dict):
            raise RuntimeError("Google Drive resumable upload session creation failed")
        location = str(headers.get("location") or headers.get("Location") or "")
        if not location.startswith("https://www.googleapis.com/"):
            raise RuntimeError("Google Drive did not return a safe resumable upload URL")
        ref = StorageObjectRef(self.name, f"pending/{metadata.owner_id}/{metadata.sha256.lower()}", metadata.owner_id)
        return ref, SignedUpload("PUT", location, {"Content-Type": metadata.content_type}), int(time.time()) + 3600

    async def verify_completion(
        self,
        object_ref: StorageObjectRef,
        file_id: str,
        *,
        expected_size: int,
        expected_sha256: str,
    ) -> StoredObjectResult:
        token = await self._access_token()
        safe_id = quote(file_id, safe="")
        status, payload = await self.fetcher(
            f"https://www.googleapis.com/drive/v3/files/{safe_id}?fields=id,name,size,mimeType,appProperties,sha256Checksum,md5Checksum,ownedByMe",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )
        if status >= 300 or not isinstance(payload, dict):
            raise RuntimeError("Google Drive completion verification failed")
        if not payload.get("ownedByMe", True):
            raise RuntimeError("Google Drive export file is not owned by the configured user")
        size = int(payload.get("size") or 0)
        app_properties = payload.get("appProperties") or {}
        digest = str(payload.get("sha256Checksum") or app_properties.get("doka_sha256") or "").lower()
        if size != expected_size or digest != expected_sha256.lower():
            raise ValueError("Google Drive export failed size/SHA-256 verification")
        return StoredObjectResult(
            StorageObjectRef(self.name, f"drive:{file_id}", object_ref.owner_id),
            size,
            digest,
            str(payload.get("mimeType") or "application/octet-stream"),
        )

    async def get_download_url(self, file_id: str) -> str:
        token = await self._access_token()
        safe_id = quote(file_id, safe="")
        return f"https://www.googleapis.com/drive/v3/files/{safe_id}?alt=media&access_token={quote(token, safe='')}"
