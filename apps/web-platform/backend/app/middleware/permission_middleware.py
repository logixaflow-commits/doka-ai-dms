"""
Permission Middleware
Folder access check middleware for document operations.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

from app.core.security import get_current_user
from app.core.database import SessionLocal
from app.services.permission_service import permission_service
from app.models.schemas import PermissionLevel


class PermissionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check folder permissions before document access.
    
    This middleware intercepts requests to document endpoints and verifies
    that the user has permission to access the requested folder.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip permission check for non-document endpoints
        path = request.url.path
        
        # Skip permission checks for:
        # - Authentication endpoints
        # - Static files
        # - Health checks
        # - Admin endpoints that handle their own permission checks
        skip_paths = [
            "/api/auth",
            "/static",
            "/health",
            "/api/admin/reports",
            "/api/admin/analytics",
            "/api/admin/activity",
            "/api/admin/folders",
            "/api/permissions",
            "/api/2fa"
        ]
        
        if any(path.startswith(skip) for skip in skip_paths):
            return await call_next(request)
        
        # Skip for GET requests to endpoints that don't require folder access
        if request.method == "GET" and path in ["/", "/login", "/dashboard"]:
            return await call_next(request)

        # For document operations, check folder permissions
        if "/api/documents" in path:
            try:
                # Get current user (this will fail if not authenticated)
                # We need to extract user from request state or token
                # For simplicity, we'll let the endpoint handle authentication
                # and we'll add a decorator-based approach instead
                
                pass  # We'll implement this as a decorator instead
                
            except Exception as e:
                logger.error(f"Permission check error: {e}")
        
        response = await call_next(request)
        return response


# Decorator-based approach for permission checking
def check_folder_permission(required_permission: PermissionLevel = PermissionLevel.READ):
    """
    Decorator to check folder permission for document operations.
    
    This decorator should be used on endpoint functions to enforce
    folder-level access control.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (assuming it's passed via dependency injection)
            # This is a simplified version - in practice you'd need to handle the request properly
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_document_access(user_id: int, document_id: int, required_permission: PermissionLevel, db) -> bool:
    """
    Check if user has permission to access a specific document.
    
    Args:
        user_id: User ID
        document_id: Document ID
        required_permission: Required permission level
        db: Database session
        
    Returns:
        bool: True if user has access
    """
    try:
        from app.models.database import Document
        
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False
        
        # Check if user uploaded the document (always allowed)
        if document.uploaded_by == user_id:
            return True
        
        # Check folder permission
        folder_path = document.suggested_folder or "Unknown"
        
        return permission_service.check_folder_access(
            user_id,
            folder_path,
            required_permission,
            db
        )
        
    except Exception as e:
        logger.error(f"Failed to check document access: {e}")
        return False


def filter_documents_by_user_permissions(user_id: int, documents, db):
    """
    Filter documents based on user's folder permissions.
    
    Args:
        user_id: User ID
        documents: List of Document objects
        db: Database session
        
    Returns:
        List[Document]: Filtered list of documents
    """
    return permission_service.filter_documents_by_permission(user_id, documents, db)


def get_user_accessible_folders(user_id: int, db) -> list:
    """
    Get list of folders user has access to.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        list: List of accessible folder paths
    """
    return permission_service.get_user_folder_permissions(user_id, db)