"""
Office DMS - Global Error Handler Middleware
Catches and formats all exceptions. Never exposes stack traces in production.
"""

import traceback
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
            # Log full error with stack trace
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}: {exc}"
            )
            logger.debug(traceback.format_exc())

            # Return safe error response
            if settings.DEBUG:
                detail = str(exc)
                stack = traceback.format_exc()
            else:
                detail = "An internal server error occurred. Please try again later."
                stack = None

            from datetime import datetime

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": detail,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "stack_trace": stack if settings.DEBUG else None,
                },
            )
