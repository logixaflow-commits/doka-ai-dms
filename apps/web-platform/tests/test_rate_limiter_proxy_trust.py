from __future__ import annotations

import sys
from pathlib import Path

from starlette.requests import Request

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.rate_limiter import RateLimiter  # noqa: E402


def request_with(headers: dict[str, str], client_ip: str = "127.0.0.1") -> Request:
    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": (client_ip, 12345),
        "server": ("testserver", 80),
    })


def test_forwarded_headers_are_ignored_by_default(monkeypatch):
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    limiter = RateLimiter()

    request = request_with({
        "X-Forwarded-For": "198.51.100.7",
        "X-Real-IP": "203.0.113.9",
        "CF-Connecting-IP": "192.0.2.1",
    })

    assert limiter.get_client_ip(request) == "127.0.0.1"


def test_proxy_headers_are_used_only_when_explicitly_trusted(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    limiter = RateLimiter()

    request = request_with({"CF-Connecting-IP": "2001:db8::1"})
    assert limiter.get_client_ip(request) == "2001:db8::1"


def test_invalid_proxy_addresses_fall_back_to_direct_client(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    limiter = RateLimiter()

    request = request_with({
        "CF-Connecting-IP": "not-an-ip",
        "X-Real-IP": "also-not-an-ip",
        "X-Forwarded-For": "spoofed-value",
    })

    assert limiter.get_client_ip(request) == "127.0.0.1"
