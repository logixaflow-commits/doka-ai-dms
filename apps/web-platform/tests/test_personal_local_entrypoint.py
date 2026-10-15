"""The Personal Local API must not mount optional cloud infrastructure routes."""

from app.main import app


def test_personal_local_api_exposes_local_routes_without_cloud_routes():
    paths = app.openapi()["paths"]

    assert "get" in paths["/health"]
    assert "get" in paths["/api/config"]
    assert any(path.startswith("/api/auth") for path in paths)
    assert any(path.startswith("/api/workspace") for path in paths)
    assert not any(path.startswith("/api/storage") for path in paths)
    assert not any(path.startswith("/api/documents") for path in paths)
