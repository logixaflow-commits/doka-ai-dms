"""
2FA Authentication Routes
Handles TOTP setup, verification, and management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user, require_staff, require_admin
from app.core.logging import log_audit, get_client_info
from app.models.database import User
from app.models.schemas import (
    TOTPSetupRequest, TOTPSetupResponse, TOTPVerifyRequest, TOTPVerifyResponse,
    TOTPEnableRequest, TOTPDisableRequest, Login2FARequest, User2FAStatus
)
from app.services.totp_service import totp_service
from app.core.config import settings

router = APIRouter()


@router.post("/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    request: Request,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Generate TOTP secret and QR code for 2FA setup.
    
    This initiates the 2FA setup process by generating a new TOTP secret
    and QR code that the user can scan with their authenticator app.
    """
    try:
        # Check if 2FA is already enabled
        if current_user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is already enabled for this user"
            )

        # Generate new TOTP secret
        secret = totp_service.generate_secret()
        
        # Generate QR code
        qr_code_url = totp_service.get_qr_code(secret, current_user.username)
        
        # Generate backup codes
        backup_codes = totp_service.generate_backup_codes()
        
        # Store secret temporarily (not enabled yet)
        # In production, you might store this in a temporary table or cache
        current_user.totp_secret = secret  # Note: This should be encrypted
        current_user.backup_codes = backup_codes  # Note: These should be hashed
        db.commit()
        
        client = get_client_info(request)
        log_audit(
            "2FA_SETUP_INITIATED",
            current_user.id,
            {"ip": client["ip_address"]}
        )
        
        return TOTPSetupResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to setup TOTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize 2FA setup"
        )


@router.post("/verify-setup", response_model=TOTPVerifyResponse)
async def verify_setup_totp(
    request: Request,
    otp_data: TOTPVerifyRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Verify OTP during 2FA setup.
    
    After the user scans the QR code, they must verify they can generate
    valid OTP codes before 2FA is enabled.
    """
    try:
        if not current_user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA setup not initiated. Please start setup first."
            )

        # Check if account is locked
        if totp_service.is_account_locked(current_user.failed_otp_attempts, current_user.otp_locked_until):
            remaining_minutes = totp_service.get_lockout_remaining_minutes(current_user.otp_locked_until)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked due to too many failed attempts. Try again in {remaining_minutes} minutes."
            )

        # Verify OTP
        if not totp_service.verify_otp(current_user.totp_secret, otp_data.otp):
            # Increment failed attempts
            new_attempts, locked_until = totp_service.increment_failed_attempts(current_user.failed_otp_attempts)
            current_user.failed_otp_attempts = new_attempts
            current_user.otp_locked_until = locked_until
            db.commit()
            
            remaining_attempts = totp_service.max_failed_attempts - new_attempts
            if locked_until:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Account locked for {totp_service.lockout_duration_minutes} minutes."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
                )

        # OTP verified successfully
        # Reset failed attempts
        current_user.failed_otp_attempts = totp_service.reset_failed_attempts()
        current_user.otp_locked_until = None
        db.commit()
        
        client = get_client_info(request)
        log_audit(
            "2FA_SETUP_VERIFIED",
            current_user.id,
            {"ip": client["ip_address"]}
        )
        
        return TOTPVerifyResponse(
            success=True,
            message="OTP verified successfully. You can now enable 2FA."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify setup TOTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP"
        )


@router.post("/enable")
async def enable_totp(
    request: Request,
    otp_data: TOTPEnableRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Enable 2FA for the user after successful verification.
    
    This finalizes the 2FA setup. The user must have completed the
    verification step before calling this endpoint.
    """
    try:
        if not current_user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA setup not completed. Please complete verification first."
            )

        # Check if 2FA is mandatory for admin
        is_mandatory = settings.__dict__.get("2FA_MANDATORY_FOR_ADMIN", "false").lower() == "true"
        if current_user.role == "admin" and not is_mandatory and not current_user.totp_enabled:
            logger.info(f"Admin {current_user.username} enabling 2FA (optional)")

        # Enable 2FA
        current_user.totp_enabled = True
        current_user.failed_otp_attempts = 0
        current_user.otp_locked_until = None
        db.commit()
        
        client = get_client_info(request)
        log_audit(
            "2FA_ENABLED",
            current_user.id,
            {"ip": client["ip_address"]}
        )
        
        return {
            "message": "2FA enabled successfully",
            "backup_codes_count": len(current_user.backup_codes) if current_user.backup_codes else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable TOTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA"
        )


