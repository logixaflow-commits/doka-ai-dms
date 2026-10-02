"""Stateless cloud API entry point for Doka.

This app deliberately exposes only Supabase-backed cloud document/storage routes.
The Personal Local workspace, filesystem import, backup, and OCR routes are not
mounted here because a free cloud instance has no durable office filesystem.
"""
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cloud_documents, cloud_storage
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doka Cloud API",
        description="Authenticated Supabase-backed document and object-storage API.",
        version="1.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
    )

    origins = [
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "").split(",")
        if item.strip()
    ]
    if settings.ENVIRONMENT.lower() == "production" and ("*" in origins or not origins):
        raise RuntimeError("Production CORS_ORIGINS must contain explicit trusted origins.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

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
