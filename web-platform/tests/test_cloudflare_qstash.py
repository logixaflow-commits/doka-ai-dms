"""Tests for the dependency-free QStash signature boundary."""
import base64
import hashlib
import hmac
import json

import pytest

from cloudflare_worker.qstash import QStashSignatureError, verify_qstash_signature


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def make_token(body: bytes, key: str, url: str, *, exp=1100, nbf=900):
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64(
        json.dumps(
            {
                "iss": "Upstash",
                "sub": url,
                "exp": exp,
                "nbf": nbf,
                "iat": 900,
                "jti": "test-jti",
                "body": b64(hashlib.sha256(body).digest()),
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = b64(hmac.new(key.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def test_current_signing_key_is_accepted():
    body = b'{"id":"evt-1"}'
    token = make_token(body, "current-key", "https://example.test/qstash")
    claims = verify_qstash_signature(
        body=body,
        signature=token,
        expected_url="https://example.test/qstash",
        current_signing_key="current-key",
        next_signing_key="next-key",
        now=1000,
    )
    assert claims["iss"] == "Upstash"


def test_next_signing_key_is_accepted_for_rotation():
    body = b'{"id":"evt-2"}'
    token = make_token(body, "next-key", "https://example.test/qstash")
    verify_qstash_signature(
        body=body,
        signature=token,
        expected_url="https://example.test/qstash",
        current_signing_key="current-key",
        next_signing_key="next-key",
        now=1000,
    )


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ("signature", "invalid signature"),
        ("body", "invalid claims"),
        ("url", "invalid claims"),
        ("issuer", "invalid claims"),
        ("expired", "invalid claims"),
        ("early", "invalid claims"),
    ],
)
def test_tampered_or_invalid_requests_are_rejected(change, match):
    body = b'{"id":"evt-3"}'
    url = "https://example.test/qstash"
    token = make_token(body, "current-key", url)

    if change == "signature":
        token = token[:-1] + ("A" if token[-1] != "A" else "B")
        kwargs = {}
    elif change == "body":
        kwargs = {"body": b'{"id":"different"}'}
    elif change == "url":
        kwargs = {"expected_url": "https://example.test/other"}
    elif change == "issuer":
        parts = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["iss"] = "attacker"
        payload_segment = b64(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{parts[0]}.{payload_segment}".encode()
        forged = b64(hmac.new(b"current-key", signing_input, hashlib.sha256).digest())
        token = f"{parts[0]}.{payload_segment}.{forged}"
        kwargs = {}
    elif change == "expired":
        token = make_token(body, "current-key", url, exp=999, nbf=900)
        kwargs = {}
    else:
        token = make_token(body, "current-key", url, exp=1100, nbf=1001)
        kwargs = {}

    with pytest.raises(QStashSignatureError, match=match):
        verify_qstash_signature(
            body=kwargs.pop("body", body),
            signature=token,
            expected_url=kwargs.pop("expected_url", url),
            current_signing_key="current-key",
            next_signing_key="next-key",
            now=1000,
        )


def test_malformed_jwt_and_wrong_algorithm_are_rejected():
    with pytest.raises(QStashSignatureError, match="invalid signature"):
        verify_qstash_signature(
            body=b"",
            signature="not-a-jwt",
            expected_url="https://example.test/qstash",
            current_signing_key="current-key",
            next_signing_key="next-key",
            now=1000,
        )
