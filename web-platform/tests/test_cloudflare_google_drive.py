from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from cloudflare_worker.storage_google_drive import GoogleDriveConfig, GoogleDriveExportProvider
from storage_contracts_compat import StorageObjectRef, UploadMetadata


def run(coro):
    return asyncio.run(coro)


def test_google_drive_resumable_session_supports_shared_drives_and_keeps_secrets_server_side():
    calls = []

    async def fetcher(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        if kwargs.get("return_headers"):
            return 200, {
                "location": "https://www.googleapis.com/upload/drive/v3/files/resumable-session"
            }
        raise AssertionError(f"unexpected fetch: {url}")

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token", "shared-folder-id"),
        fetcher,
    )
    digest = hashlib.sha256(b"test document").hexdigest()
    metadata = UploadMetadata("doc.txt", "text/plain", 13, digest, "owner")
    ref, upload, expires = run(provider.create_upload_session(metadata))

    assert ref.provider == "google_drive"
    assert upload.url.startswith("https://www.googleapis.com/")
    assert "client-secret" not in str(upload)
    assert "refresh-token" not in str(upload)
    assert expires > 0
    assert "supportsAllDrives=true" in calls[1][0]
    drive_request = calls[1][1]
    assert json.loads(drive_request["body"])["parents"] == ["shared-folder-id"]


def test_google_drive_completion_accepts_verified_shared_drive_parent():
    digest = hashlib.sha256(b"test document").hexdigest()
    calls = []

    async def fetcher(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        if "alt=media" in url:
            assert kwargs.get("return_sha256") is True
            return 200, {"size_bytes": 13, "sha256": digest}
        return 200, {
            "id": "shared-file-id",
            "size": "13",
            "mimeType": "text/plain",
            "parents": ["shared-folder-id"],
            "driveId": "shared-drive-id",
            "ownedByMe": False,
            "appProperties": {"doka_sha256": digest},
            "sha256Checksum": digest,
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token", "shared-folder-id"),
        fetcher,
    )
    result = run(
        provider.verify_completion(
            StorageObjectRef("google_drive", "pending/owner/digest", "owner"),
            "shared-file-id",
            expected_size=13,
            expected_sha256=digest,
        )
    )

    assert result.object_ref.object_key == "drive:shared-file-id"
    assert result.size_bytes == 13
    assert result.sha256 == digest
    assert "supportsAllDrives=true" in calls[1][0]
    assert "parents" in calls[1][0]
    assert any("alt=media" in url for url, _ in calls)


def test_google_drive_completion_rejects_file_outside_configured_folder():
    digest = hashlib.sha256(b"test document").hexdigest()

    async def fetcher(url, **kwargs):
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        return 200, {
            "id": "unexpected-file",
            "size": "13",
            "mimeType": "text/plain",
            "parents": ["different-folder"],
            "driveId": "shared-drive-id",
            "ownedByMe": False,
            "sha256Checksum": digest,
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token", "shared-folder-id"),
        fetcher,
    )
    with pytest.raises(RuntimeError, match="configured destination folder"):
        run(
            provider.verify_completion(
                StorageObjectRef("google_drive", "pending/owner/digest", "owner"),
                "unexpected-file",
                expected_size=13,
                expected_sha256=digest,
            )
        )


def test_google_drive_root_export_requires_configured_user_ownership():
    digest = hashlib.sha256(b"data").hexdigest()

    async def fetcher(url, **kwargs):
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        return 200, {
            "id": "drive-file-2",
            "size": "4",
            "mimeType": "application/octet-stream",
            "appProperties": {"doka_sha256": digest},
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token"),
        fetcher,
    )
    with pytest.raises(RuntimeError, match="not owned"):
        run(
            provider.verify_completion(
                StorageObjectRef("google_drive", "pending/owner/digest", "owner"),
                "drive-file-2",
                expected_size=4,
                expected_sha256=digest,
            )
        )


def test_google_drive_completion_rejects_wrong_size_or_digest():
    digest = hashlib.sha256(b"correct").hexdigest()

    async def fetcher(url, **kwargs):
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        return 200, {
            "id": "drive-file-3",
            "size": "5",
            "mimeType": "application/pdf",
            "ownedByMe": True,
            "appProperties": {"doka_sha256": "c" * 64},
            "sha256Checksum": "c" * 64,
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token"),
        fetcher,
    )
    with pytest.raises(ValueError, match="size/SHA-256"):
        run(
            provider.verify_completion(
                StorageObjectRef("google_drive", "pending/owner/digest", "owner"),
                "drive-file-3",
                expected_size=4,
                expected_sha256=digest,
            )
        )



def test_google_drive_completion_hashes_downloaded_bytes_instead_of_trusting_app_properties():
    digest = hashlib.sha256(b"correct").hexdigest()

    async def fetcher(url, **kwargs):
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        if "alt=media" in url:
            return 200, {"size_bytes": 7, "sha256": "0" * 64}
        return 200, {
            "id": "drive-file-4",
            "size": "7",
            "mimeType": "text/plain",
            "ownedByMe": True,
            "appProperties": {"doka_sha256": digest},
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token"),
        fetcher,
    )
    with pytest.raises(ValueError, match="size/SHA-256"):
        run(
            provider.verify_completion(
                StorageObjectRef("google_drive", "pending/owner/digest", "owner"),
                "drive-file-4",
                expected_size=7,
                expected_sha256=digest,
            )
        )



def test_google_drive_completion_stream_verifies_large_file_without_inline_size_cap():
    large_size = 50 * 1024 * 1024 + 1
    calls = []

    async def fetcher(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        if "alt=media" in url:
            assert kwargs.get("return_sha256") is True
            assert kwargs.get("max_bytes") == 1024 * 1024 * 1024
            return 200, {"size_bytes": large_size, "sha256": "a" * 64}
        return 200, {
            "id": "large-file",
            "size": str(large_size),
            "mimeType": "application/octet-stream",
            "ownedByMe": True,
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token"),
        fetcher,
    )
    result = run(
        provider.verify_completion(
            StorageObjectRef("google_drive", "pending/owner/digest", "owner"),
            "large-file",
            expected_size=large_size,
            expected_sha256="a" * 64,
        )
    )
    assert result.size_bytes == large_size
    assert result.sha256 == "a" * 64
