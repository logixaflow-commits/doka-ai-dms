import asyncio

from cloudflare_worker.storage_google_drive import GoogleDriveConfig, GoogleDriveExportProvider
from storage_contracts_compat import UploadMetadata


def run(coro):
    return asyncio.run(coro)


def test_google_drive_resumable_session_keeps_oauth_secret_out_of_browser_upload():
    calls = []

    async def fetcher(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        return 200, {"location": "https://www.googleapis.com/upload/drive/v3/files/resumable-session"}

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token", "folder-id"),
        fetcher,
    )
    meta = UploadMetadata("doc.pdf", "application/pdf", 1024, "a" * 64, "owner")
    ref, upload, expires = run(provider.create_upload_session(meta))
    assert ref.provider == "google_drive"
    assert upload.url.startswith("https://www.googleapis.com/")
    assert "client-secret" not in str(upload)
    assert "refresh-token" not in str(upload)
    assert expires > 0
    assert calls[0][1]["body"].startswith("client_id=client-id")


def test_google_drive_completion_verifies_owner_size_and_sha256():
    async def fetcher(url, **kwargs):
        if url.endswith("/token"):
            return 200, {"access_token": "short-lived-access-token"}
        return 200, {
            "id": "drive-file-1",
            "size": "1024",
            "mimeType": "application/pdf",
            "ownedByMe": True,
            "appProperties": {"doka_sha256": "a" * 64},
        }

    provider = GoogleDriveExportProvider(
        GoogleDriveConfig("client-id", "client-secret", "refresh-token"),
        fetcher,
    )
    result = run(provider.verify_completion(
        provider_ref := __import__("cloudflare_worker.storage_contracts_compat", fromlist=["StorageObjectRef"]).StorageObjectRef("google_drive", "pending/owner/a"*1, "owner"),
        "drive-file-1",
        expected_size=1024,
        expected_sha256="a" * 64,
    ))
    assert result.object_ref.object_key == "drive:drive-file-1"
