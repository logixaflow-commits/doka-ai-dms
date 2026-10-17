"""Cloudinary derivative provider with a server-side credit guard."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from storage_contracts_compat import (
    CLOUDINARY_DERIVATIVE_MAX_BYTES,
    SignedUpload,
    StorageObjectRef,
    StoredObjectResult,
    UploadMetadata,
    UploadSession,
    owner_object_key,
)


@dataclass(frozen=True)
class CloudinaryConfig:
    cloud_name: str
    api_key: str
    api_secret: str
    low_credit_threshold: float = 5.0


@dataclass(frozen=True)
class CloudinaryCreditDecision:
    allowed: bool
    remaining_credits: float | None
    warning: str | None = None


class CloudinaryCreditGuard:
    def __init__(self, config: CloudinaryConfig, fetcher):
        self.config = config
        self.fetcher = fetcher

    async def check(self) -> CloudinaryCreditDecision:
        if not all((self.config.cloud_name, self.config.api_key, self.config.api_secret)):
            return CloudinaryCreditDecision(False, None, "cloudinary_not_configured")
        credentials = f"{self.config.api_key}:{self.config.api_secret}"
        import base64
        basic = base64.b64encode(credentials.encode()).decode()
        status, payload = await self.fetcher(
            f"https://api.cloudinary.com/v1_1/{quote(self.config.cloud_name, safe='')}/usage",
            headers={"Authorization": f"Basic {basic}"},
        )
        if status >= 300 or not isinstance(payload, dict):
            return CloudinaryCreditDecision(False, None, "cloudinary_usage_unknown")
        credits = payload.get("credits") or {}
        used = credits.get("usage", credits.get("used"))
        limit = credits.get("limit", credits.get("quota"))
        if used is None or limit is None:
            plan = payload.get("plan") or {}
            used = plan.get("credits_usage", used)
            limit = plan.get("credits_limit", limit)
        try:
            remaining = float(limit) - float(used)
        except (TypeError, ValueError):
            return CloudinaryCreditDecision(False, None, "cloudinary_usage_unknown")
        if remaining <= self.config.low_credit_threshold:
            return CloudinaryCreditDecision(False, remaining, "cloudinary_credit_fallback")
        return CloudinaryCreditDecision(True, remaining)


class CloudinaryDerivativeProvider:
    name = "cloudinary"

    def __init__(self, config: CloudinaryConfig, fetcher):
        if not all((config.cloud_name, config.api_key, config.api_secret)):
            raise ValueError("Cloudinary configuration is incomplete")
        self.config = config
        self.fetcher = fetcher
        self.guard = CloudinaryCreditGuard(config, fetcher)

    # codeql[py/weak-sensitive-data-hashing]: Cloudinary's documented API signature is a SHA-256 digest of canonical parameters plus the API secret; this is protocol authentication, not password storage.
    @staticmethod
    def _signature(params: dict[str, str], secret: str) -> str:
        payload = "&".join(f"{key}={params[key]}" for key in sorted(params) if params[key] is not None)
        return hashlib.sha256((payload + secret).encode()).hexdigest()

    @staticmethod
    def _public_id(object_key: str) -> str:
        filename = object_key.rsplit("/", 1)[-1]
        if "." not in filename:
            raise ValueError("Cloudinary derivative keys require a file extension")
        return object_key.rsplit(".", 1)[0]

    @staticmethod
    def _context_fields(value) -> dict[str, str]:
        if isinstance(value, dict):
            custom = value.get("custom") if isinstance(value.get("custom"), dict) else value
            return {str(key): str(item) for key, item in custom.items() if item is not None}
        if isinstance(value, str):
            result: dict[str, str] = {}
            for field in value.split("|"):
                if "=" in field:
                    key, item = field.split("=", 1)
                    result[key] = item
            return result
        return {}

    def _signed_params(self, params: dict[str, str]) -> dict[str, str]:
        return {
            **params,
            "api_key": self.config.api_key,
            "signature": self._signature(params, self.config.api_secret),
        }

    async def create_upload_session(self, metadata: UploadMetadata) -> UploadSession:
        metadata.validate()
        if metadata.artifact_type.value not in {"preview", "thumbnail", "cover"}:
            raise ValueError("Cloudinary is reserved for image derivatives")
        if metadata.size_bytes >= CLOUDINARY_DERIVATIVE_MAX_BYTES:
            raise ValueError("Cloudinary derivative artifacts must be smaller than 10 MB")
        decision = await self.guard.check()
        if not decision.allowed:
            warning = decision.warning or "cloudinary_credit_fallback"
            raise RuntimeError(warning)
        key = owner_object_key(metadata)
        timestamp = int(time.time())
        public_id = self._public_id(key)
        context = (
            f"sha256={metadata.sha256.lower()}|size_bytes={metadata.size_bytes}"
            f"|content_type={metadata.content_type}"
        )
        params = {
            "context": context,
            "public_id": public_id,
            "timestamp": str(timestamp),
            "type": "authenticated",
        }
        signature = self._signature(params, self.config.api_secret)
        upload_url = f"https://api.cloudinary.com/v1_1/{quote(self.config.cloud_name, safe='')}/image/upload"
        upload = SignedUpload(
            method="POST",
            url=upload_url,
            fields={
                "api_key": self.config.api_key,
                "timestamp": str(timestamp),
                "signature": signature,
                "public_id": public_id,
                "context": context,
                "type": "authenticated",
            },
        )
        return UploadSession(
            provider=self.name,
            object_ref=StorageObjectRef(self.name, key, metadata.owner_id),
            expires_at=timestamp + 3600,
            upload=upload,
            session_id=f"cloudinary:{metadata.owner_id}:{metadata.sha256.lower()}",
        )

    async def complete_upload(self, session: UploadSession, client_result: dict) -> StoredObjectResult:
        expected_public_id = session.upload.fields["public_id"]
        if str(client_result.get("public_id") or "") != expected_public_id:
            raise ValueError("Cloudinary completion public ID mismatch")
        if str(client_result.get("type") or "") != "authenticated":
            raise ValueError("Cloudinary derivative must use authenticated delivery")
        if str(client_result.get("resource_type") or "") != "image":
            raise ValueError("Cloudinary derivative resource type mismatch")

        expected_context = self._context_fields(session.upload.fields["context"])
        received_context = self._context_fields(client_result.get("context"))
        if any(received_context.get(key) != value for key, value in expected_context.items()):
            raise ValueError("Cloudinary completion context mismatch")
        digest = expected_context.get("sha256", "").lower()
        content_type = expected_context.get("content_type", "")
        try:
            expected_size = int(expected_context.get("size_bytes", "0"))
            reported_size = int(client_result.get("bytes") or 0)
        except (TypeError, ValueError):
            raise ValueError("Cloudinary completion has invalid size metadata") from None
        if len(digest) != 64 or not content_type or expected_size < 1 or reported_size != expected_size:
            raise ValueError("Cloudinary completion metadata does not match the signed upload session")

        # The upload response's context is client-visible metadata, not proof of the
        # stored bytes. Re-download the authenticated asset through a short-lived
        # API URL and verify the actual byte count and SHA-256 before accepting it.
        signed_url = await self.get_signed_download(session.object_ref, expires_seconds=300)
        status, verification = await self.fetcher(
            signed_url,
            return_sha256=True,
            max_bytes=CLOUDINARY_DERIVATIVE_MAX_BYTES,
        )
        if status >= 300 or not isinstance(verification, dict):
            raise RuntimeError("Cloudinary derivative integrity verification failed")
        if (
            str(verification.get("sha256") or "").lower() != digest
            or int(verification.get("size_bytes") or 0) != expected_size
        ):
            raise ValueError("Cloudinary derivative content integrity check failed")
        return StoredObjectResult(session.object_ref, expected_size, digest, content_type)

    async def get_signed_download(self, object_ref: StorageObjectRef, expires_seconds: int = 300) -> str:
        if not 1 <= expires_seconds <= 604800:
            raise ValueError("Signed URL expiry must be between 1 second and 7 days.")
        prefix = f"users/{object_ref.owner_id}/derivatives/"
        if object_ref.provider != self.name or not object_ref.object_key.startswith(prefix):
            raise ValueError("Cloudinary derivative key is not scoped to the authenticated owner")
        filename = object_ref.object_key.rsplit("/", 1)[-1]
        if "." not in filename:
            raise ValueError("Cloudinary derivative keys require a file extension")
        public_id = self._public_id(object_ref.object_key)
        file_format = filename.rsplit(".", 1)[-1].lower()
        timestamp = int(time.time())
        params = {
            "expires_at": str(timestamp + expires_seconds),
            "format": file_format,
            "public_id": public_id,
            "timestamp": str(timestamp),
            "type": "authenticated",
        }
        signed = self._signed_params(params)
        url = f"https://api.cloudinary.com/v1_1/{quote(self.config.cloud_name, safe='')}/image/download"
        from urllib.parse import urlencode
        return f"{url}?{urlencode(signed)}"

    async def delete(self, object_ref: StorageObjectRef) -> None:
        raise NotImplementedError("Cloudinary deletion is handled by the derivative lifecycle adapter")

    async def head(self, object_ref: StorageObjectRef) -> StoredObjectResult:
        raise NotImplementedError("Cloudinary head lookup is handled by the derivative lifecycle adapter")

    async def initiateMultipartUpload(self, metadata: UploadMetadata):
        raise NotImplementedError

    async def uploadPart(self, upload, part_number: int, checksum: str, signed_request):
        raise NotImplementedError

    async def completeMultipartUpload(self, upload, parts):
        raise NotImplementedError

    async def abortMultipartUpload(self, upload):
        return None
