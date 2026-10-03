"""
Office DMS - Document Routes
CRUD, approve, reject, preview, upload endpoints with RBAC.
"""
import os
import uuid
import anyio
import shutil
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.security import get_current_user, require_staff, require_admin, get_client_info, can_approve_document, can_delete_document
from app.core.storage import storage_manager
from app.core.logging import get_logger, log_audit
from app.core.config import settings
from app.services.email_service import email_service
from app.services.permission_service import permission_service
from app.core.tasks import process_document
from app.models.database import Document, User
from app.models.schemas import (
    DocumentResponse, DocumentListResponse, DocumentDetailResponse,
    DocumentApproveRequest, DocumentRejectRequest, DocumentUpdate,
    DocumentStatus, BulkApproveRequest, BulkRejectRequest, BulkActionResponse,
    DocumentLockRequest, DocumentUnlockRequest, DocumentLockInfo,
    PermissionLevel
)

logger = get_logger(__name__)
router = APIRouter()


def _to_doc_response(doc: Document) -> DocumentResponse:
    """Convert Document model to response schema."""
    resp = DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        stored_filename=doc.stored_filename,
        file_hash=doc.file_hash,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        category=doc.category,
        confidence=doc.confidence,
        suggested_folder=doc.suggested_folder,
        status=doc.status,
        is_duplicate=doc.is_duplicate,
        is_suspicious=doc.is_suspicious,
        suspicious_reason=doc.suspicious_reason,
        extracted_metadata=doc.extracted_metadata,
        ocr_text_preview=(doc.ocr_text[:200] + "...") if doc.ocr_text and len(doc.ocr_text) > 200 else doc.ocr_text,
        created_at=doc.created_at,
        approved_at=doc.approved_at,
        rejection_reason=doc.rejection_reason,
        uploader_name=doc.uploader.username if doc.uploader else None,
        presigned_url=None,
        expiry_date=doc.expiry_date,
        expiry_notes=doc.expiry_notes,
        function_type=doc.function_type,
        function_confidence=doc.function_confidence,
        quality_level=doc.quality_level,
        has_damage=doc.has_damage,
        damage_type=doc.damage_type,
        damage_severity=doc.damage_severity,
    )
    return resp


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """List documents with pagination and filtering."""
    query = db.query(Document)

    if status:
        query = query.filter(Document.status == status)
    if category:
        query = query.filter(Document.category == category)

    total = query.count()
    docs = query.order_by(desc(Document.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    # Filter by folder permissions
    filtered_docs = permission_service.filter_documents_by_user_permissions(current_user.id, docs, db)

    return DocumentListResponse(
        items=[_to_doc_response(d) for d in filtered_docs],
        total=total,  # Keep total before filtering for pagination accuracy
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/pending", response_model=DocumentListResponse)
async def list_pending(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """List documents pending review (status: pending, review, unknown, completed)."""
    pending_statuses = ["pending", "review", "unknown", "completed", "processing", "failed"]
    query = db.query(Document).filter(Document.status.in_(pending_statuses))
    total = query.count()
    docs = query.order_by(desc(Document.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    # Filter by folder permissions
    filtered_docs = permission_service.filter_documents_by_user_permissions(current_user.id, docs, db)

    return DocumentListResponse(
        items=[_to_doc_response(d) for d in filtered_docs],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get document details with presigned URL for preview."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check folder permission
    folder_path = doc.suggested_folder or "Unknown"
    has_access = permission_service.check_folder_access(
        current_user.id,
        folder_path,
        PermissionLevel.READ,
        db
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document"
        )

    # Generate presigned URL for preview
    try:
        presigned = storage_manager.get_presigned_url(doc.storage_key, expiry=timedelta(minutes=15))
    except Exception:
        presigned = None

    resp = DocumentDetailResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        stored_filename=doc.stored_filename,
        file_hash=doc.file_hash,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        category=doc.category,
        confidence=doc.confidence,
        suggested_folder=doc.suggested_folder,
        status=doc.status,
        is_duplicate=doc.is_duplicate,
        is_suspicious=doc.is_suspicious,
        suspicious_reason=doc.suspicious_reason,
        extracted_metadata=doc.extracted_metadata,
        ocr_text_preview=(doc.ocr_text[:500] + "...") if doc.ocr_text and len(doc.ocr_text) > 500 else doc.ocr_text,
        created_at=doc.created_at,
        approved_at=doc.approved_at,
        rejection_reason=doc.rejection_reason,
        uploader_name=doc.uploader.username if doc.uploader else None,
        presigned_url=presigned,
        ocr_text=doc.ocr_text,
        storage_key=doc.storage_key,
        is_encrypted=doc.is_encrypted,
        task_id=doc.task_id,
        retry_count=doc.retry_count,
        classification_method=doc.classification_method,
        locked_by=doc.locked_by,
        locked_at=doc.locked_at,
        locked_by_username=doc.locked_by_user.username if doc.locked_by_user else None,
        expiry_date=doc.expiry_date,
        expiry_notes=doc.expiry_notes,
        function_type=doc.function_type,
        function_confidence=doc.function_confidence,
        quality_level=doc.quality_level,
        has_damage=doc.has_damage,
        damage_type=doc.damage_type,
        damage_severity=doc.damage_severity,
        quality_analysis_metadata=doc.quality_analysis_metadata,
    )
    return resp


@router.get("/{doc_id}/preview")
async def preview_document(
    doc_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get presigned URL for document preview/download."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        url = storage_manager.get_presigned_url(doc.storage_key, expiry=timedelta(minutes=15))
        return {"presigned_url": url, "expires_in_seconds": 900}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview URL: {e}")


@router.post("/{doc_id}/approve")
async def approve_document(
    request: Request,
    doc_id: int,
    approve_data: DocumentApproveRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Approve a document and suggest final folder location."""
    if not can_approve_document(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to approve documents")

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status not in ["pending", "review", "unknown", "completed", "duplicate"]:
        raise HTTPException(status_code=400, detail=f"Cannot approve document with status: {doc.status}")

    doc.previous_status = doc.status
    doc.status = "approved"
    doc.suggested_folder = approve_data.target_folder
    doc.approved_by = current_user.id
    doc.approved_at = datetime.utcnow()

    db.commit()

    client = get_client_info(request)
    log_audit(
        "APPROVE",
        current_user.id,
        {
            "document_id": doc_id,
            "target_folder": approve_data.target_folder,
            "previous_status": doc.previous_status,
            "ip": client["ip_address"],
        }
    )

    return {"message": "Document approved", "document_id": doc_id, "folder": approve_data.target_folder}


@router.post("/{doc_id}/reject")
async def reject_document(
    request: Request,
    doc_id: int,
    reject_data: DocumentRejectRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Reject a document with a reason."""
    if not can_approve_document(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to reject documents")

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.previous_status = doc.status
    doc.status = "rejected"
    doc.rejection_reason = reject_data.reason
    doc.approved_by = current_user.id
    doc.approved_at = datetime.utcnow()

    db.commit()

    client = get_client_info(request)
    log_audit(
        "REJECT",
        current_user.id,
        {
            "document_id": doc_id,
            "reason": reject_data.reason,
            "ip": client["ip_address"],
        }
    )

    return {"message": "Document rejected", "document_id": doc_id, "reason": reject_data.reason}


@router.put("/{doc_id}")
async def update_document(
    request: Request,
    doc_id: int,
    update_data: DocumentUpdate,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Edit document metadata (category, folder, etc.)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    old_values = {}

    if update_data.category is not None:
        old_values["category"] = doc.category
        doc.category = update_data.category
    if update_data.suggested_folder is not None:
        old_values["suggested_folder"] = doc.suggested_folder
        doc.suggested_folder = update_data.suggested_folder
    if update_data.extracted_metadata is not None:
        old_values["metadata"] = doc.extracted_metadata
        doc.extracted_metadata = update_data.extracted_metadata
    if update_data.status is not None:
        old_values["status"] = doc.status
        doc.status = update_data.status.value
    if update_data.expiry_date is not None:
        old_values["expiry_date"] = doc.expiry_date
        doc.expiry_date = update_data.expiry_date
    if update_data.expiry_notes is not None:
        old_values["expiry_notes"] = doc.expiry_notes
        doc.expiry_notes = update_data.expiry_notes

    doc.updated_at = datetime.utcnow()
    db.commit()

    client = get_client_info(request)
    log_audit(
        "EDIT",
        current_user.id,
        {
            "document_id": doc_id,
            "old_values": old_values,
            "ip": client["ip_address"],
        }
    )

    return {"message": "Document updated", "document_id": doc_id}


@router.put("/{doc_id}/ocr")
async def update_ocr_text(
    request: Request,
    doc_id: int,
    ocr_text: str = Form(...),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Update OCR text for a document (with audit logging)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    old_ocr_text = doc.ocr_text
    doc.ocr_text = ocr_text
    doc.updated_at = datetime.utcnow()
    db.commit()

    client = get_client_info(request)
    log_audit(
        "ocr_correction",
        current_user.id,
        {
            "document_id": doc_id,
            "filename": doc.original_filename,
            "old_ocr_preview": (old_ocr_text[:100] + "...") if old_ocr_text and len(old_ocr_text) > 100 else old_ocr_text,
            "new_ocr_preview": (ocr_text[:100] + "...") if ocr_text and len(ocr_text) > 100 else ocr_text,
            "ip": client["ip_address"],
        }
    )

    return {"message": "OCR text updated", "document_id": doc_id}


@router.get("/expiring-soon")
async def get_expiring_soon(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get documents expiring within the specified number of days."""
    cutoff_date = datetime.utcnow() + timedelta(days=days)
    
    expiring_docs = db.query(Document).filter(
        Document.expiry_date.isnot(None),
        Document.expiry_date <= cutoff_date,
        Document.expiry_date >= datetime.utcnow()
    ).order_by(Document.expiry_date).all()

    return {
        "documents": [_to_doc_response(d) for d in expiring_docs],
        "total": len(expiring_docs),
        "days": days
    }


@router.delete("/{doc_id}")
async def delete_document(
    request: Request,
    doc_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a document (admin only)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from storage
    try:
        storage_manager.delete_file(doc.storage_key)
    except Exception as e:
        logger.warning(f"Failed to delete file from storage: {e}")

    db.delete(doc)
    db.commit()

    client = get_client_info(request)
    log_audit("DELETE", admin_user.id, {"document_id": doc_id, "ip": client["ip_address"]})

    return {"message": "Document deleted", "document_id": doc_id}


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Upload a new document (enqueues Celery processing task)."""
    from app.core.config import settings

    # Stream to disk in bounded chunks; never hold the full upload in memory.
    MAX_SIZE = 100 * 1024 * 1024
    chunk_size = 1024 * 1024
    source_name = (file.filename or "upload").replace("\\", "/").rsplit("/", 1)[-1]
    source_name = "".join(char for char in source_name if ord(char) >= 32 and ord(char) != 127)
    source_name = source_name.strip(" .") or "upload"

    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}_{source_name}"
    workspace_path = settings.PROCESSING_WORKSPACE / safe_name
    total_size = 0

    try:
        await anyio.to_thread.run_sync(
            lambda: workspace_path.parent.mkdir(parents=True, exist_ok=True)
        )
        async with await anyio.open_file(workspace_path, "wb") as output:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_SIZE:
                    raise HTTPException(status_code=413, detail="File too large (max 100MB)")
                await output.write(chunk)
    except Exception:
        await anyio.to_thread.run_sync(
            lambda: workspace_path.unlink(missing_ok=True)
        )
        raise
    finally:
        await file.close()

    # Create DB record only after the complete file has been written.
    doc = Document(
        original_filename=source_name,
        stored_filename=safe_name,
        storage_key=f"file://{workspace_path}",
        file_hash="pending",
        file_size=total_size,
        mime_type=file.content_type or "application/octet-stream",
        status="pending",
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Enqueue processing
    task = process_document.delay(
        document_id=doc.id,
        file_path=str(workspace_path),
        original_filename=source_name,
        mime_type=file.content_type or "application/octet-stream",
    )
    doc.task_id = task.id
    db.commit()

    client = get_client_info(request)
    log_audit(
        "UPLOAD",
        current_user.id,
        {
            "document_id": doc.id,
            "filename": source_name,
            "size": total_size,
            "ip": client["ip_address"],
        }
    )

    return {
        "message": "Document uploaded and queued for processing",
        "document_id": doc.id,
        "task_id": task.id,
        "filename": file.filename,
    }


# =============================================================================
# Bulk Actions (Enterprise Feature)
# =============================================================================

@router.post("/bulk/approve", response_model=BulkActionResponse)
async def bulk_approve_documents(
    request: Request,
    bulk_data: BulkApproveRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Approve multiple documents at once."""
    if not can_approve_document(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to approve documents")

    success_count = 0
    failed_count = 0
    errors = []
    details = []

    for doc_id in bulk_data.document_ids:
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                failed_count += 1
                errors.append({"document_id": doc_id, "error": "Document not found"})
                continue

            if doc.status not in ["pending", "review", "unknown", "completed", "duplicate"]:
                failed_count += 1
                errors.append({"document_id": doc_id, "error": f"Cannot approve document with status: {doc.status}"})
                continue

            # Auto-rename the file
            supplier = (doc.extracted_metadata.get("supplier") if doc.extracted_metadata else None) or "Unknown"
            category = doc.category or "Unknown"
            date_str = doc.created_at.strftime("%Y%m%d") if doc.created_at else "Unknown"
            original_name = Path(doc.original_filename).stem
            new_filename = f"{supplier}_{category}_{date_str}_{original_name}.pdf"

            # Update document
            doc.previous_status = doc.status
            doc.status = "approved"
            doc.suggested_folder = bulk_data.target_folder
            doc.approved_by = current_user.id
            doc.approved_at = datetime.utcnow()
            doc.original_filename = new_filename  # Auto-rename

            db.commit()

            success_count += 1
            details.append({
                "document_id": doc_id,
                "old_filename": doc.original_filename,
                "new_filename": new_filename,
                "status": "approved"
            })

            client = get_client_info(request)
            log_audit(
                "BULK_APPROVE",
                current_user.id,
                {
                    "document_id": doc_id,
                    "target_folder": bulk_data.target_folder,
                    "previous_status": doc.previous_status,
                    "ip": client["ip_address"],
                }
            )

        except Exception as e:
            failed_count += 1
            errors.append({"document_id": doc_id, "error": str(e)})
            db.rollback()

    return BulkActionResponse(
        success_count=success_count,
        failed_count=failed_count,
        errors=errors,
        details=details
    )


@router.post("/bulk/reject", response_model=BulkActionResponse)
async def bulk_reject_documents(
    request: Request,
    bulk_data: BulkRejectRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Reject multiple documents at once."""
    if not can_approve_document(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to reject documents")

    success_count = 0
    failed_count = 0
    errors = []
    details = []

    for doc_id in bulk_data.document_ids:
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                failed_count += 1
                errors.append({"document_id": doc_id, "error": "Document not found"})
                continue

            doc.previous_status = doc.status
            doc.status = "rejected"
            doc.rejection_reason = bulk_data.reason
            doc.approved_by = current_user.id
            doc.approved_at = datetime.utcnow()

            db.commit()

            # Send email alert for rejection
            if doc.uploader and doc.uploader.email:
                email_service.send_document_rejection_alert(
                    document_filename=doc.original_filename,
                    rejection_reason=bulk_data.reason,
                    uploaded_by_email=doc.uploader.email,
                    uploaded_by_name=doc.uploader.full_name or doc.uploader.username
                )

            success_count += 1
            details.append({
                "document_id": doc_id,
                "filename": doc.original_filename,
                "status": "rejected"
            })

            client = get_client_info(request)
            log_audit(
                "BULK_REJECT",
                current_user.id,
                {
                    "document_id": doc_id,
                    "reason": bulk_data.reason,
                    "previous_status": doc.previous_status,
                    "ip": client["ip_address"],
                }
            )

        except Exception as e:
            failed_count += 1
            errors.append({"document_id": doc_id, "error": str(e)})
            db.rollback()

    return BulkActionResponse(
        success_count=success_count,
        failed_count=failed_count,
        errors=errors,
        details=details
    )


# =============================================================================
# Document Locking (Enterprise Feature)
# =============================================================================

@router.post("/{doc_id}/lock", response_model=DocumentLockInfo)
async def lock_document(
    request: Request,
    doc_id: int,
    lock_data: DocumentLockRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Lock a document to prevent concurrent edits."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if already locked by another user
    if doc.locked_by and doc.locked_by != current_user.id:
        locker = db.query(User).filter(User.id == doc.locked_by).first()
        raise HTTPException(
            status_code=409,
            detail=f"Document is locked by {locker.username if locker else 'another user'} since {doc.locked_at}"
        )

    # Lock the document
    doc.locked_by = current_user.id
    doc.locked_at = datetime.utcnow()
    db.commit()

    client = get_client_info(request)
    log_audit(
        "LOCK_DOCUMENT",
        current_user.id,
        {
            "document_id": doc_id,
            "ip": client["ip_address"],
        }
    )

    return DocumentLockInfo(
        locked_by=current_user.id,
        locked_by_username=current_user.username,
        locked_at=doc.locked_at,
        is_locked=True
    )


@router.post("/{doc_id}/unlock", response_model=DocumentLockInfo)
async def unlock_document(
    request: Request,
    doc_id: int,
    unlock_data: DocumentUnlockRequest,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Unlock a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if user is the one who locked it or admin
    if doc.locked_by and doc.locked_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to unlock this document")

    # Unlock the document
    doc.locked_by = None
    doc.locked_at = None
    db.commit()

    client = get_client_info(request)
    log_audit(
        "UNLOCK_DOCUMENT",
        current_user.id,
        {
            "document_id": doc_id,
            "ip": client["ip_address"],
        }
    )

    return DocumentLockInfo(
        locked_by=None,
        locked_by_username=None,
        locked_at=None,
        is_locked=False
    )


@router.get("/{doc_id}/lock-status", response_model=DocumentLockInfo)
async def get_lock_status(
    doc_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Get the lock status of a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    is_locked = doc.locked_by is not None
    locked_by_username = None
    if doc.locked_by:
        locker = db.query(User).filter(User.id == doc.locked_by).first()
        locked_by_username = locker.username if locker else None

    return DocumentLockInfo(
        locked_by=doc.locked_by,
        locked_by_username=locked_by_username,
        locked_at=doc.locked_at,
        is_locked=is_locked
    )
