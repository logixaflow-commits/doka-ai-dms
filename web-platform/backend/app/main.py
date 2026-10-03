"""FastAPI entry point for the Personal Local Edition.

Legacy enterprise routes remain in the repository but are intentionally not loaded
by this runtime until their deferred ORM/model stack is restored.
"""
import os
import time
from datetime import datetime
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import cloud_documents, cloud_storage, local_auth, workspace, workspace_files
from app.core.config import settings
from app.core.logging import get_logger
from app.core.observability import init_observability

logger = get_logger(__name__)


def parse_cors_origins(raw_origins: str) -> list[str]:
    """Parse an explicit allowlist of browser origins; never allow wildcard credentials."""
    origins = [value.strip() for value in raw_origins.split(",") if value.strip()]
    if not origins:
        raise ValueError("CORS_ORIGINS must contain at least one explicit origin.")

    normalized: list[str] = []
    for origin in origins:
        if origin == "*":
            raise ValueError("CORS_ORIGINS cannot contain '*' when authenticated APIs use credentials.")
        try:
            parsed = urlsplit(origin)
            # Accessing .port also validates malformed/out-of-range port values.
            _ = parsed.port
        except ValueError as exc:
            raise ValueError(f"Invalid CORS origin: {origin}") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"CORS entry must be an origin only (scheme + host + optional port): {origin}")
        canonical = f"{parsed.scheme}://{parsed.netloc}"
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doka — Personal Local Edition",
        description="Safe local document workspace with read-only source protection.",
        version="2.0.0-personal-local",
        docs_url="/api/docs" if settings.DEBUG else None,
    )
    cors_origins = parse_cors_origins(os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8000",
    ))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        start = time.time()
        request_id = request.headers.get("X-Request-ID", f"req_{time.time():.6f}")
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"Unhandled request error: {exc}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error", "request_id": request_id},
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{time.time() - start:.3f}s"
        return response

    app.include_router(local_auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(workspace.router)
    app.include_router(workspace_files.router)
    app.include_router(cloud_storage.router)
    app.include_router(cloud_documents.router)

    @app.get("/health", tags=["System"])
    async def health():
        return {
            "status": "healthy",
            "edition": "personal-local",
            "timestamp": datetime.utcnow().isoformat(),
            "ai_enabled": bool(settings.AI_ENABLED),
            "ai_external_processing_consent": bool(settings.AI_EXTERNAL_PROCESSING_CONSENT),
            "source_read_only": bool(settings.ORIGINAL_READ_ONLY and not settings.ALLOW_SOURCE_WRITE),
        }

    @app.get("/api/config", tags=["System"])
    async def public_config():
        return {
            "edition": "personal-local",
            "ai_enabled": bool(settings.AI_ENABLED),
            "source_read_only": bool(settings.ORIGINAL_READ_ONLY and not settings.ALLOW_SOURCE_WRITE),
            "workspace_root_configured": bool(settings.WORKING_ROOT),
        }

    @app.on_event("startup")
    async def startup_event():
        logger.info("Doka Personal Local Edition starting")
        init_observability()

    return app


app = create_app()