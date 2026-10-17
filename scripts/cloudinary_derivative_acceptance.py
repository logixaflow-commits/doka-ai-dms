#!/usr/bin/env python3
"""Staging-only end-to-end Cloudinary derivative upload, verification and cleanup."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import time
import uuid
import zlib
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

import httpx

STAGING_WORKER_HOST = "doka-ai-dms-staging.logixaflow.workers.dev"


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or "\n" in value or "\r" in value:
        raise SystemExit(f"Missing or invalid staging Cloudinary acceptance setting: {name}")
    return value


def _assert_staging_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname != STAGING_WORKER_HOST:
        raise SystemExit("Refusing Cloudinary acceptance unless the exact dedicated staging Worker is configured.")


def _png_1x1() -> bytes:
    def chunk(name: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixels = zlib.compress(b"\x00\x00\x00\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def _cloudinary_signature(params: dict[str, str], api_secret: str) -> str:
    canonical = "&".join(
        f"{key}={params[key]}"
        for key in sorted(params)
        if params[key] is not None and str(params[key]) != ""
    )
    return hashlib.sha256((canonical + api_secret).encode("utf-8")).hexdigest()


def _cleanup_cloudinary_asset(
    client: httpx.Client, cloud_name: str, api_key: str, api_secret: str, public_id: str
) -> str:
    timestamp = str(int(time.time()))
    params = {
        "invalidate": "true",
        "public_id": public_id,
        "timestamp": timestamp,
        "type": "authenticated",
    }
    fields = {
        **params,
        "api_key": api_key,
        "signature": _cloudinary_signature(params, api_secret),
    }
    url = f"https://api.cloudinary.com/v1_1/{quote(cloud_name, safe='')}/image/destroy"
    response = client.post(url, data=fields)
    if response.status_code >= 300:
        raise RuntimeError(f"Cloudinary cleanup failed (HTTP {response.status_code}).")
    result = str((response.json() or {}).get("result") or "")
    if result not in {"ok", "not found"}:
        raise RuntimeError("Cloudinary cleanup did not confirm object removal.")
    return result


def run_acceptance(base_url: str, token: str, cloud_name: str, api_key: str, api_secret: str) -> dict:
    _assert_staging_base_url(base_url)
    payload = _png_1x1()
    digest = hashlib.sha256(payload).hexdigest()
    filename = f"doka-cloudinary-acceptance-{uuid.uuid4().hex}.png"
    public_id = ""
    cleanup = "not_needed"
    status = "failed"
    error_code = ""
    worker = httpx.Client(base_url=base_url.rstrip("/"), timeout=45.0, follow_redirects=False)
    cloud = httpx.Client(timeout=45.0, follow_redirects=False)
    try:
        session_response = worker.post(
            "/api/storage/upload-session",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            json={
                "filename": filename,
                "content_type": "image/png",
                "size_bytes": len(payload),
                "sha256": digest,
                "artifact_type": "thumbnail",
            },
        )
        if session_response.status_code != 200:
            raise RuntimeError(f"Cloudinary upload-session request failed (HTTP {session_response.status_code}).")
        session = session_response.json()
        if session.get("provider") != "cloudinary":
            raise RuntimeError("Staging Worker did not select Cloudinary for a derivative upload.")
        upload = session.get("upload") or {}
        fields = upload.get("fields") or {}
        upload_url = str(upload.get("url") or "")
        parsed_upload = urlparse(upload_url)
        if (
            parsed_upload.scheme != "https"
            or parsed_upload.hostname != "api.cloudinary.com"
            or not parsed_upload.path.endswith("/image/upload")
            or quote(cloud_name, safe="") not in parsed_upload.path
        ):
            raise RuntimeError("Cloudinary upload-session URL is not the expected HTTPS endpoint.")
        public_id = str(fields.get("public_id") or "")
        if (
            fields.get("type") != "authenticated"
            or not fields.get("signature")
            or not public_id.startswith("users/")
            or "/derivatives/thumbnail/" not in public_id
        ):
            raise RuntimeError("Cloudinary session is not owner-scoped authenticated delivery.")

        upload_response = cloud.post(
            upload_url,
            data=fields,
            files={"file": (filename, payload, "image/png")},
        )
        if upload_response.status_code >= 300:
            raise RuntimeError(f"Cloudinary direct upload failed (HTTP {upload_response.status_code}).")
        remote = upload_response.json()
        provider_result = {
            "public_id": remote.get("public_id"),
            "type": remote.get("type"),
            "resource_type": remote.get("resource_type"),
            "bytes": remote.get("bytes"),
            "context": remote.get("context"),
        }
        if provider_result["public_id"] != public_id or provider_result["type"] != "authenticated":
            raise RuntimeError("Cloudinary upload response did not preserve the signed private identity.")

        complete_response = worker.post(
            "/api/storage/upload-complete",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            json={
                "session_id": session["session_id"],
                "size_bytes": len(payload),
                "sha256": digest,
                "provider_result": provider_result,
            },
        )
        if complete_response.status_code >= 300:
            raise RuntimeError(f"Worker did not verify the Cloudinary derivative (HTTP {complete_response.status_code}).")
        stored = (complete_response.json() or {}).get("stored") or {}
        if (
            stored.get("provider") != "cloudinary"
            or int(stored.get("size_bytes") or 0) != len(payload)
            or str(stored.get("sha256") or "").lower() != digest
            or stored.get("content_type") != "image/png"
        ):
            raise RuntimeError("Worker completion evidence did not match the uploaded derivative.")
        status = "passed"
    except Exception as exc:
        # Error class only: never serialize URLs, provider response bodies or credentials.
        error_code = type(exc).__name__
    finally:
        if public_id:
            try:
                cleanup = _cleanup_cloudinary_asset(cloud, cloud_name, api_key, api_secret, public_id)
            except Exception:
                cleanup = "failed"
                if status == "passed":
                    status = "failed"
                    error_code = "CleanupFailed"
        worker.close()
        cloud.close()
    return {
        "status": status,
        "provider": "cloudinary",
        "artifact_type": "thumbnail",
        "size_bytes": len(payload),
        "sha256": digest,
        "authenticated_delivery": True,
        "remote_byte_integrity_verified_by_worker": status == "passed",
        "cleanup": cleanup,
        "error_code": error_code or None,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a staging-only Cloudinary derivative acceptance test.")
    parser.add_argument("--base-url", default=os.getenv("DOKA_CLOUD_BASE_URL", ""))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    _assert_staging_base_url(args.base_url)
    token = _require("DOKA_CLOUD_USER_TOKEN")
    cloud_name = _require("CLOUDINARY_STAGING_CLOUD_NAME")
    api_key = _require("CLOUDINARY_STAGING_API_KEY")
    api_secret = _require("CLOUDINARY_STAGING_API_SECRET")
    evidence = run_acceptance(args.base_url, token, cloud_name, api_key, api_secret)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if evidence["status"] != "passed" or evidence["cleanup"] not in {"ok", "not found"}:
        raise SystemExit("Cloudinary staging acceptance failed; inspect the redacted evidence artifact.")
    print("Cloudinary staging derivative upload, remote integrity verification and cleanup passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
