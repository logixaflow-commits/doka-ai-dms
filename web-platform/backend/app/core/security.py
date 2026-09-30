"""
Office DMS - Security Module
Password hashing (bcrypt), JWT token management, and RBAC dependencies.
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.database import User
from app.models.schemas import UserRole
from app.core.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer for token auth
security_bearer = HTTPBearer(auto_error=False)


# =============================================================================
# Password Utilities
# =============================================================================
def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


# =============================================================================
# JWT Token Utilities
# =============================================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError as e:
        logger.debug(f"Token decode failed: {e}")
        return None


# =============================================================================
# Authentication Dependencies
# =============================================================================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get the currently authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# =============================================================================
# RBAC Dependencies
# =============================================================================
class RoleChecker:
    """Dependency factory for role-based access control."""

    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            logger.warning(
                f"Access denied: user '{user.username}' (role={user.role}) attempted "
                f"to access resource requiring {self.allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(self.allowed_roles)}"
            )
        return user


# Pre-built role dependencies
require_admin = RoleChecker([UserRole.ADMIN.value])
require_staff = RoleChecker([UserRole.ADMIN.value, UserRole.STAFF.value])
require_any_user = RoleChecker([
    UserRole.ADMIN.value, UserRole.STAFF.value, UserRole.CUSTOMER.value
])


# =============================================================================
# Permission Helpers
# =============================================================================
def can_view_document(user: User, document) -> bool:
    """Check if user can view a specific document."""
    if user.role == UserRole.ADMIN.value:
        return True
    if user.role == UserRole.STAFF.value:
        return True
    # Customer can only view their own uploads
    return document.uploaded_by == user.id


def can_approve_document(user: User) -> bool:
    """Check if user can approve/reject documents."""
    return user.role in [UserRole.ADMIN.value, UserRole.STAFF.value]


def can_delete_document(user: User) -> bool:
    """Check if user can delete documents. Only admins."""
    return user.role == UserRole.ADMIN.value


def can_manage_users(user: User) -> bool:
    """Check if user can manage other users."""
    return user.role == UserRole.ADMIN.value


def can_view_audit_logs(user: User) -> bool:
    """Check if user can view audit logs."""
    return user.role == UserRole.ADMIN.value


# =============================================================================
# Client Info Extraction
# =============================================================================
def get_client_info(request: Request) -> dict:
    """Extract client IP and user agent from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "endpoint": str(request.url.path),
    }


# =============================================================================
# Login Rate Limiting (Simple In-Memory)
# =============================================================================
_login_attempts: dict = {}  # ip -> {count, locked_until}


def check_login_allowed(ip: str) -> tuple[bool, Optional[int]]:
    """Check if login is allowed from this IP. Returns (allowed, lockout_seconds_remaining)."""
    now = datetime.utcnow()
    record = _login_attempts.get(ip)

    if record and record.get("locked_until"):
        if now < record["locked_until"]:
            remaining = int((record["locked_until"] - now).total_seconds())
            return False, remaining
        else:
            # Lockout expired, reset
            del _login_attempts[ip]

    return True, None


def record_login_attempt(ip: str, success: bool):
    """Record a login attempt. Lock IP after max failures."""
    now = datetime.utcnow()

    if success:
        # Clear failures on success
        if ip in _login_attempts:
            del _login_attempts[ip]
        return

    if ip not in _login_attempts:
        _login_attempts[ip] = {"count": 0, "locked_until": None}

    _login_attempts[ip]["count"] += 1

    if _login_attempts[ip]["count"] >= settings.MAX_LOGIN_ATTEMPTS:
        lockout_duration = timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
        _login_attempts[ip]["locked_until"] = now + lockout_duration
        logger.warning(f"IP {ip} locked out for {settings.LOCKOUT_DURATION_MINUTES} minutes after {settings.MAX_LOGIN_ATTEMPTS} failed login attempts")
