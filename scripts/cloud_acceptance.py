#!/usr/bin/env python3
"""Authenticated Cloud release acceptance runner.

Uses the production direct-upload session contract; file bytes never pass
through the Cloudflare Worker. Requires two pre-created Supabase users and
access tokens. Evidence is privacy-safe and never records tokens or emails.
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


MAX_SOURCE_BYTES = 50 * 1024 * 1024


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _auth(client: httpx.Client, token: str, path: str, *, method: str = "GET", **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bearer {token}"
    return client.request(method, path, headers=headers, **kwargs)


def _assert_status(response: httpx.Response, expected: int | tuple[int, ...], label: str) -> None:
    allowed = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in allowed:
        raise AssertionError(f"{label}: expected HTTP {allowed}, got {response.status_code}")


def _upload_document(
    client: httpx.Client, token: str, payload: bytes, filename: str, content_type: str
) -> dict:
    """Upload through the signed provider URL, then verify Worker completion."""
    digest = hashlib.sha256(payload).hexdigest()
    session_response = _auth(
        client,
        token,
        "/api/storage/upload-session",
        method="POST",
        json={
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(payload),
            "sha256": digest,
            "artifact_type": "source",
        },
    )
    _assert_status(session_response, 200, "create direct-upload session")
    session = session_response.json()
    provider = str(session.get("provider") or "")
    if provider not in {"supabase", "b2"}:
        raise AssertionError("source upload selected an unsupported storage provider")
    upload = session.get("upload") or {}
    upload_url = str(upload.get("url") or "")
    parsed = urlparse(upload_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssertionError("direct-upload session did not return a safe HTTPS URL")
    method = str(upload.get("method") or "PUT").upper()
    if method not in {"PUT", "POST"}:
        raise AssertionError("direct-upload session returned an unsupported method")
    direct = client.request(
        method,
        upload_url,
        headers=dict(upload.get("headers") or {}),
        content=payload,
    )
    _assert_status(direct, (200, 201, 204), "direct provider upload")

    completion = _auth(
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
    _assert_status(completion, 200, "verify direct upload completion")
    document = completion.json().get("document") or {}
    document_id = str(document.get("id") or "")
    if not document_id:
        raise AssertionError("verified source upload did not return a document id")
    if str(document.get("sha256") or "").lower() != digest:
        raise AssertionError("uploaded document SHA-256 metadata mismatch")
    if int(document.get("size_bytes") or 0) != len(payload):
        raise AssertionError("uploaded document size metadata mismatch")
    if document.get("storage_status") != "ready":
        raise AssertionError("uploaded document is not marked storage-ready")
    return document


def _download_and_verify(client: httpx.Client, token: str, document_id: str, expected_sha256: str) -> None:
    response = _auth(client, token, f"/api/documents/{document_id}/download")
    _assert_status(response, 200, "create signed download URL")
    signed = response.json()
    if str(signed.get("sha256") or "").lower() != expected_sha256:
        raise AssertionError("download metadata SHA-256 mismatch")
    url = str(signed.get("url") or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssertionError("download endpoint did not return a safe HTTPS URL")
    downloaded = client.get(url)
    _assert_status(downloaded, 200, "download stored object")
    if hashlib.sha256(downloaded.content).hexdigest() != expected_sha256:
        raise AssertionError("downloaded object SHA-256 mismatch")


def _trash_and_permanently_delete(client: httpx.Client, token: str, document_id: str) -> None:
    trashed = _auth(client, token, f"/api/documents/{document_id}", method="DELETE")
    _assert_status(trashed, 200, "trash document before permanent deletion")
    deleted = _auth(
        client, token, f"/api/documents/{document_id}/permanent", method="DELETE"
    )
    _assert_status(deleted, 200, "permanently delete document")
    if deleted.json().get("deleted") is not True:
        raise AssertionError("permanent cleanup was not confirmed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("DOKA_CLOUD_BASE_URL", "").strip())
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--fifty-mib-file",
        default=os.getenv("DOKA_CLOUD_50MIB_FILE", "").strip(),
        help="Optional exact 50 MiB fixture used for the 50 MiB acceptance boundary.",
    )
    args = parser.parse_args()

    base_url = (args.base_url or _require("DOKA_CLOUD_BASE_URL")).rstrip("/")
    if urlparse(base_url).scheme != "https":
        raise SystemExit("DOKA_CLOUD_BASE_URL must use HTTPS")
    user_a = _require("DOKA_CLOUD_USER_A_TOKEN")
    user_b = _require("DOKA_CLOUD_USER_B_TOKEN")
    if user_a == user_b:
        raise SystemExit("DOKA_CLOUD_USER_A_TOKEN and DOKA_CLOUD_USER_B_TOKEN must differ.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {
        "schema_version": 2,
        "privacy": {"tokens_recorded": False, "emails_recorded": False},
        "base_url_recorded": False,
        "checks": {},
    }
    payload = b"Doka cloud acceptance fixture\n"
    filename = "gate9-acceptance.txt"
    digest = hashlib.sha256(payload).hexdigest()
    started = time.monotonic()
    created_document_ids: list[str] = []

    try:
        with httpx.Client(base_url=base_url, timeout=90.0, follow_redirects=False) as client:
            health = client.get("/health")
            _assert_status(health, 200, "cloud health")
            evidence["checks"]["health"] = True

            list_a = _auth(client, user_a, "/api/documents")
            _assert_status(list_a, 200, "user A document list")
            evidence["checks"]["user_a_list"] = True

            document = _upload_document(client, user_a, payload, filename, "text/plain")
            document_id = str(document["id"])
            created_document_ids.append(document_id)
            evidence["checks"]["user_a_upload"] = True
            evidence["checks"]["upload_integrity"] = True

            patch = _auth(
                client,
                user_a,
                f"/api/documents/{document_id}",
                method="PATCH",
                json={"status": "review", "metadata": {"acceptance": True}},
            )
            _assert_status(patch, 200, "user A metadata update")
            evidence["checks"]["user_a_update"] = True

            _download_and_verify(client, user_a, document_id, digest)
            evidence["checks"]["user_a_download_integrity"] = True

            trashed = _auth(client, user_a, f"/api/documents/{document_id}", method="DELETE")
            _assert_status(trashed, 200, "user A trash")
            restored = _auth(
                client, user_a, f"/api/documents/{document_id}/restore", method="POST"
            )
            _assert_status(restored, 200, "user A restore")
            evidence["checks"]["user_a_trash_restore"] = True

            list_b = _auth(client, user_b, "/api/documents")
            _assert_status(list_b, 200, "user B document list")
            ids_b = {
                str(item.get("id"))
                for item in list_b.json().get("documents", [])
                if isinstance(item, dict)
            }
            if document_id in ids_b:
                raise AssertionError("cross-user document appeared in user B listing")
            denied_download = _auth(
                client, user_b, f"/api/documents/{document_id}/download"
            )
            _assert_status(denied_download, 404, "user B cross-user download")
            evidence["checks"]["two_user_isolation"] = True

            if args.fifty_mib_file:
                fixture = Path(args.fifty_mib_file)
                if fixture.stat().st_size != MAX_SOURCE_BYTES:
                    raise AssertionError("50 MiB fixture must be exactly 52428800 bytes")
                boundary_payload = fixture.read_bytes()
                boundary_digest = hashlib.sha256(boundary_payload).hexdigest()
                boundary = _upload_document(
                    client, user_a, boundary_payload, fixture.name, "application/octet-stream"
                )
                boundary_id = str(boundary["id"])
                created_document_ids.append(boundary_id)
                if boundary_digest != str(boundary.get("sha256") or "").lower():
                    raise AssertionError("exact 50 MiB upload integrity mismatch")
                _download_and_verify(client, user_a, boundary_id, boundary_digest)
                evidence["checks"]["exact_50_mib_boundary"] = True
                evidence["checks"]["exact_50_mib_download_integrity"] = True
                _trash_and_permanently_delete(client, user_a, boundary_id)
                created_document_ids.remove(boundary_id)
            else:
                evidence["checks"]["exact_50_mib_boundary"] = "pending_fixture"
                evidence["checks"]["exact_50_mib_download_integrity"] = "pending_fixture"

            _trash_and_permanently_delete(client, user_a, document_id)
            created_document_ids.remove(document_id)
            evidence["checks"]["permanent_cleanup"] = True
    except Exception as exc:
        evidence["passed"] = False
        evidence["failure_class"] = type(exc).__name__
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
        evidence["gate9_ready"] = False
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 2
    finally:
        # Best-effort cleanup also runs when any assertion fails midway.
        if created_document_ids:
            try:
                with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=False) as cleanup_client:
                    for cleanup_id in reversed(created_document_ids):
                        try:
                            trashed = _auth(
                                cleanup_client, user_a, f"/api/documents/{cleanup_id}", method="DELETE"
                            )
                            if trashed.status_code not in (200, 404):
                                continue
                            permanent = _auth(
                                cleanup_client,
                                user_a,
                                f"/api/documents/{cleanup_id}/permanent",
                                method="DELETE",
                            )
                            if permanent.status_code not in (200, 404):
                                print(
                                    "WARNING: acceptance cleanup did not complete for one test object "
                                    f"(HTTP {permanent.status_code}).",
                                    file=sys.stderr,
                                )
                        except Exception:
                            print(
                                "WARNING: acceptance cleanup encountered a transport error.",
                                file=sys.stderr,
                            )
            except Exception:
                print("WARNING: acceptance cleanup client could not be opened.", file=sys.stderr)

    checks = evidence["checks"]
    evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
    evidence["gate9_ready"] = all(
        value is True
        for key, value in checks.items()
        if key not in {"exact_50_mib_boundary", "exact_50_mib_download_integrity"}
    ) and checks["exact_50_mib_boundary"] is True and checks["exact_50_mib_download_integrity"] is True
    evidence["passed"] = evidence["gate9_ready"] is True
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["gate9_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
