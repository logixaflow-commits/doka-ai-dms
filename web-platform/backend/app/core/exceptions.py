"""
Office DMS - Custom Exceptions
Domain-specific exceptions for clear error handling across the pipeline.
"""

from fastapi import HTTPException, status


class DMSException(Exception):
    """Base exception for the DMS application."""

    pass


# =============================================================================
# OCR Exceptions
# =============================================================================
class OCRError(DMSException):
    """Raised when OCR processing fails."""

    pass


class OCRLanguageNotSupported(OCRError):
    """Raised when requested OCR language is not available."""

    pass


class OCRPreprocessingError(OCRError):
    """Raised when image preprocessing fails."""

    pass


# =============================================================================
# Classification Exceptions
# =============================================================================
class ClassificationError(DMSException):
    """Raised when document classification fails."""

    pass


class LowConfidenceError(ClassificationError):
    """Raised when classification confidence is too low."""

    pass


# =============================================================================
# Storage Exceptions
# =============================================================================
class StorageError(DMSException):
    """Raised when file storage operations fail."""

    pass


class FileNotFoundInStorage(StorageError):
    """Raised when a file is not found in storage."""

    pass


# =============================================================================
# Pipeline Exceptions
# =============================================================================
class PipelineError(DMSException):
    """Raised when the processing pipeline fails."""

    pass


class DuplicateDetectedError(PipelineError):
    """Raised when a duplicate document is detected."""

    pass


class SuspiciousFileError(PipelineError):
    """Raised when a file fails security checks."""

    pass


# =============================================================================
# Security Exceptions
# =============================================================================
class SecurityError(DMSException):
    """Raised for security-related errors."""

    pass


class EncryptionNotAvailable(SecurityError):
    """Raised when encryption is required but not configured."""

    pass


# =============================================================================
# HTTP Exception Mapping
# =============================================================================
def handle_dms_exception(exc: DMSException) -> HTTPException:
    """Map domain exceptions to HTTP exceptions."""
    if isinstance(exc, OCRError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    elif isinstance(exc, StorageError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    elif isinstance(exc, ClassificationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    elif isinstance(exc, SecurityError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
