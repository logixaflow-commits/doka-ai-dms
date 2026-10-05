"""Runtime construction for Cloudflare direct-storage providers."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import quote

from shared.storage_contracts import StorageObjectRef, UploadMetadata
from cloudflare_worker.storage_b2 import B2StorageConfig, B2StorageProvider
from cloudflare_worker.storage_cloudinary import CloudinaryConfig, CloudinaryDerivativeProvider
from cloudflare_worker.storage_router import CloudStorageRouter
from cloudflare_worker.storage_supabase import SupabaseDirectStorageProvider, SupabaseStorageConfig


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
                region=_read_env(request, "B2_REGION", "us-east-005"),
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
