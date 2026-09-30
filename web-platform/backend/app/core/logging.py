"""
Office DMS - Logging Configuration
Simple logging with loguru for development and production.
"""
import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings


def setup_logging():
    """Configure loguru with structured JSON output for production."""
    # Remove default handler
    logger.remove()

    # Ensure log directory exists
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Console handler - simple format for all environments
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=False,  # Disable color to avoid encoding issues
    )

    # File handler - application logs (simple format)
    app_log = settings.LOG_DIR / "application.log"
    logger.add(
        str(app_log),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}\n",
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        enqueue=True,
    )

    # File handler - human-readable audit trail
    audit_log = settings.LOG_DIR / "audit.log"
    logger.add(
        str(audit_log),
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}\n",
        level="INFO",
        filter=lambda record: record["extra"].get("audit") is True,
        rotation="5 MB",
        retention="90 days",
        enqueue=True,
    )

    # File handler - error logs only
    error_log = settings.LOG_DIR / "error.log"
    logger.add(
        str(error_log),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}\n",
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="gz",
        enqueue=True,
    )

    return logger


def get_logger(name: str):
    """Get a named logger instance."""
    return logger.bind(name=name)


def log_audit(action: str, user_id: int, details: dict = None):
    """Log an audit event to the human-readable audit log."""
    details_str = ""
    if details:
        parts = []
        for key, value in details.items():
            if value is not None:
                parts.append(f"{key}={value}")
        details_str = " | " + " | ".join(parts) if parts else ""

    logger.bind(audit=True).info(
        f"ACTION={action} | USER={user_id}{details_str}"
    )


def get_client_info(request):
    """Extract client information from request for logging."""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "method": request.method,
        "path": request.url.path,
    }


# Initialize on module import
setup_logging()
