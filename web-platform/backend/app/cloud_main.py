"""Stateless cloud API entry point for Doka.

This app deliberately exposes only Supabase-backed cloud document/storage routes.
The Personal Local workspace, filesystem import, backup, and OCR routes are not
mounted here because a free cloud instance has no durable office filesystem.
"""
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cloud_documents, cloud_storage
from app.core.config import settings
from app.core.rate_limiter import rate_limit_middleware


def parse_cloud_cors_origins(raw_origins: str, environment: str) -> list[str]:
    """Require explicit origins for credentialed cloud APIs; wildcard is never safe."""
    values = [item.strip() for item in raw_origins.split(",") if item.strip()]
    if environment.lower() == "production" and not values:
        raise ValueError("Production CORS_ORIGINS must contain explicit trusted origins.")

    origins: list[str] = []
    for value in values:
        if value == "*":
            raise ValueError("CORS_ORIGINS cannot contain '*' when credentials are enabled.")
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError as exc:
            raise ValueError(f"Invalid CORS origin: {value}") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"CORS entry must be an origin only: {value}")
        canonical = f"{parsed.scheme}://{parsed.netloc}"
        if canonical not in origins:
            origins.append(canonical)
    return origins


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doka Cloud API",
        description="Authenticated Supabase-backed document and object-storage API.",
        version="1.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
    )

    origins = parse_cloud_cors_origins(
        os.getenv("CORS_ORIGINS", ""),
        settings.ENVIRONMENT,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    app.middleware("http")(rate_limit_middleware)
    app.include_router(cloud_documents.router)
    app.include_router(cloud_storage.router)

    @app.get("/health", tags=["System"])
    async def health():
        return {
            "status": "healthy",
            "edition": "cloud-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/config", tags=["System"])
    async def public_config():
        return {
            "edition": "cloud-api",
            "auth": "supabase",
            "storage": os.getenv("DOKA_STORAGE_PROVIDER", "disabled"),
            "local_workspace_available": False,
        }

    return app


app = create_app()
