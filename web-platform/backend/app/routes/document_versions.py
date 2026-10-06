"""
API Routes for Document Versioning
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import User, Document
from app.services.document_versioning import get_versioning_service

router = APIRouter(prefix="/api/versions", tags=["Document Versions"])


@router.post("/document/{document_id}")
async def create_document_version(
    document_id: int,
    comment: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new document version"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission
        if document.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="No permission to access this document")
        
        # Get file path
        from app.core.config import settings
        file_path = settings.PROCESSING_WORKSPACE / document.stored_filename
        
        # Create version
        versioning_service = get_versioning_service()
        version = versioning_service.create_version(
            document_id,
            str(file_path),
            current_user.id,
            comment,
            document.extracted_metadata
        )
        
        return {
            "success": True,
            "version": {
                "id": version.id,
                "version_number": version.version_number,
                "comment": version.comment,
                "created_at": version.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create version: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/document/{document_id}")
async def get_document_versions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all versions of a document"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission
        if document.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="No permission to access this document")
        
        # Get versions
        versioning_service = get_versioning_service()
        versions = versioning_service.get_document_versions(document_id)
        
        return {
            "success": True,
            "document_id": document_id,
            "total_versions": len(versions),
            "versions": [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "comment": v.comment,
                    "created_by": v.created_by,
                    "created_at": v.created_at.isoformat(),
                    "file_hash": v.file_hash
                }
                for v in versions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get versions: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/document/{document_id}/version/{version_id}")
async def get_version(
    document_id: int,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific version details"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission
        if document.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="No permission to access this document")
        
        # Get version
        versioning_service = get_versioning_service()
        version = versioning_service.get_version(document_id, version_id)
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        return {
            "success": True,
            "version": {
                "id": version.id,
                "version_number": version.version_number,
                "parent_version_id": version.parent_version_id,
                "comment": version.comment,
                "created_by": version.created_by,
                "created_at": version.created_at.isoformat(),
                "file_hash": version.file_hash,
                "metadata": version.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get version: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/document/{document_id}/rollback/{version_id}")
async def rollback_to_version(
    document_id: int,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rollback document to specific version"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission
        if document.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="No permission to access this document")
        
        # Get file path
        from app.core.config import settings
        file_path = settings.PROCESSING_WORKSPACE / document.stored_filename
        
        # Rollback
        versioning_service = get_versioning_service()
        result = versioning_service.rollback_to_version(
            document_id,
            version_id,
            str(file_path),
            current_user.id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/document/{document_id}/compare/{version_id_1}/{version_id_2}")
async def compare_versions(
    document_id: int,
    version_id_1: str,
    version_id_2: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare two document versions"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission
        if document.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="No permission to access this document")
        
        # Compare versions
        versioning_service = get_versioning_service()
        result = versioning_service.compare_versions(document_id, version_id_1, version_id_2)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare versions: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.delete("/document/{document_id}/version/{version_id}")
async def delete_version(
    document_id: int,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete specific version"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted == False
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check permission (admin only)
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        # Delete version
        versioning_service = get_versioning_service()
        result = versioning_service.delete_version(document_id, version_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete version: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")