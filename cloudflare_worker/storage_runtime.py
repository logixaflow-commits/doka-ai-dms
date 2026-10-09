"""Runtime construction for Cloudflare direct-storage providers."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from urllib.parse import quote, urlsplit
from workers import env as worker_env

from shared.storage_contracts import StorageObjectRef, UploadMetadata
from storage_b2 import B2StorageConfig, B2StorageProvider
from storage_cloudinary import CloudinaryConfig, CloudinaryDerivativeProvider
from storage_router import CloudStorageRouter
from storage_supabase import SupabaseDirectStorageProvider, SupabaseStorageConfig
from storage_google_drive import GoogleDriveConfig, GoogleDriveExportProvider


def _b2_region_from_endpoint(endpoint: str, configured_region: str = "") -> str:
    """Prefer an explicit region; infer it from standard Backblaze S3 endpoints otherwise."""
    if configured_region.strip():
        return configured_region.strip()
    host = (urlsplit(endpoint.strip()).hostname or "").lower()
    match = re.fullmatch(r"s3\.([a-z0-9-]+)\.backblazeb2\.com", host)
    if match:
        return match.group(1)
    return "us-east-005"


def build_storage_router(request, token: str, fetcher_factory):
    mode = (request.scope.get("env") and _read_env(request, "STORAGE_PROVIDER", "hybrid")) or _read_env(request, "STORAGE_PROVIDER", "hybrid")
    supabase = SupabaseDirectStorageProvider(
        SupabaseStorageConfig(
            base_url=_read_env(request, "SUPABASE_URL").rstrip("/"),
            bucket=_read_env(request, "SUPABASE_STORAGE_BUCKET", "doka-documents"),
        ),
        fetcher_factory(request),
        auth_headers={
            "apikey": _read_env(request, "SUPABASE_PUBLISHABLE_KEY"),
            "Authorization": f"Bearer {token}",
        },
    )

    b2 = None
    if all(_read_env(request, key) for key in ("B2_ENDPOINT", "B2_BUCKET", "B2_KEY_ID", "B2_APPLICATION_KEY")):
        b2 = B2StorageProvider(
            B2StorageConfig(
                endpoint=_read_env(request, "B2_ENDPOINT"),
                bucket=_read_env(request, "B2_BUCKET"),
                key_id=_read_env(request, "B2_KEY_ID"),
                application_key=_read_env(request, "B2_APPLICATION_KEY"),
                region=_b2_region_from_endpoint(_read_env(request, "B2_ENDPOINT"), _read_env(request, "B2_REGION")),
            ),
            fetcher_factory(request),
        )

    cloudinary = None
    if all(_read_env(request, key) for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")):
        cloudinary = CloudinaryDerivativeProvider(
            CloudinaryConfig(
                cloud_name=_read_env(request, "CLOUDINARY_CLOUD_NAME"),
                api_key=_read_env(request, "CLOUDINARY_API_KEY"),
                api_secret=_read_env(request, "CLOUDINARY_API_SECRET"),
                low_credit_threshold=float(_read_env(request, "CLOUDINARY_LOW_CREDIT_THRESHOLD", "5")),
            ),
            fetcher_factory(request),
        )

    return CloudStorageRouter(
        supabase=supabase,
        b2=b2,
        cloudinary=cloudinary,
        mode=mode,
    )


def _read_env(request, name: str, default: str = "") -> str:
    bindings = request.scope.get("env")
    if bindings is not None:
        try:
            value = getattr(bindings, name)
        except Exception:
            try:
                value = bindings[name]
            except Exception:
                value = None
        if value is not None:
            return str(value)
    if worker_env is not None:
        try:
            value = getattr(worker_env, name)
        except Exception:
            try:
                value = worker_env[name]
            except Exception:
                value = None
        if value is not None:
            return str(value)
    return default


def sign_session(secret: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    encoded = _b64url(raw)
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def verify_session(secret: str, token: str) -> dict:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        raw = _b64url_decode(encoded)
        payload = json.loads(raw.decode())
        if int(payload.get("expires_at", 0)) < int(time.time()):
            raise ValueError
        return payload
    except Exception as exc:
        raise ValueError("Invalid or expired upload session") from exc


def _b64url(value: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64url_decode(value: str) -> bytes:
    import base64
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def build_google_drive_provider(request, fetcher_factory):
    required = ("GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN")
    if not all(_read_env(request, key).strip() for key in required):
        return None
    return GoogleDriveExportProvider(
        GoogleDriveConfig(
            client_id=_read_env(request, "GOOGLE_DRIVE_CLIENT_ID"),
            client_secret=_read_env(request, "GOOGLE_DRIVE_CLIENT_SECRET"),
            refresh_token=_read_env(request, "GOOGLE_DRIVE_REFRESH_TOKEN"),
            folder_id=_read_env(request, "GOOGLE_DRIVE_FOLDER_ID"),
        ),
        fetcher_factory(request),
    )
