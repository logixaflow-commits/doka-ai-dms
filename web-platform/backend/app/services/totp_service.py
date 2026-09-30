"""
TOTP Service - Two-Factor Authentication implementation
Handles TOTP secret generation, QR code generation, and OTP verification.
"""
import pyotp
import qrcode
import io
import base64
from typing import Tuple, List
from datetime import datetime, timedelta
from loguru import logger
from app.core.config import settings


class TOTPService:
    """Service for managing TOTP-based 2FA."""

    def __init__(self):
        self.issuer_name = settings.__dict__.get("APP_NAME", "Enterprise DMS")
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 15

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            str: Base32 encoded TOTP secret
        """
        return pyotp.random_base32()

    def get_qr_code(self, secret: str, username: str) -> str:
        """
        Generate QR code for TOTP setup.
        
        Args:
            secret: TOTP secret
            username: Username for the authenticator app
            
        Returns:
            str: Base64 encoded QR code image
        """
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name=self.issuer_name
        )

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Convert to base64
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    def verify_otp(self, secret: str, otp: str) -> bool:
        """
        Verify OTP code against TOTP secret.
        
        Args:
            secret: TOTP secret
            otp: 6-digit OTP code
            
        Returns:
            bool: True if OTP is valid
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(otp, valid_window=1)  # Allow 1 step window
        except Exception as e:
            logger.error(f"OTP verification error: {e}")
            return False

    def generate_backup_codes(self) -> List[str]:
        """
        Generate 10 single-use backup codes.
        
        Returns:
            List[str]: List of backup codes
        """
        codes = []
        for _ in range(10):
            code = pyotp.random_base32(length=8).upper()[:8]
            # Format as XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes

    def is_account_locked(self, failed_attempts: int, locked_until: datetime) -> bool:
        """
        Check if account is locked due to failed OTP attempts.
        
        Args:
            failed_attempts: Number of failed attempts
            locked_until: Lock expiration timestamp
            
        Returns:
            bool: True if account is locked
        """
        if failed_attempts >= self.max_failed_attempts:
            if locked_until and locked_until > datetime.utcnow():
                return True
        return False

    def get_lockout_remaining_minutes(self, locked_until: datetime) -> int:
        """
        Get remaining lockout time in minutes.
        
        Args:
            locked_until: Lock expiration timestamp
            
        Returns:
            int: Remaining minutes
        """
        if not locked_until:
            return 0
        remaining = locked_until - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 60))

    def increment_failed_attempts(self, current_attempts: int) -> Tuple[int, Optional[datetime]]:
        """
        Increment failed OTP attempts and handle lockout.
        
        Args:
            current_attempts: Current number of failed attempts
            
        Returns:
            Tuple[int, Optional[datetime]]: New failed attempts count and lock expiration
        """
        new_attempts = current_attempts + 1
        
        if new_attempts >= self.max_failed_attempts:
            locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
            logger.warning(f"Account locked due to {new_attempts} failed OTP attempts")
            return new_attempts, locked_until
        
        return new_attempts, None

    def reset_failed_attempts(self) -> int:
        """
        Reset failed OTP attempts after successful verification.
        
        Returns:
            int: 0 (reset count)
        """
        return 0


# Global TOTP service instance
totp_service = TOTPService()