"""
Document Versioning Service
Provides document version history, comparison, and rollback functionality
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import os
import re
import tempfile
from filelock import FileLock
from loguru import logger
from app.core.config import settings


@dataclass
class DocumentVersion:
    """Document version data"""
    id: str
    document_id: int
    version_number: int
    parent_version_id: Optional[str]
    comment: str
    created_by: int
    created_at: datetime
    file_path: str
    file_hash: str
    metadata: Dict[str, Any]
    changes: Optional[Dict[str, Any]] = None


class VersionMetadataError(RuntimeError):
    """Raised when persisted version metadata cannot be read safely."""


class DocumentVersioningService:
    """Service for document version management"""
    
    def __init__(self):
        self.versions_storage_path = Path("storage/versions")
        self.versions_storage_path.mkdir(parents=True, exist_ok=True)

    def _safe_version_dir(self, document_id: int) -> Path:
        """Resolve a document version directory strictly below the version root."""
        if not isinstance(document_id, int) or document_id < 1:
            raise ValueError("Invalid document id.")
        root = self.versions_storage_path.resolve()
        candidate = (root / str(document_id)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("Version path escaped its safe root.") from exc
        return candidate
        
    def create_version(
        self,
        document_id: int,
        file_path: str,
        user_id: int,
        comment: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentVersion:
        """Create a version under a per-document process-safe lock."""
        version_dir = self._safe_version_dir(document_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(version_dir / ".versions.lock"), timeout=30)

        with lock:
            versions = self.get_document_versions(document_id)
            next_version = len(versions) + 1
            version_id = str(uuid.uuid4())
            source_root = Path(settings.PROCESSING_WORKSPACE).resolve()
            source_path = Path(file_path).resolve()
            source_path.relative_to(source_root)
            if not source_path.is_file() or source_path.is_symlink():
                raise ValueError("Version source is not a regular file.")
            suffix = source_path.suffix.lower()
            if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix):
                suffix = ""
            version_file_path = version_dir / f"v{next_version}_{uuid.uuid4().hex}{suffix}"

            try:
                shutil.copy2(source_path, version_file_path)
                file_hash = self._calculate_file_hash(version_file_path)
                version = DocumentVersion(
                    id=version_id,
                    document_id=document_id,
                    version_number=next_version,
                    parent_version_id=versions[-1].id if versions else None,
                    comment=comment,
                    created_by=user_id,
                    created_at=datetime.utcnow(),
                    file_path=str(version_file_path),
                    file_hash=file_hash,
                    metadata=metadata or {},
                )
                self._save_version_metadata(version)
            except Exception as exc:
                version_file_path.unlink(missing_ok=True)
                logger.error(f"Failed to create version for document {document_id}: {exc}")
                raise

        logger.info(f"Created version {next_version} for document {document_id}")
        return version

    def get_document_versions(self, document_id: int) -> List[DocumentVersion]:
        """Get all versions of a document"""
        try:
            metadata_file = self.versions_storage_path / str(document_id) / "versions.json"
            
            if not metadata_file.exists():
                return []
            
            with open(metadata_file, 'r') as f:
                versions_data = json.load(f)
            
            versions = []
            for version_data in versions_data:
                version = DocumentVersion(
                    id=version_data["id"],
                    document_id=version_data["document_id"],
                    version_number=version_data["version_number"],
                    parent_version_id=version_data.get("parent_version_id"),
                    comment=version_data["comment"],
                    created_by=version_data["created_by"],
                    created_at=datetime.fromisoformat(version_data["created_at"]),
                    file_path=version_data["file_path"],
                    file_hash=version_data["file_hash"],
                    metadata=version_data.get("metadata", {}),
                    changes=version_data.get("changes")
                )
                versions.append(version)
            
            return sorted(versions, key=lambda v: v.version_number)
            
        except Exception as e:
            logger.error(f"Failed to read version metadata for document {document_id}: {e}")
            raise VersionMetadataError(
                f"Version metadata is unreadable for document {document_id}"
            ) from e
    
    def get_version(self, document_id: int, version_id: str) -> Optional[DocumentVersion]:
        """Get specific version of a document"""
        versions = self.get_document_versions(document_id)
        
        for version in versions:
            if version.id == version_id:
                return version
        
        return None
    
    def rollback_to_version(
        self,
        document_id: int,
        version_id: str,
        current_file_path: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Rollback document to specific version"""
        try:
            # Get target version
            version = self.get_version(document_id, version_id)
            
            if not version:
                return {
                    "success": False,
                    "error": "Version not found"
                }
            
            # Check if version file exists
            if not Path(version.file_path).exists():
                return {
                    "success": False,
                    "error": "Version file not found"
                }
            
            # Create backup of current version
            self.create_version(
                document_id,
                current_file_path,
                user_id,
                comment="Auto-backup before rollback"
            )
            
            # Copy version file to current location
            shutil.copy2(version.file_path, current_file_path)
            
            logger.info(f"Rolled back document {document_id} to version {version.version_number}")
            
            return {
                "success": True,
                "version_number": version.version_number,
                "message": f"Successfully rolled back to version {version.version_number}"
            }
            
        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def compare_versions(
        self,
        document_id: int,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """Compare two document versions"""
        try:
            version_1 = self.get_version(document_id, version_id_1)
            version_2 = self.get_version(document_id, version_id_2)
            
            if not version_1 or not version_2:
                return {
                    "success": False,
                    "error": "One or both versions not found"
                }
            
            # Compare file hashes
            files_identical = version_1.file_hash == version_2.file_hash
            
            # Compare metadata
            metadata_diff = self._compare_metadata(version_1.metadata, version_2.metadata)
            
            return {
                "success": True,
                "version_1": {
                    "version_number": version_1.version_number,
                    "created_at": version_1.created_at.isoformat(),
                    "created_by": version_1.created_by,
                    "comment": version_1.comment
                },
                "version_2": {
                    "version_number": version_2.version_number,
                    "created_at": version_2.created_at.isoformat(),
                    "created_by": version_2.created_by,
                    "comment": version_2.comment
                },
                "files_identical": files_identical,
                "metadata_diff": metadata_diff
            }
            
        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_version(self, document_id: int, version_id: str) -> Dict[str, Any]:
        """Delete a version while serializing metadata and file updates."""
        version_dir = self.versions_storage_path / str(document_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(version_dir / ".versions.lock"), timeout=30)
        try:
            with lock:
                versions = self.get_document_versions(document_id)
                target = next((item for item in versions if item.id == version_id), None)
                if target is None:
                    return {"success": False, "error": "Version not found"}

                remaining = [item for item in versions if item.id != version_id]
                for index, item in enumerate(remaining, 1):
                    item.version_number = index
                # Persist the new history before deleting the now-unreferenced file.
                self._save_all_versions_metadata(document_id, remaining)
                try:
                    version_root = self.versions_storage_path.resolve()
                    target_path = Path(target.file_path).resolve()
                    target_path.relative_to(version_root)
                    target_path.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    logger.warning(
                        f"Version metadata was updated but old file cleanup failed for "
                        f"document {document_id}, version {version_id}: {cleanup_error}"
                    )

            logger.info(f"Deleted version {version_id} for document {document_id}")
            return {"success": True, "message": "Version deleted successfully"}
        except Exception as exc:
            logger.error(f"Failed to delete version {version_id} for document {document_id}: {exc}")
            return {"success": False, "error": str(exc)}

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _save_version_metadata(self, version: DocumentVersion):
        """Atomically replace metadata; caller holds the per-document lock."""
        metadata_file = self.versions_storage_path / str(version.document_id) / "versions.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        versions_data = []
        if metadata_file.exists():
            with metadata_file.open("r", encoding="utf-8") as source:
                versions_data = json.load(source)

        versions_data.append({
            "id": version.id,
            "document_id": version.document_id,
            "version_number": version.version_number,
            "parent_version_id": version.parent_version_id,
            "comment": version.comment,
            "created_by": version.created_by,
            "created_at": version.created_at.isoformat(),
            "file_path": version.file_path,
            "file_hash": version.file_hash,
            "metadata": version.metadata,
            "changes": version.changes,
        })

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=metadata_file.parent,
                prefix=".versions-",
                suffix=".tmp",
                delete=False,
            ) as target:
                temp_path = Path(target.name)
                json.dump(versions_data, target, indent=2)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temp_path, metadata_file)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _save_all_versions_metadata(self, document_id: int, versions: List[DocumentVersion]):
        """Atomically replace all version metadata; caller holds the document lock."""
        metadata_file = self.versions_storage_path / str(document_id) / "versions.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        versions_data = [
            {
                "id": version.id,
                "document_id": version.document_id,
                "version_number": version.version_number,
                "parent_version_id": version.parent_version_id,
                "comment": version.comment,
                "created_by": version.created_by,
                "created_at": version.created_at.isoformat(),
                "file_path": version.file_path,
                "file_hash": version.file_hash,
                "metadata": version.metadata,
                "changes": version.changes,
            }
            for version in versions
        ]

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=metadata_file.parent,
                prefix=".versions-", suffix=".tmp", delete=False,
            ) as target:
                temp_path = Path(target.name)
                json.dump(versions_data, target, indent=2)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temp_path, metadata_file)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _compare_metadata(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two metadata dictionaries"""
        all_keys = set(metadata1.keys()) | set(metadata2.keys())
        
        diff = {}
        
        for key in all_keys:
            if key not in metadata1:
                diff[key] = {"status": "added", "value": metadata2[key]}
            elif key not in metadata2:
                diff[key] = {"status": "removed", "value": metadata1[key]}
            elif metadata1[key] != metadata2[key]:
                diff[key] = {
                    "status": "changed",
                    "old_value": metadata1[key],
                    "new_value": metadata2[key]
                }
        
        return diff


# Singleton instance
_versioning_service: Optional[DocumentVersioningService] = None


def get_versioning_service() -> DocumentVersioningService:
    """Get singleton versioning service"""
    global _versioning_service
    if _versioning_service is None:
        _versioning_service = DocumentVersioningService()
    return _versioning_service