"""
Office DMS - Search Routes
Full-text search with filters across documents, OCR text, and metadata.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from typing import Optional

from app.core.database import get_db
from app.core.security import require_staff
from app.services.permission_service import permission_service
from app.models.database import Document, User
from app.models.schemas import DocumentListResponse, DocumentResponse

router = APIRouter()


@router.get("")
async def search_documents(
    q: Optional[str] = Query(None, description="Search query text"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    supplier: Optional[str] = Query(None, description="Filter by supplier"),
    is_duplicate: Optional[bool] = Query(None, description="Filter duplicates"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Full-text search across documents with multiple filters.
    Searches: filename, OCR text, metadata, category.
    """
    query = db.query(Document)

    # Text search across multiple fields
    if q:
        search_filter = or_(
            Document.original_filename.ilike(f"%{q}%"),
            Document.ocr_text.ilike(f"%{q}%"),
            Document.category.ilike(f"%{q}%"),
            Document.suggested_folder.ilike(f"%{q}%"),
        )

        # Also search in JSON metadata
        # PostgreSQL has JSON operators, SQLite doesn't support this well
        try:
            # Try to search metadata JSON (works in PostgreSQL)
            from sqlalchemy.dialects.postgresql import JSONB
            search_filter = or_(
                search_filter,
                Document.extracted_metadata.cast(JSONB).op("@>")({"supplier": q}),
            )
        except Exception:
            pass

        query = query.filter(search_filter)

    # Category filter
    if category:
        query = query.filter(Document.category == category)

    # Status filter
    if status:
        query = query.filter(Document.status == status)

    # Date range
    if from_date:
        query = query.filter(Document.created_at >= from_date)
    if to_date:
        query = query.filter(Document.created_at <= to_date + " 23:59:59")

    # Duplicate filter
    if is_duplicate is not None:
        query = query.filter(Document.is_duplicate == is_duplicate)

    # Sorting
    sort_col = getattr(Document, sort_by, Document.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(sort_col)

    # Pagination
    total = query.count()
    docs = query.offset((page - 1) * page_size).limit(page_size).all()

    # Filter by folder permissions
    filtered_docs = permission_service.filter_documents_by_user_permissions(current_user.id, docs, db)

    return {
        "items": [doc.to_dict() for doc in filtered_docs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "query": q,
    }


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get all distinct document categories with counts."""
    from sqlalchemy import func

    results = db.query(
        Document.category,
        func.count(Document.id).label("count")
    ).group_by(Document.category).all()

    return {cat or "Unknown": count for cat, count in results}


@router.get("/suppliers")
async def list_suppliers(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get all distinct suppliers from metadata."""
    docs = db.query(Document).filter(Document.extracted_metadata.isnot(None)).all()

    suppliers = set()
    for doc in docs:
        meta = doc.extracted_metadata or {}
        supplier = meta.get("supplier")
        if supplier:
            suppliers.add(supplier)

    return sorted(suppliers)
