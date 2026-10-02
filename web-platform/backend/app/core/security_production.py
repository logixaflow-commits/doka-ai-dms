"""
Production Security Module
Enhanced security features for production deployment
"""
import os
import secrets
import hashlib
import hmac
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from passlib.context import CryptContext
from loguru import logger
import re


class SecurityConfig:
    """Security configuration settings"""
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL = True
    COMMON_PASSWORDS = [
        "password", "123456", "qwerty", "abc123", "password123",
        "admin", "letmein", "welcome", "monkey", "dragon"
    ]
    
    # Session settings
    SESSION_TIMEOUT_MINUTES = 30
    MAX_CONCURRENT_SESSIONS = 3
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    RATE_LIMIT_PER_MINUTE = 100
    RATE_LIMIT_BURST = 20
    
    # Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # Allowed hosts
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")
    
    # IP whitelisting
    IP_WHITELIST = os.getenv("IP_WHITELIST", "").split(",")
    
    # File upload security
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_MIME_TYPES = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    # Input validation
    MAX_STRING_LENGTH = 1000
    MAX_TEXT_LENGTH = 10000


class ProductionSecurity:
    """Production security implementation"""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )
        self.security_bearer = HTTPBearer(auto_error=False)
    
    def generate_secure_key(self) -> str:
        """Generate a cryptographically secure random key"""
        return secrets.token_urlsafe(32)
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    def validate_password_strength(self, password: str) -> tuple[bool, List[str]]:
        """Validate password strength"""
        errors = []
        
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters")
        
        if SecurityConfig.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if SecurityConfig.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if SecurityConfig.REQUIRE_NUMBERS and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if SecurityConfig.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        if password.lower() in SecurityConfig.COMMON_PASSWORDS:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def sanitize_input(self, input_string: str, max_length: Optional[int] = None) -> str:
        """Sanitize user input"""
        if max_length is None:
            max_length = SecurityConfig.MAX_STRING_LENGTH
        
        # Truncate if too long
        if len(input_string) > max_length:
            input_string = input_string[:max_length]
        
        # Remove potentially dangerous characters
        input_string = re.sub(r'[<>]', '', input_string)
        
        return input_string.strip()
    
    def validate_file_upload(self, filename: str, file_size: int, mime_type: str) -> tuple[bool, str]:
        """Validate file upload"""
        # Check file size
        if file_size > SecurityConfig.MAX_FILE_SIZE:
            return False, f"File size exceeds maximum of {SecurityConfig.MAX_FILE_SIZE // (1024*1024)}MB"
        
        # Check MIME type
        if mime_type not in SecurityConfig.ALLOWED_MIME_TYPES:
            return False, f"File type {mime_type} is not allowed"
        
        # Check filename for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False, "Invalid filename"
        
        # Check file extension
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.doc', '.docx']
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            return False, "File extension not allowed"
        
        return True, "File validation passed"
    
    def check_ip_whitelist(self, ip_address: str) -> bool:
        """Check if IP is in whitelist"""
        if not SecurityConfig.IP_WHITELIST or SecurityConfig.IP_WHITELIST == [""]:
            return True  # No whitelist configured, allow all
        
        return ip_address in SecurityConfig.IP_WHITELIST
    
    def check_host_header(self, host: str) -> bool:
        """Check if host is allowed"""
        if not SecurityConfig.ALLOWED_HOSTS or SecurityConfig.ALLOWED_HOSTS == ["localhost"]:
            return True  # No host restriction configured
        
        return host in SecurityConfig.ALLOWED_HOSTS
    
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        encoded = jwt.encode(to_encode, SecurityConfig.SECRET_KEY, algorithm="HS256")
        return encoded
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        encoded = jwt.encode(to_encode, SecurityConfig.SECRET_KEY, algorithm="HS256")
        return encoded
    
    def decode_token(self, token: str) -> Optional[dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, SecurityConfig.SECRET_KEY, algorithms=["HS256"])
            return payload
        except JWTError as e:
            logger.warning(f"Token decode failed: {e}")
            return None
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
    
    def validate_csrf_token(self, token: str, session_token: str) -> bool:
        """Validate CSRF token"""
        return hmac.compare_digest(token, session_token)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        from cryptography.fernet import Fernet
        import os
        
        key = os.getenv("ENCRYPTION_KEY", "default-key-32-chars-")
        fernet = Fernet(key.encode() if len(key) == 44 else key.encode().ljust(44, b'='))
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        from cryptography.fernet import Fernet
        import os
        
        key = os.getenv("ENCRYPTION_KEY", "default-key-32-chars-")
        fernet = Fernet(key.encode() if len(key) == 44 else key.encode().ljust(44, b'='))
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def log_security_event(self, event_type: str, details: dict, request: Request):
        """Log security event"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        logger.info(f"SECURITY_EVENT: {event_type}", extra={
            "event_type": event_type,
            "ip_address": client_ip,
            "user_agent": user_agent,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })


# Singleton instance
_security: Optional[ProductionSecurity] = None


def get_security() -> ProductionSecurity:
    """Get singleton security instance"""
    global _security
    if _security is None:
        _security = ProductionSecurity()
    return _security