"""
Office DMS - API Dependencies
Shared dependencies: RBAC, current user, audit logging.
"""

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    require_admin,
    require_staff,
    require_any_user,
    get_client_info,
    can_view_document,
    can_approve_document,
)
from app.core.logging import get_logger, log_audit
from app.models.database import User

logger = get_logger(__name__)


async def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """Get current user if authenticated, else None (for hybrid pages)."""
    from app.core.security import security_bearer, decode_token

    credentials = await security_bearer(request)
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == int(user_id)).first()


class AuditLogDependency:
    """Dependency that logs API actions to the audit trail."""

    def __init__(self, action: str, log_response: bool = False):
        self.action = action
        self.log_response = log_response

    async def __call__(self, request: Request, user: User = Depends(get_current_user)):
        client = get_client_info(request)
        log_audit(
            action=self.action,
            user_id=user.id,
            details={
                "ip": client["ip_address"],
                "endpoint": client["endpoint"],
                "method": request.method,
            },
        )
        return user
