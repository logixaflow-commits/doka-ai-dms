"""Cloudflare Worker storage routing policy.

This layer is intentionally separate from provider implementations so provider
credentials and fallback behavior remain server-side and testable.
"""
from __future__ import annotations

from dataclasses import dataclass

from shared.storage_contracts import (
    CLOUDINARY_DERIVATIVE_MAX_BYTES,
    SUPABASE_SOURCE_MAX_BYTES,
    StorageArtifactType,
    UploadMetadata,
)


@dataclass(frozen=True)
class RoutingDecision:
    provider: str
    warnings: tuple[str, ...] = ()


class CloudStorageRouter:
    def __init__(self, *, supabase, b2=None, cloudinary=None, mock=None, mode: str = "hybrid"):
        self.supabase = supabase
        self.b2 = b2
        self.cloudinary = cloudinary
        self.mock = mock
        self.mode = mode.strip().lower()

    def _validate_mode(self) -> None:
        if self.mode not in {"mock", "hybrid", "supabase"}:
            raise ValueError("STORAGE_PROVIDER must be mock, hybrid, or supabase")

    async def select(self, metadata: UploadMetadata) -> tuple[object, RoutingDecision]:
        metadata.validate()
        self._validate_mode()
        if self.mode == "mock":
            if self.mock is None:
                raise RuntimeError("mock_storage_not_configured")
            return self.mock, RoutingDecision("mock")

        if metadata.artifact_type is not StorageArtifactType.SOURCE:
            if metadata.size_bytes >= CLOUDINARY_DERIVATIVE_MAX_BYTES:
                raise ValueError("Cloudinary derivative artifacts must be smaller than 10 MB")
            if self.mode == "supabase":
                return self.supabase, RoutingDecision("supabase", ("cloudinary_disabled",))
            if self.cloudinary is None:
                return self.supabase, RoutingDecision("supabase", ("cloudinary_not_configured",))
            try:
                # The provider performs the credit guard before returning its session.
                return self.cloudinary, RoutingDecision("cloudinary")
            except RuntimeError as exc:
                warning = str(exc) or "cloudinary_credit_fallback"
                return self.supabase, RoutingDecision("supabase", (warning,))

        if metadata.size_bytes <= SUPABASE_SOURCE_MAX_BYTES:
            return self.supabase, RoutingDecision("supabase")
        if self.b2 is None:
            raise RuntimeError("b2_not_configured")
        return self.b2, RoutingDecision("b2")

    async def create_upload_session(self, metadata: UploadMetadata):
        provider, decision = await self.select(metadata)
        # Provider selection is intentionally followed by provider session creation.
        # Cloudinary credit fallback is handled here so a failed guard never leaks a secret.
        try:
            session = await provider.create_upload_session(metadata)
            return session, decision
        except RuntimeError as exc:
            if decision.provider == "cloudinary":
                warning = str(exc) or "cloudinary_credit_fallback"
                session = await self.supabase.create_upload_session(metadata)
                return session, RoutingDecision("supabase", (warning,))
            raise
