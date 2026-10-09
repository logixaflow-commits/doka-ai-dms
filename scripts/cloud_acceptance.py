#!/usr/bin/env python3
"""Authenticated Cloud release acceptance runner.

Requires two pre-created Supabase users and access tokens. This runner deliberately
does not create accounts or accept service-role credentials. It records only
privacy-safe identifiers and response assertions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _auth(client: httpx.Client, token: str, path: str, *, method: str = "GET", **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bearer {token}"
    return client.request(method, path, headers=headers, **kwargs)


def _assert_status(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:300]}"
        )


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

    base_url = args.base_url or _require("DOKA_CLOUD_BASE_URL").rstrip("/")
    user_a = _require("DOKA_CLOUD_USER_A_TOKEN")
    user_b = _require("DOKA_CLOUD_USER_B_TOKEN")
    if user_a == user_b:
        raise SystemExit("DOKA_CLOUD_USER_A_TOKEN and DOKA_CLOUD_USER_B_TOKEN must differ.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    evidence: dict[str, object] = {
        "schema_version": 1,
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
        with httpx.Client(base_url=base_url, timeout=60.0, follow_redirects=False) as client:
            health = client.get("/health")
            _assert_status(health, 200, "cloud health")
            evidence["checks"]["health"] = True
    
            list_a = _auth(client, user_a, "/api/documents")
            _assert_status(list_a, 200, "user A document list")
    
            upload = _auth(
                client,
                user_a,
                "/api/documents",
                method="POST",
                files={"file": (filename, payload, "text/plain")},
            )
            _assert_status(upload, 200, "user A upload")
            document = upload.json().get("document") or {}
            document_id = str(document.get("id") or "")
            if not document_id:
                raise AssertionError("user A upload did not return a document id")
            created_document_ids.append(document_id)
            if document.get("sha256") != digest:
                raise AssertionError("uploaded document SHA-256 mismatch")
            evidence["checks"]["user_a_upload"] = True
    
            patch = _auth(
                client,
                user_a,
                f"/api/documents/{document_id}",
                method="PATCH",
                json={"status": "review", "metadata": {"acceptance": True}},
            )
            _assert_status(patch, 200, "user A metadata update")
            evidence["checks"]["user_a_update"] = True
    
            download_a = _auth(client, user_a, f"/api/documents/{document_id}/download")
            _assert_status(download_a, 200, "user A download")
            if download_a.json().get("sha256") != digest:
                raise AssertionError("user A download metadata SHA-256 mismatch")
            evidence["checks"]["user_a_download"] = True
    
            trash_a = _auth(client, user_a, f"/api/documents/{document_id}", method="DELETE")
            _assert_status(trash_a, 200, "user A trash")
            restore_a = _auth(client, user_a, f"/api/documents/{document_id}/restore", method="POST")
            _assert_status(restore_a, 200, "user A restore")
            evidence["checks"]["user_a_trash_restore"] = True
    
            list_b = _auth(client, user_b, "/api/documents")
            _assert_status(list_b, 200, "user B document list")
            ids_b = {str(item.get("id")) for item in list_b.json().get("documents", [])}
            if document_id in ids_b:
                raise AssertionError("cross-user document appeared in user B listing")
    
            denied_download = _auth(client, user_b, f"/api/documents/{document_id}/download")
            _assert_status(denied_download, 404, "user B cross-user download")
            evidence["checks"]["two_user_isolation"] = True
    
            if args.fifty_mib_file:
                fixture = Path(args.fifty_mib_file)
                if fixture.stat().st_size != 50 * 1024 * 1024:
                    raise AssertionError("50 MiB fixture must be exactly 52428800 bytes")
                with fixture.open("rb") as handle:
                    boundary = _auth(
                        client,
                        user_a,
                        "/api/documents",
                        method="POST",
                        files={"file": (fixture.name, handle, "application/octet-stream")},
                    )
                _assert_status(boundary, 200, "exact 50 MiB upload")
                boundary_document = boundary.json().get("document") or {}
                boundary_document_id = str(boundary_document.get("id") or "")
                if not boundary_document_id:
                    raise AssertionError("exact 50 MiB upload did not return a document id")
                created_document_ids.append(boundary_document_id)
                evidence["checks"]["exact_50_mib_boundary"] = True
    
                trash_boundary = _auth(
                    client, user_a, f"/api/documents/{boundary_document_id}", method="DELETE"
                )
                _assert_status(trash_boundary, 200, "exact 50 MiB trash")
                permanent_boundary = _auth(
                    client,
                    user_a,
                    f"/api/documents/{boundary_document_id}/permanent",
                    method="DELETE",
                )
                _assert_status(permanent_boundary, 200, "exact 50 MiB permanent cleanup")
                created_document_ids.remove(boundary_document_id)
            else:
                evidence["checks"]["exact_50_mib_boundary"] = "pending_fixture"
    
            permanent = _auth(
                client,
                user_a,
                f"/api/documents/{document_id}/permanent",
                method="DELETE",
            )
            _assert_status(permanent, 200, "user A permanent cleanup")
        created_document_ids.remove(document_id)
    
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
                            # 404 means the item was already cleaned or never persisted.
                            if permanent.status_code not in (200, 404):
                                print(
                                    f"WARNING: acceptance cleanup did not complete for one test object "
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

    evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
    evidence["gate9_ready"] = all(
        value is True
        for key, value in evidence["checks"].items()
        if key != "exact_50_mib_boundary"
    ) and evidence["checks"]["exact_50_mib_boundary"] is True

    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["gate9_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
