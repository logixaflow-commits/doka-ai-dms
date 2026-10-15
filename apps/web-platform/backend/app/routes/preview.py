"""
API Routes for Document Preview and Annotation
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import User, Document
from app.services.document_preview import (
    DocumentPreviewService,
    get_preview_service,
    Annotation,
    AnnotationType
)
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/api/preview", tags=["Preview"])


@router.post("/generate/{document_id}")
async def generate_preview(
    document_id: int,
    max_pages: int = Form(10),
    quality: str = Form("medium"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate document preview"""
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
        
        # Generate preview
        preview_service = get_preview_service()
        result = preview_service.generate_preview(
            str(file_path),
            document_id,
            max_pages,
            quality
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/{document_id}/page/{page_number}")
async def get_preview_page(
    document_id: int,
    page_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get preview page image"""
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
        
        # Get preview path
        preview_service = get_preview_service()
        preview_dir = preview_service.annotation_storage_path / f"previews/{document_id}"
        preview_path = preview_dir / f"page_{page_number}.jpg"
        
        if not preview_path.exists():
            raise HTTPException(status_code=404, detail="Preview page not found")
        
        return FileResponse(preview_path, media_type="image/jpeg")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get preview page: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/annotation")
async def add_annotation(
    document_id: int = Form(...),
    annotation_type: str = Form(...),
    page_number: int = Form(...),
    position: str = Form(...),  # JSON string
    content: str = Form(...),
    color: str = Form("#ffff00"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add annotation to document"""
    try:
        import json
        import uuid
        from datetime import datetime
        
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
        
        # Parse position
        position_data = json.loads(position)
        
        # Create annotation
        annotation = Annotation(
            id=str(uuid.uuid4()),
            type=AnnotationType(annotation_type),
            user_id=current_user.id,
            document_id=document_id,
            page_number=page_number,
            position=position_data,
            content=content,
            color=color,
            created_at=datetime.utcnow()
        )
        
        # Add annotation
        preview_service = get_preview_service()
        result = preview_service.add_annotation(annotation)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add annotation: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/annotations/{document_id}")
async def get_annotations(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get annotations for document"""
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
        
        # Get annotations
        preview_service = get_preview_service()
        annotations = preview_service.get_annotations(document_id)
        
        return {
            "success": True,
            "document_id": document_id,
            "annotations": annotations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get annotations: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.delete("/annotation/{document_id}/{annotation_id}")
async def delete_annotation(
    document_id: int,
    annotation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete annotation"""
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
        
        # Delete annotation
        preview_service = get_preview_service()
        result = preview_service.delete_annotation(document_id, annotation_id, current_user.id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete annotation: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/print/{document_id}")
async def get_print_view(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get print-friendly view"""
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
        
        # Get print view
        preview_service = get_preview_service()
        result = preview_service.get_print_view(document_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get print view: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")