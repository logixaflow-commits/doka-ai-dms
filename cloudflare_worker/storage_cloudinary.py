"""Cloudinary derivative provider with a server-side credit guard."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from urllib.parse import quote

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

    @staticmethod
    def _signature(params: dict[str, str], secret: str) -> str:
        payload = "&".join(f"{key}={params[key]}" for key in sorted(params) if params[key] is not None)
        return hashlib.sha1((payload + secret).encode()).hexdigest()

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
        public_id = key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        params = {
            "context": f"sha256={metadata.sha256.lower()}",
            "public_id": public_id,
            "timestamp": str(timestamp),
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
                "context": params["context"],
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
        public_id = session.upload.fields["public_id"]
        context = str(client_result.get("context") or "")
        expected = session.object_ref.object_key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if public_id != expected:
            raise ValueError("Cloudinary completion public ID mismatch")
        digest = context.split("sha256=", 1)[1].split("|", 1)[0].lower() if "sha256=" in context else ""
        if len(digest) != 64:
            raise ValueError("Cloudinary completion is missing SHA-256 metadata")
        return StoredObjectResult(session.object_ref, int(client_result.get("bytes") or 0), digest, str(client_result.get("resource_type") or "image"))

    async def get_signed_download(self, object_ref: StorageObjectRef, expires_seconds: int = 300) -> str:
        # Cloudinary delivery is identified by the opaque public ID; the API key is not included.
        public_id = object_ref.object_key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return f"https://res.cloudinary.com/{quote(self.config.cloud_name, safe='')}/image/upload/{quote(public_id, safe='/')}"

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
