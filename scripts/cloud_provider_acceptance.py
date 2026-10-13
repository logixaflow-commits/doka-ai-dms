#!/usr/bin/env python3
"""Single-user live provider acceptance for Doka Cloud.

Exercises the configured source provider (Supabase or B2), byte integrity,
version history, trash/restore, Google Drive export verification, audit events,
and cleanup. Designed for the currently single-user production deployment;
never records access tokens, emails, signed URLs, document IDs, or file content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def auth_request(client: httpx.Client, token: str, path: str, *, method: str = "GET", **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bearer {token}"
    return client.request(method, path, headers=headers, **kwargs)


def assert_status(response: httpx.Response, expected: int | tuple[int, ...], label: str) -> None:
    allowed = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in allowed:
        raise AssertionError(f"{label}: expected HTTP {allowed}, got {response.status_code}")


def require_https_url(value: object, label: str) -> str:
    url = str(value or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssertionError(f"{label} did not return an absolute HTTPS URL")
    return url


def upload_bytes(
    client: httpx.Client,
    token: str,
    *,
    payload: bytes,
    filename: str,
    content_type: str,
    expected_provider: str,
    document_id: str | None = None,
) -> dict:
    digest = hashlib.sha256(payload).hexdigest()
    request_body = {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(payload),
        "sha256": digest,
        "artifact_type": "source",
    }
    if document_id:
        request_body["document_id"] = document_id
    created = auth_request(
        client, token, "/api/storage/upload-session", method="POST", json=request_body
    )
    assert_status(created, 200, "create direct upload session")
    session = created.json()
    provider = str(session.get("provider") or "")
    if provider != expected_provider:
        raise AssertionError(f"source provider mismatch: expected {expected_provider}, got {provider or 'missing'}")
    upload = session.get("upload") or {}
    upload_url = require_https_url(upload.get("url"), "direct upload session")
    method = str(upload.get("method") or "PUT").upper()
    if method not in {"PUT", "POST"}:
        raise AssertionError("direct upload session returned an unsupported method")
    direct = client.request(
        method, upload_url, headers=dict(upload.get("headers") or {}), content=payload
    )
    assert_status(direct, (200, 201, 204), "direct provider upload")
    completed = auth_request(
        client,
        token,
        "/api/storage/upload-complete",
        method="POST",
        json={
            "session_id": session.get("session_id"),
            "size_bytes": len(payload),
            "sha256": digest,
            "provider_result": {},
        },
    )
    assert_status(completed, 200, "complete and verify provider upload")
    document = completed.json().get("document") or {}
    if not document.get("id"):
        raise AssertionError("upload completion did not return a document")
    if str(document.get("sha256") or "").lower() != digest:
        raise AssertionError("document metadata SHA-256 differs from uploaded bytes")
    if int(document.get("size_bytes") or 0) != len(payload):
        raise AssertionError("document metadata size differs from uploaded bytes")
    if document.get("storage_status") != "ready":
        raise AssertionError("document is not marked storage-ready")
    return document


def download_and_verify(client: httpx.Client, token: str, document_id: str, payload: bytes) -> None:
    digest = hashlib.sha256(payload).hexdigest()
    response = auth_request(client, token, f"/api/documents/{document_id}/download")
    assert_status(response, 200, "create signed download")
    signed = response.json()
    if str(signed.get("sha256") or "").lower() != digest:
        raise AssertionError("download response SHA-256 metadata mismatch")
    url = require_https_url(signed.get("url"), "download endpoint")
    downloaded = client.get(url)
    assert_status(downloaded, 200, "download stored object")
    if hashlib.sha256(downloaded.content).hexdigest() != digest:
        raise AssertionError("downloaded bytes failed SHA-256 verification")


def export_to_google_drive(
    client: httpx.Client, token: str, document_id: str, payload: bytes
) -> None:
    digest = hashlib.sha256(payload).hexdigest()
    response = auth_request(
        client,
        token,
        f"/api/documents/{document_id}/export/google-drive/upload-session",
        method="POST",
    )
    assert_status(response, 200, "create Google Drive export session")
    session = response.json()
    if session.get("provider") != "google_drive":
        raise AssertionError("export session did not select Google Drive")
    source = session.get("source_document") or {}
    if int(source.get("size_bytes") or 0) != len(payload):
        raise AssertionError("Google Drive export source size mismatch")
    if str(source.get("sha256") or "").lower() != digest:
        raise AssertionError("Google Drive export source SHA-256 metadata mismatch")
    source_response = client.get(require_https_url(source.get("download_url"), "export source"))
    assert_status(source_response, 200, "download export source")
    if hashlib.sha256(source_response.content).hexdigest() != digest:
        raise AssertionError("source bytes failed SHA-256 before Google Drive export")

    upload = session.get("upload") or {}
    upload_url = require_https_url(upload.get("url"), "Google Drive resumable session")
    if urlparse(upload_url).hostname not in {"www.googleapis.com", "content.googleapis.com"}:
        raise AssertionError("Google Drive upload session returned an unexpected host")
    method = str(upload.get("method") or "PUT").upper()
    if method not in {"PUT", "POST"}:
        raise AssertionError("Google Drive upload session returned an unsupported method")
    direct = client.request(
        method,
        upload_url,
        headers=dict(upload.get("headers") or {}),
        content=source_response.content,
    )
    assert_status(direct, (200, 201), "upload bytes to Google Drive")
    file_id = str((direct.json() if direct.content else {}).get("id") or "")
    if not file_id:
        raise AssertionError("Google Drive upload response did not include a file ID")

    completed = auth_request(
        client,
        token,
        f"/api/documents/{document_id}/export/google-drive/complete",
        method="POST",
        json={
            "session_id": session.get("session_id"),
            "file_id": file_id,
            "size_bytes": len(payload),
            "sha256": digest,
        },
    )
    assert_status(completed, 200, "verify Google Drive export completion")
    document = completed.json().get("document") or {}
    if document.get("export_provider") != "google_drive" or document.get("export_status") != "ready":
        raise AssertionError("document metadata did not confirm a verified Google Drive export")
    if not str(document.get("export_reference") or "").startswith("drive:"):
        raise AssertionError("verified Google Drive export reference is missing")


def best_effort_cleanup(client: httpx.Client, token: str, document_id: str) -> bool:
    try:
        trash = auth_request(client, token, f"/api/documents/{document_id}", method="DELETE")
        if trash.status_code not in (200, 404):
            return False
        deleted = auth_request(
            client, token, f"/api/documents/{document_id}/permanent", method="DELETE"
        )
        return deleted.status_code == 200 and deleted.json().get("deleted") is True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("DOKA_CLOUD_BASE_URL", "").strip())
    parser.add_argument("--provider", choices=("supabase", "b2"), default="b2")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    base_url = (args.base_url or require_env("DOKA_CLOUD_BASE_URL")).rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("DOKA_CLOUD_BASE_URL must be an absolute HTTPS URL")
    token = require_env("DOKA_CLOUD_USER_TOKEN")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {
        "schema_version": 1,
        "provider_required": args.provider,
        "provider_selected": None,
        "privacy": {
            "tokens_recorded": False,
            "emails_recorded": False,
            "signed_urls_recorded": False,
            "document_ids_recorded": False,
            "file_content_recorded": False,
        },
        "checks": {},
    }
    created_id: str | None = None
    started = time.monotonic()
    payload_v1 = b"Doka live provider acceptance v1\n"
    payload_v2 = b"Doka live provider acceptance v2 - version check\n"
    try:
        with httpx.Client(base_url=base_url, timeout=120.0, follow_redirects=False) as client:
            health = client.get("/health")
            assert_status(health, 200, "cloud health")
            evidence["checks"]["health"] = True

            listing = auth_request(client, token, "/api/documents")
            assert_status(listing, 200, "authenticated document listing")
            evidence["checks"]["authenticated_supabase_session"] = True

            first = upload_bytes(
                client, token, payload=payload_v1, filename="doka-provider-acceptance.txt",
                content_type="text/plain", expected_provider=args.provider,
            )
            created_id = str(first["id"])
            evidence["provider_selected"] = first.get("storage_provider")
            evidence["checks"]["provider_upload_and_metadata"] = True
            download_and_verify(client, token, created_id, payload_v1)
            evidence["checks"]["provider_download_sha256"] = True

            second = upload_bytes(
                client, token, payload=payload_v2, filename="doka-provider-acceptance.txt",
                content_type="text/plain", expected_provider=args.provider, document_id=created_id,
            )
            if str(second.get("sha256") or "").lower() != hashlib.sha256(payload_v2).hexdigest():
                raise AssertionError("new document version SHA-256 metadata mismatch")
            versions = auth_request(client, token, f"/api/documents/{created_id}/versions")
            assert_status(versions, 200, "list document versions")
            version_rows = versions.json().get("versions") or []
            if len(version_rows) < 1:
                raise AssertionError("version history did not return the uploaded version")
            evidence["checks"]["version_upload_and_history"] = True

            download_and_verify(client, token, created_id, payload_v2)
            evidence["checks"]["latest_version_download_sha256"] = True

            export_to_google_drive(client, token, created_id, payload_v2)
            evidence["checks"]["google_drive_export_and_verification"] = True

            trashed = auth_request(client, token, f"/api/documents/{created_id}", method="DELETE")
            assert_status(trashed, 200, "trash acceptance document")
            restored = auth_request(
                client, token, f"/api/documents/{created_id}/restore", method="POST"
            )
            assert_status(restored, 200, "restore acceptance document")
            evidence["checks"]["trash_and_restore"] = True

            audit = auth_request(client, token, "/api/audit?limit=100")
            assert_status(audit, 200, "list audit events")
            actions = {
                str(event.get("action") or "")
                for event in (audit.json().get("events") or [])
                if isinstance(event, dict)
            }
            expected_actions = {"upload", "download", "version_create", "export"}
            if not expected_actions.issubset(actions):
                raise AssertionError("audit log is missing one or more expected lifecycle actions")
            evidence["checks"]["audit_lifecycle_events"] = True

            if not best_effort_cleanup(client, token, created_id):
                raise AssertionError("acceptance document cleanup was not confirmed")
            created_id = None
            evidence["checks"]["permanent_cleanup"] = True
    except Exception as exc:
        evidence["passed"] = False
        evidence["failure_class"] = type(exc).__name__
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if created_id:
            try:
                with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=False) as cleanup_client:
                    evidence["checks"]["best_effort_cleanup"] = best_effort_cleanup(
                        cleanup_client, token, created_id
                    )
            except Exception:
                evidence["checks"]["best_effort_cleanup"] = False
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2, sort_keys=True))
        print(f"Acceptance failed at {evidence.get('failure_class')}; response details and credentials were not recorded.", file=sys.stderr)
        return 2

    evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
    evidence["passed"] = all(value is True for value in evidence["checks"].values())
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
