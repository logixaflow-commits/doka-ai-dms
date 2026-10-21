"""
Version Management Routes
Handles document versioning and history endpoints.
"""
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_staff
from app.core.upload_safety import (
    DEFAULT_MAX_UPLOAD_BYTES,
    UploadTooLargeError,
    safe_upload_filename,
    stream_upload_bounded,
)
from app.models.database import User
from app.services.version_service import get_version_service

router = APIRouter()


_DEFAULT_MAX_VERSION_UPLOAD_BYTES = DEFAULT_MAX_UPLOAD_BYTES


@router.get("/documents/{doc_id}/versions")
async def list_versions(
    doc_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """List all versions of a document."""
    try:
        version_service = get_version_service(db)
        history = version_service.get_version_history(doc_id)
        
        return {
            "document_id": doc_id,
            "versions": history,
            "total_versions": len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to list versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list versions"
        )


@router.get("/documents/{doc_id}/versions/{version}")
async def get_version(
    doc_id: int,
    version: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Get specific version details."""
    try:
        version_service = get_version_service(db)
        storage_key = version_service.get_version_file(doc_id, version)
        
        if not storage_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found"
            )
        
        # Get version record for details
        from app.models.database import DocumentVersion
        version_record = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc_id,
            DocumentVersion.version == version
        ).first()
        
        if not version_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found"
            )
        
        return {
            "document_id": doc_id,
            "version": version,
            "storage_key": storage_key,
            "file_size": version_record.file_size,
            "uploaded_at": version_record.uploaded_at,
            "comment": version_record.comment
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get version"
        )


@router.post("/documents/{doc_id}/versions")
async def upload_new_version(
    doc_id: int,
    file: UploadFile = File(...),
    comment: str | None = None,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Upload a new version using bounded streaming and a sanitized basename."""
    max_bytes = _DEFAULT_MAX_VERSION_UPLOAD_BYTES
    if file.size is not None and file.size > max_bytes:
        await file.close()
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    safe_name = safe_upload_filename(file.filename)
    tmp_file_path: str | None = None
    try:
        fd, tmp_file_path = tempfile.mkstemp(prefix="doka-version-")
        with os.fdopen(fd, "wb") as tmp_file:
            try:
                await stream_upload_bounded(file, tmp_file, max_bytes=max_bytes)
            except UploadTooLargeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large",
                ) from exc

        version_service = get_version_service(db)
        version_record = version_service.create_new_version(
            document_id=doc_id,
            file_path=tmp_file_path,
            user_id=current_user.id,
            comment=comment,
            original_filename=safe_name,
        )
        if not version_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create version",
            )

        return {
            "message": "Version created successfully",
            "document_id": doc_id,
            "version": version_record.version,
            "created_at": version_record.uploaded_at,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to upload document version (document_id={})", doc_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload new version",
        ) from exc
    finally:
        await file.close()
        if tmp_file_path is not None:
            try:
                os.unlink(tmp_file_path)
            except FileNotFoundError:
                pass
            except OSError:
                logger.warning("Failed to remove temporary version upload file")


@router.post("/documents/{doc_id}/versions/{version}/restore")
async def restore_version(
    doc_id: int,
    version: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Restore a document to a specific version."""
    try:
        version_service = get_version_service(db)
        success = version_service.restore_version(doc_id, version)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore version"
            )
        
        return {
            "message": f"Document restored to version {version}",
            "document_id": doc_id,
            "restored_to_version": version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore version"
        )


@router.get("/documents/{doc_id}/versions/diff")
async def diff_versions(
    doc_id: int,
    v1: int,
    v2: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Compare two versions of a document."""
    try:
        version_service = get_version_service(db)
        diff = version_service.diff_versions(doc_id, v1, v2)
        
        if not diff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both versions not found"
            )
        
        return diff
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to diff versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to diff versions"
        )