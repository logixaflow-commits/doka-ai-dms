"""
Office DMS - Global Error Handler Middleware
Catches and formats all exceptions. Never exposes stack traces in production.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware that catches unhandled exceptions and returns safe responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except Exception as exc:
            # Keep the full exception and stack trace server-side only.
            logger.exception(
                "Unhandled exception in %s %s",
                request.method,
                request.url.path,
            )

            # Never expose exception messages or stack traces to API clients.
            # Debug details belong in server logs only.
            from datetime import datetime

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An internal server error occurred. Please try again later.",
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            )
