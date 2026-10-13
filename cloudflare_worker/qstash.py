"""Fail-closed QStash webhook signature verification.

The verifier is intentionally dependency-free so it can be used by the
Cloudflare Python Worker without adding a runtime SDK. It verifies the raw
request body before any queue event is processed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any


class QStashSignatureError(ValueError):
    """Raised when an incoming QStash signature is invalid."""


def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise QStashSignatureError("invalid signature")
    # JWT segments use unpadded base64url only. Python's decoder is otherwise
    # permissive about invalid characters, which can create ambiguous tokens.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise QStashSignatureError("invalid signature")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != value:
            raise QStashSignatureError("invalid signature")
        return decoded
    except (ValueError, TypeError) as exc:
        raise QStashSignatureError("invalid signature") from exc


def _decode_json_segment(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_b64url_decode(value).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QStashSignatureError("invalid signature") from exc
    if not isinstance(decoded, dict):
        raise QStashSignatureError("invalid signature")
    return decoded


def _signature_for(signing_key: str, signing_input: bytes) -> bytes:
    return hmac.new(
        signing_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()


def verify_qstash_signature(
    *,
    body: bytes | str,
    signature: str,
    expected_url: str,
    current_signing_key: str,
    next_signing_key: str,
    now: int | float | None = None,
) -> dict[str, Any]:
    """Verify a QStash JWT and return its validated claims.

    Both current and next signing keys are accepted to permit key rotation
    without downtime. The caller must pass the raw request body unchanged.
    """
    if not isinstance(body, (bytes, str)) or not isinstance(expected_url, str) or not expected_url:
        raise QStashSignatureError("invalid request")
    if not isinstance(current_signing_key, str) or not current_signing_key:
        raise QStashSignatureError("signing key is not configured")
    if not isinstance(next_signing_key, str) or not next_signing_key:
        raise QStashSignatureError("signing key is not configured")

    parts = signature.split(".") if isinstance(signature, str) else []
    if len(parts) != 3 or any(not part for part in parts):
        raise QStashSignatureError("invalid signature")
    header_segment, payload_segment, signature_segment = parts
    header = _decode_json_segment(header_segment)
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise QStashSignatureError("invalid signature")

    provided_signature = _b64url_decode(signature_segment)
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    valid = any(
        hmac.compare_digest(provided_signature, _signature_for(key, signing_input))
        for key in (current_signing_key, next_signing_key)
    )
    if not valid:
        raise QStashSignatureError("invalid signature")

    claims = _decode_json_segment(payload_segment)
    if claims.get("iss") != "Upstash":
        raise QStashSignatureError("invalid claims")
    if claims.get("sub") != expected_url:
        raise QStashSignatureError("invalid claims")

    try:
        exp_value = claims["exp"]
        nbf_value = claims["nbf"]
        body_claim = claims["body"]
        # Reject booleans, floats, and numeric strings rather than coercing
        # attacker-controlled claim types into timestamps.
        if type(exp_value) is not int or type(nbf_value) is not int:
            raise TypeError("timestamps must be integers")
        exp = exp_value
        nbf = nbf_value
    except (KeyError, TypeError, ValueError) as exc:
        raise QStashSignatureError("invalid claims") from exc
    if not isinstance(body_claim, str) or not body_claim:
        raise QStashSignatureError("invalid claims")

    current_time = int(time.time() if now is None else now)
    if current_time >= exp or current_time < nbf:
        raise QStashSignatureError("invalid claims")

    raw_body = body.encode("utf-8") if isinstance(body, str) else body
    expected_body = hashlib.sha256(raw_body).digest()
    try:
        claimed_body = _b64url_decode(body_claim)
    except QStashSignatureError as exc:
        raise QStashSignatureError("invalid claims") from exc
    if not hmac.compare_digest(claimed_body, expected_body):
        raise QStashSignatureError("invalid claims")

    return claims
