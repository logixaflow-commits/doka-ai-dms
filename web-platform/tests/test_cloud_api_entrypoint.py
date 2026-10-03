"""The cloud API must never mount local filesystem/workspace endpoints."""
from app.cloud_main import app, parse_cloud_cors_origins


def test_cloud_api_exposes_cloud_routes_only():
    # FastAPI lazily expands included routers; OpenAPI materializes the route table.
    paths = app.openapi()["paths"]

    assert "get" in paths["/health"]
    assert "get" in paths["/api/config"]
    assert "get" in paths["/api/documents"]
    assert "post" in paths["/api/documents"]
    assert "get" in paths["/api/documents/{document_id}/download"]
    assert "patch" in paths["/api/documents/{document_id}"]
    assert "post" in paths["/api/storage/objects"]

    assert not any(path.startswith("/api/workspace") for path in paths)
    assert not any(path.startswith("/api/auth") for path in paths)


def test_cloud_cors_requires_explicit_production_origins():
    assert parse_cloud_cors_origins("https://doka.example.com/", "production") == [
        "https://doka.example.com"
    ]


def test_cloud_cors_allows_empty_origins_only_outside_production():
    assert parse_cloud_cors_origins("", "development") == []


import pytest


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "https://example.com/path",
        "https://user:secret@example.com",
        "https://example.com?next=/",
        "ftp://example.com",
        "https://example.com:99999",
    ],
)
def test_cloud_cors_rejects_wildcard_and_non_origin_values(value):
    with pytest.raises(ValueError):
        parse_cloud_cors_origins(value, "production")


def test_cloud_cors_rejects_empty_production_allowlist():
    with pytest.raises(ValueError, match="explicit trusted origins"):
        parse_cloud_cors_origins("", "production")