@router.post("/disable")
async def disable_totp(
    request: Request,
    otp_data: TOTPDisableRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA for the user (requires OTP verification).
    
    Users can disable 2FA by providing their current OTP code.
    """
    try:
        if not current_user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled for this user"
            )

        # Verify OTP
        if not totp_service.verify_otp(current_user.totp_secret, otp_data.otp):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )

        # Check if 2FA is mandatory for admin
        is_mandatory = settings.__dict__.get("2FA_MANDATORY_FOR_ADMIN", "false").lower() == "true"
        if current_user.role == "admin" and is_mandatory:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="2FA is mandatory for admin users and cannot be disabled"
            )

        # Disable 2FA
        current_user.totp_enabled = False
        current_user.totp_secret = None
        current_user.backup_codes = None
        current_user.failed_otp_attempts = 0
        current_user.otp_locked_until = None
        db.commit()
        
        client = get_client_info(request)
        log_audit(
            "2FA_DISABLED",
            current_user.id,
            {"ip": client["ip_address"]}
        )
        
        return {"message": "2FA disabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable TOTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA"
        )


@router.post("/verify-login")
async def verify_login_otp(
    request: Request,
    login_data: Login2FARequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP during login process.
    
    This is called after successful password authentication when 2FA is enabled.
    """
    try:
        # Get user
        user = db.query(User).filter(User.username == login_data.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Check if 2FA is enabled
        if not user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled for this user"
            )

        # Check if account is locked
        if totp_service.is_account_locked(user.failed_otp_attempts, user.otp_locked_until):
            remaining_minutes = totp_service.get_lockout_remaining_minutes(user.otp_locked_until)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked due to too many failed attempts. Try again in {remaining_minutes} minutes."
            )

        # Verify OTP
        if not totp_service.verify_otp(user.totp_secret, login_data.otp):
            # Increment failed attempts
            new_attempts, locked_until = totp_service.increment_failed_attempts(user.failed_otp_attempts)
            user.failed_otp_attempts = new_attempts
            user.otp_locked_until = locked_until
            db.commit()
            
            remaining_attempts = totp_service.max_failed_attempts - new_attempts
            if locked_until:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Account locked for {totp_service.lockout_duration_minutes} minutes."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
                )

        # OTP verified successfully
        # Reset failed attempts
        user.failed_otp_attempts = totp_service.reset_failed_attempts()
        user.otp_locked_until = None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        client = get_client_info(request)
        log_audit(
            "LOGIN_2FA_SUCCESS",
            user.id,
            {"ip": client["ip_address"]}
        )
        
        # Generate tokens (this would typically be done by the main auth endpoint)
        from app.core.security import create_access_token, create_refresh_token
        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        return {
            "success": True,
            "message": "2FA verification successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify login TOTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP"
        )


@router.get("/status", response_model=User2FAStatus)
async def get_2fa_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's 2FA status.
    
    Returns information about whether 2FA is enabled and if backup codes are available.
    """
    try:
        has_backup_codes = bool(current_user.backup_codes and len(current_user.backup_codes) > 0)
        
        return User2FAStatus(
            totp_enabled=current_user.totp_enabled,
            has_backup_codes=has_backup_codes
        )
        
    except Exception as e:
        logger.error(f"Failed to get 2FA status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get 2FA status"
        )


@router.post("/regenerate-backup-codes")
async def regenerate_backup_codes(
    request: Request,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Generate new backup codes (invalidates old ones).
    
    This should only be done if the user has lost access to their backup codes.
    """
    try:
        if not current_user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled for this user"
            )

        # Generate new backup codes
        new_backup_codes = totp_service.generate_backup_codes()
        
        # Store new codes
        current_user.backup_codes = new_backup_codes
        db.commit()
        
        client = get_client_info(request)
        log_audit(
            "BACKUP_CODES_REGENERATED",
            current_user.id,
            {"ip": client["ip_address"]}
        )
        
        return {
            "message": "Backup codes regenerated successfully",
            "backup_codes": new_backup_codes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate backup codes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )