"""
Version Service - Document versioning and history management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import uuid
import hashlib

from sqlalchemy.orm import Session
from app.models.database import Document, DocumentVersion
from app.core.config import settings
from app.core.storage import storage_manager


class VersionService:
    """Service for managing document versions and history."""

    def __init__(self, db: Session):
        self.db = db
        self.max_versions = getattr(settings, 'max_versions_per_document', 10)

    def get_latest_version(self, document_id: int) -> Optional[Document]:
        """
        Get the latest version of a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Latest document or None
        """
        try:
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return None
            return doc
        except Exception as e:
            logger.error(f"Failed to get latest version: {e}")
            return None

    def get_version_history(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get the complete version history of a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of version information
        """
        try:
            versions = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id
            ).order_by(DocumentVersion.version.desc()).all()
            
            history = []
            for v in versions:
                uploader = self.db.query(Document).filter(Document.id == v.uploaded_by).first()
                history.append({
                    "id": v.id,
                    "version": v.version,
                    "storage_key": v.storage_key,
                    "file_hash": v.file_hash,
                    "file_size": v.file_size,
                    "uploaded_at": v.uploaded_at,
                    "comment": v.comment,
                    "uploaded_by_username": uploader.username if uploader else "Unknown"
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get version history: {e}")
            return []

    def create_new_version(
        self,
        document_id: int,
        file_path: str,
        user_id: int,
        comment: Optional[str] = None,
        original_filename: Optional[str] = None
    ) -> Optional[DocumentVersion]:
        """
        Create a new version of an existing document.
        
        Args:
            document_id: Existing document ID
            file_path: Path to new file
            user_id: User uploading the version
            comment: Version comment
            original_filename: Original filename (if different)
            
        Returns:
            New DocumentVersion or None
        """
        try:
            import os
            
            # Get current document
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Document {document_id} not found")
                return None

            # Calculate file hash
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            file_size = os.path.getsize(file_path)

            # Generate new version number
            latest_version = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id
            ).order_by(DocumentVersion.version.desc()).first()
            
            new_version = (latest_version.version + 1) if latest_version else 1

            # Check max versions limit
            if new_version > self.max_versions:
                self._cleanup_old_versions(document_id)

            # Upload new file to storage
            new_storage_key = f"documents/{document_id}/v{new_version}/{original_filename or doc.original_filename}"
            storage_manager.upload_file(file_path, new_storage_key)

            # Create version record
            version_record = DocumentVersion(
                document_id=document_id,
                version=new_version,
                storage_key=new_storage_key,
                file_hash=file_hash,
                file_size=file_size,
                uploaded_by=user_id,
                uploaded_at=datetime.utcnow(),
                comment=comment
            )
            
            self.db.add(version_record)
            
            # Update main document record
            doc.version = new_version
            doc.parent_version_id = doc.id  # Keep reference to previous
            doc.storage_key = new_storage_key
            doc.file_hash = file_hash
            doc.file_size = file_size
            doc.updated_at = datetime.utcnow()
            doc.version_comment = comment
            
            if original_filename:
                doc.original_filename = original_filename
            
            self.db.commit()
            self.db.refresh(version_record)
            
            logger.info(f"Created version {new_version} for document {document_id}")
            return version_record
            
        except Exception as e:
            logger.error(f"Failed to create new version: {e}")
            self.db.rollback()
            return None

    def restore_version(self, document_id: int, version_number: int) -> bool:
        """
        Restore a document to a specific previous version.
        
        Args:
            document_id: Document ID
            version_number: Version to restore
            
        Returns:
            True if successful
        """
        try:
            # Get version record
            version = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version == version_number
            ).first()
            
            if not version:
                logger.error(f"Version {version_number} not found for document {document_id}")
                return False

            # Get current document
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return False

            # Create a backup of current version before restoring
            # (In production, you might want to preserve this as a new version)
            
            # Restore file from storage
            # For MinIO, we copy the file from version storage to current storage
            restored_key = f"documents/{document_id}/restored_v{version_number}/{doc.original_filename}"
            storage_manager.copy_file(version.storage_key, restored_key)
            
            # Update document
            doc.storage_key = restored_key
            doc.file_hash = version.file_hash
            doc.file_size = version.file_size
            doc.parent_version_id = doc.version  # Track previous version
            doc.version = version_number
            doc.updated_at = datetime.utcnow()
            doc.version_comment = f"Restored from version {version_number}"
            
            self.db.commit()
            
            logger.info(f"Restored document {document_id} to version {version_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore version: {e}")
            self.db.rollback()
            return False

    def diff_versions(
        self,
        document_id: int,
        v1: int,
        v2: int
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two versions of a document.
        
        Args:
            document_id: Document ID
            v1: First version number
            v2: Second version number
            
        Returns:
            Diff information
        """
        try:
            version1 = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version == v1
            ).first()
            
            version2 = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version == v2
            ).first()
            
            if not version1 or not version2:
                return None

            # Get file sizes difference
            size_diff = version2.file_size - version1.file_size

            # Check if files are identical
            files_same = version1.file_hash == version2.file_hash

            return {
                "version1": {
                    "version": v1,
                    "file_size": version1.file_size,
                    "file_hash": version1.file_hash,
                    "uploaded_at": version1.uploaded_at
                },
                "version2": {
                    "version": v2,
                    "file_size": version2.file_size,
                    "file_hash": version2.file_hash,
                    "uploaded_at": version2.uploaded_at
                },
                "difference": {
                    "files_same": files_same,
                    "size_diff_bytes": size_diff,
                    "size_diff_human": self._human_readable_size(abs(size_diff))
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to diff versions: {e}")
            return None

    def get_version_file(self, document_id: int, version: int) -> Optional[str]:
        """
        Get the storage key for a specific version.
        
        Args:
            document_id: Document ID
            version: Version number
            
        Returns:
            Storage key or None
        """
        try:
            version_record = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version == version
            ).first()
            
            if version_record:
                return version_record.storage_key
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version file: {e}")
            return None

    def _cleanup_old_versions(self, document_id: int):
        """Remove old versions if exceeding max_versions limit."""
        try:
            versions = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id
            ).order_by(DocumentVersion.version.asc()).all()
            
            if len(versions) <= self.max_versions:
                return

            # Remove oldest versions
            to_remove = versions[:len(versions) - self.max_versions]
            
            for version in to_remove:
                # Delete from storage
                storage_manager.delete_file(version.storage_key)
                
                # Delete record
                self.db.delete(version)
            
            self.db.commit()
            logger.info(f"Cleaned up {len(to_remove)} old versions for document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old versions: {e}")

    def archive_old_versions(self, days: int = 365):
        """Archive versions older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_versions = self.db.query(DocumentVersion).filter(
                DocumentVersion.uploaded_at < cutoff_date
            ).all()
            
            archived_count = 0
            for version in old_versions:
                # Move to archive storage (different prefix)
                archived_key = version.storage_key.replace("documents/", "archive/")
                storage_manager.copy_file(version.storage_key, archived_key)
                storage_manager.delete_file(version.storage_key)
                
                version.storage_key = archived_key
                archived_count += 1
            
            self.db.commit()
            logger.info(f"Archived {archived_count} versions older than {days} days")
            
        except Exception as e:
            logger.error(f"Failed to archive old versions: {e}")

    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def get_version_service(db: Session) -> VersionService:
    """Factory function to get VersionService instance."""
    return VersionService(db)