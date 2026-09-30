"""
Office DMS - Authentication Routes
Login, logout, registration, JWT token management.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user, check_login_allowed, record_login_attempt,
    get_client_info, require_admin,
)
from app.core.logging import get_logger, log_audit
from app.models.database import User
from app.models.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/login")
async def login(request: Request, response: Response, login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT tokens with secure cookie for refresh token."""
    client = get_client_info(request)
    ip = client["ip_address"]

    # Rate limiting check
    allowed, lockout_remaining = check_login_allowed(ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {lockout_remaining} seconds."
        )

    # Find user
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        record_login_attempt(ip, success=False)
        log_audit("LOGIN_FAILED", 0, {"username": login_data.username, "ip": ip})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact administrator."
        )

    # Check if 2FA is enabled
    if user.totp_enabled:
        # Return 2FA required response
        return {
            "requires_2fa": True,
            "username": user.username,
            "message": "2FA verification required"
        }

    # Success
    record_login_attempt(ip, success=True)
    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    log_audit("LOGIN", user.id, {"ip": ip, "username": user.username})

    # Set refresh_token in HttpOnly, Secure cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Convert days to seconds
        path="/"
    )

    # Return only access_token in JSON (refresh_token is in cookie)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        "user": UserResponse.model_validate(user).model_dump()
    }


@router.post("/logout")
async def logout(request: Request, response: Response, user: User = Depends(get_current_user)):
    """Logout user and clear refresh token cookie."""
    client = get_client_info(request)
    log_audit("LOGOUT", user.id, {"ip": client["ip_address"]})
    
    # Clear the refresh_token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=settings.ENVIRONMENT == "production",
        httponly=True,
        samesite="strict"
    )
    
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token from cookie."""
    # Try to get refresh token from cookie first
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        # Fallback: try to get from Authorization header (backward compatibility)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ")[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required"
            )
    
    # Decode refresh token
    from app.core.security import decode_token
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )
    
    # Get user from database
    db: Session = next(get_db())
    user = db.query(User).filter(User.id == int(user_id)).first()
    db.close()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    new_access = create_access_token({"sub": str(user.id), "role": user.role})
    
    # Optionally refresh the refresh token cookie as well
    new_refresh = create_refresh_token({"sub": str(user.id)})
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )
    
    return {
        "access_token": new_access,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse)
async def register(
    request: Request,
    user_data: UserCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Register a new user (admin only)."""
    # Check for existing username
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists"
        )

    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role.value,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    client = get_client_info(request)
    log_audit(
        "USER_CREATED",
        admin_user.id,
        {
            "created_user_id": new_user.id,
            "created_username": new_user.username,
            "created_role": new_user.role,
            "ip": client["ip_address"],
        }
    )

    logger.info(f"User registered: {new_user.username} (by admin {admin_user.username})")
    return UserResponse.model_validate(new_user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.email:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role:
        user.role = user_data.role.value
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    log_audit("USER_UPDATED", admin_user.id, {"target_user_id": user_id})
    return UserResponse.model_validate(user)


@router.get("/users")
async def list_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    users = db.query(User).all()
    return [UserResponse.model_validate(u) for u in users]
