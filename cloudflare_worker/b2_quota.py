"""Quota policy for B2-backed Doka source objects."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class B2QuotaDecision:
    quota_bytes: int
    used_bytes: int
    requested_bytes: int
    usage_ratio: float
    blocked: bool
    warning: str | None = None

    @property
    def projected_bytes(self) -> int:
        return self.used_bytes + self.requested_bytes


def evaluate_b2_quota(
    *,
    used_bytes: int,
    requested_bytes: int,
    quota_bytes: int,
    alert_ratio: float = 0.80,
    block_ratio: float = 0.95,
) -> B2QuotaDecision:
    if quota_bytes <= 0:
        raise ValueError("B2_QUOTA_BYTES must be greater than zero")
    if used_bytes < 0 or requested_bytes <= 0:
        raise ValueError("B2 quota inputs are invalid")
    ratio = (used_bytes + requested_bytes) / quota_bytes
    if ratio >= block_ratio:
        return B2QuotaDecision(quota_bytes, used_bytes, requested_bytes, ratio, True, "b2_quota_block")
    if ratio >= alert_ratio:
        return B2QuotaDecision(quota_bytes, used_bytes, requested_bytes, ratio, False, "b2_quota_warning")
    return B2QuotaDecision(quota_bytes, used_bytes, requested_bytes, ratio, False)
