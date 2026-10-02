"""The cloud API must never mount local filesystem/workspace endpoints."""
from app.cloud_main import app


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
