"""The cloud API must never mount local filesystem/workspace endpoints."""
from app.cloud_main import app


def test_cloud_api_exposes_cloud_routes_only():
    routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("GET", "/health") in routes
    assert ("GET", "/api/config") in routes
    assert ("GET", "/api/documents") in routes
    assert ("POST", "/api/documents") in routes
    assert ("GET", "/api/documents/{document_id}/download") in routes
    assert ("PATCH", "/api/documents/{document_id}") in routes
    assert ("POST", "/api/storage/objects") in routes

    assert not any(path.startswith("/api/workspace") for _, path in routes)
    assert not any(path.startswith("/api/auth") for _, path in routes)
