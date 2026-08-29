"""
Office DMS - Audit Logging Middleware
Automatically logs all API requests to the audit trail.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.security import decode_token
from app.models.database import AuditLog

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs API requests to the audit_logs table."""

    # Actions that should be audited
    AUDIT_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    SKIP_PATHS = {"/health", "/api/docs", "/api/redoc", "/api/openapi.json", "/static/"}

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Skip non-mutating endpoints and health checks
        path = request.url.path
        if request.method not in self.AUDIT_METHODS:
            return await call_next(request)

        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        response = await call_next(request)

        try:
            self._log_request(request, response, time.time() - start_time)
        except Exception as e:
            logger.debug(f"Audit logging skipped: {e}")

        return response

    def _log_request(self, request: Request, response, duration: float):
        """Log the request to the audit trail."""
        db = SessionLocal()
        try:
            # Extract user from Authorization header
            user_id = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                if payload:
                    user_id = int(payload.get("sub"))

            # Get forwarded IP
            forwarded = request.headers.get("x-forwarded-for")
            ip = (
                forwarded.split(",")[0].strip()
                if forwarded
                else (request.client.host if request.client else "unknown")
            )

            # Determine action from method and path
            action = self._determine_action(request.method, request.url.path)

            log = AuditLog(
                user_id=user_id,
                action=action,
                endpoint=str(request.url.path),
                ip_address=ip,
                user_agent=request.headers.get("user-agent", "unknown"),
                details={
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            db.add(log)
            db.commit()

        except Exception as e:
            db.rollback()
            logger.debug(f"Audit log insertion failed: {e}")
        finally:
            db.close()

    def _determine_action(self, method: str, path: str) -> str:
        """Map HTTP method and path to action name."""
        path_lower = path.lower()

        if "/auth/login" in path_lower:
            return "LOGIN"
        elif "/auth/logout" in path_lower:
            return "LOGOUT"
        elif "/auth/register" in path_lower:
            return "USER_CREATED"
        elif (
            "/documents/" in path_lower
            and method == "POST"
            and "/approve" in path_lower
        ):
            return "APPROVE"
        elif (
            "/documents/" in path_lower and method == "POST" and "/reject" in path_lower
        ):
            return "REJECT"
        elif "/documents" in path_lower and method == "DELETE":
            return "DELETE"
        elif "/documents" in path_lower and method == "PUT":
            return "EDIT"
        elif (
            "/documents" in path_lower and method == "POST" and "/upload" in path_lower
        ):
            return "UPLOAD"
        elif (
            "/documents" in path_lower and method == "GET" and "/preview" in path_lower
        ):
            return "DOWNLOAD"

        return f"{method}_{path}"
