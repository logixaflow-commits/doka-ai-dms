"""
Tag Management Routes
Handles document tagging and tag search endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import require_staff, require_admin
from app.models.database import User
from app.services.ai_tagging_service import ai_tagging_service
from app.models.schemas import TagResponse, TagGenerationResponse

router = APIRouter()


@router.post("/documents/{doc_id}/tags", response_model=TagGenerationResponse)
async def generate_document_tags(
    doc_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    Auto-generate and save tags for a document.
    """
    try:
        from app.models.database import Document
        
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Extract metadata and generate tags
        text = doc.ocr_text or ""
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no OCR text"
            )

        metadata = ai_tagging_service.extract_document_metadata(text)
        
        # Update document with new tags
        doc.tags = metadata['tags']
        doc.urgency = metadata['urgency']
        db.commit()
        
        return TagGenerationResponse(
            document_id=doc_id,
            tags=metadata['tags'],
            urgency=metadata['urgency'],
            entities=metadata['entities']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tags"
        )


@router.get("/tags", response_model=list)
async def list_all_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    List all tags with document counts.
    """
    try:
        from app.models.database import Document
        from collections import Counter
        
        # Get all documents
        docs = db.query(Document).filter(Document.tags.isnot(None)).all()
        
        # Count tags
        tag_counter = Counter()
        for doc in docs:
            if doc.tags:
                for tag in doc.tags:
                    tag_counter[tag] += 1
        
        # Return as list of dicts
        return [
            {"tag": tag, "count": count}
            for tag, count in tag_counter.most_common(100)
        ]
        
    except Exception as e:
        logger.error(f"Failed to list tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tags"
        )


@router.get("/tags/{tag}")
async def search_by_tag(
    tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    Search documents by tag.
    """
    try:
        from app.models.database import Document
        
        # Find documents with the tag
        docs = db.query(Document).filter(
            Document.tags.contains(tag) if hasattr(Document.tags, 'contains') else True
        ).all()
        
        # Filter out None tags
        docs = [d for d in docs if d.tags and tag in d.tags]
        
        return {
            "tag": tag,
            "count": len(docs),
            "documents": [
                {
                    "id": d.id,
                    "filename": d.original_filename,
                    "category": d.category,
                    "tags": d.tags
                }
                for d in docs[:50]  # Limit to 50 results
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to search by tag: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search by tag"
        )


@router.get("/urgent")
async def get_urgent_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    Get all urgent documents.
    """
    try:
        from app.models.database import Document
        
        docs = db.query(Document).filter(
            Document.urgency == 'urgent'
        ).order_by(Document.created_at.desc()).all()
        
        return {
            "count": len(docs),
            "documents": [
                {
                    "id": d.id,
                    "filename": d.original_filename,
                    "category": d.category,
                    "urgency": d.urgency,
                    "created_at": d.created_at
                }
                for d in docs
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get urgent documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get urgent documents"
        )