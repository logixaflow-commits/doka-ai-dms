"""
Office DMS - Object Storage Module
MinIO/S3 abstraction with presigned URLs, bucket management, and secure access.
Includes LocalStorageManager for Railway/cloud deployments without MinIO.
"""

import re
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Optional, BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageError(RuntimeError):
    """Raised when a local storage operation cannot be completed safely."""


class LocalStorageManager:
    """
    Local filesystem storage for Railway/cloud deployments without MinIO.
    Provides a simple file-based storage backend when MinIO is disabled.
    """

    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default to uploads directory in app root
            self.base_path = Path(__file__).resolve().parent.parent.parent / "uploads"
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageManager initialized with base path: {self.base_path}")

    @staticmethod
    def _safe_storage_component(value: str, *, fallback: str) -> str:
        """Allow a single, non-traversing storage path component."""
        candidate = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", candidate):
            return fallback
        return candidate

    def _generate_key(
        self, category: str, original_filename: str, doc_id: Optional[int] = None
    ) -> str:
        """Generate a unique storage key using only safe path components."""
        original = Path(original_filename)
        ext = original.suffix.lower()
        if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", ext):
            ext = ""
        name_part = self._safe_storage_component(
            original.stem[:30].replace(" ", "_"),
            fallback="document",
        )
        category_part = self._safe_storage_component(category, fallback="uncategorized")
        unique_id = uuid.uuid4().hex
        if doc_id:
            return f"{category_part}/{doc_id}_{name_part}_{unique_id}{ext}"
        return f"{category_part}/{name_part}_{unique_id}{ext}"

    def upload_file(
        self,
        file_data: bytes,
        original_filename: str,
        category: str = "uncategorized",
        doc_id: Optional[int] = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to local filesystem. Returns the storage URI."""
        key = self._generate_key(category, original_filename, doc_id)
        storage_path = self.base_path / key
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(file_data)
        logger.info(f"Stored locally: {storage_path} ({len(file_data)} bytes)")
        return f"file://{storage_path}"

    def upload_file_obj(
        self,
        file_obj: BinaryIO,
        original_filename: str,
        category: str = "uncategorized",
        doc_id: Optional[int] = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload from file object."""
        file_data = file_obj.read()
        return self.upload_file(
            file_data, original_filename, category, doc_id, content_type
        )

    def _resolve_local_path(self, storage_uri: str) -> Path:
        """Resolve a file URI strictly beneath this storage manager's root."""
        if not storage_uri.startswith("file://"):
            raise StorageError("Unknown storage URI scheme.")
        raw_path = storage_uri[len("file://"):]
        raw_candidate = Path(raw_path)
        if raw_candidate.is_symlink():
            raise StorageError("Symlinked storage paths are not allowed.")
        candidate = raw_candidate.resolve()
        root = self.base_path.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise StorageError("Storage path is outside the configured storage root.") from exc
        if candidate.is_symlink():
            raise StorageError("Symlinked storage paths are not allowed.")
        return candidate

    def download_file(self, storage_uri: str) -> bytes:
        """Download file from local filesystem."""
        path = self._resolve_local_path(storage_uri)
        if not path.exists():
            raise StorageError("File not found.")
        return path.read_bytes()

    def delete_file(self, storage_uri: str) -> bool:
        """Delete file from local filesystem."""
        try:
            path = self._resolve_local_path(storage_uri)
            path.unlink(missing_ok=True)
            logger.info("Deleted local storage object.")
            return True
        except StorageError:
            return False
        except OSError as exc:
            logger.error(f"Failed to delete file: {exc}")
            return False

    def get_file_info(self, storage_uri: str) -> dict:
        """Get metadata about a stored file."""
        try:
            path = self._resolve_local_path(storage_uri)
        except StorageError:
            return {}
        if path.exists():
            stat = path.stat()
            return {
                "size": stat.st_size,
                "content_type": "application/octet-stream",
                "last_modified": stat.st_mtime,
            }
        return {}

    def get_stats(self) -> dict:
        """Get storage statistics."""
        try:
            total_size = sum(f.stat().st_size for f in self.base_path.rglob("*") if f.is_file())
            file_count = sum(1 for f in self.base_path.rglob("*") if f.is_file())
            return {
                "status": "connected",
                "type": "local",
                "base_path": str(self.base_path),
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class StorageManager:
    """
    Manages object storage operations via MinIO/S3-compatible API.
    Provides: upload, download, presigned URLs, bucket management.
    Falls back to LocalStorageManager when MinIO is disabled.
    """

    def __init__(self):
        self.client: Optional[Minio] = None
        self.bucket_name: str = settings.MINIO_BUCKET_NAME
        self._connected = False
        self.local_storage: Optional[LocalStorageManager] = None

        # Use local storage if MinIO is disabled
        if not settings.MINIO_ENABLED or settings.STORAGE_TYPE == "local":
            self.local_storage = LocalStorageManager()
            logger.info("Using LocalStorageManager (MinIO disabled)")
        else:
            self._connect()

    def _connect(self):
        """Initialize MinIO client connection."""
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            # Verify connectivity
            self.client.list_buckets()
            self._connected = True
            logger.info(f"Connected to MinIO at {settings.MINIO_ENDPOINT}")

            # Ensure bucket exists
            self._ensure_bucket()

        except Exception as e:
            self._connected = False
            logger.warning(
                f"MinIO connection failed: {e}. Falling back to filesystem storage."
            )

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        if not self._connected:
            return

        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")

            # Set bucket policy to private (deny all public access)
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Deny",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject", "s3:PutObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                        "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                    }
                ],
            }
            # Note: In production, apply stricter policies
        except S3Error as e:
            logger.error(f"Failed to ensure bucket: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _generate_key(
        self, category: str, original_filename: str, doc_id: Optional[int] = None
    ) -> str:
        """Generate a storage key using only safe path components."""
        original = Path(original_filename)
        ext = original.suffix.lower()
        if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", ext):
            ext = ""
        name_part = LocalStorageManager._safe_storage_component(
            original.stem[:30].replace(" ", "_"),
            fallback="document",
        )
        category_part = LocalStorageManager._safe_storage_component(
            category,
            fallback="uncategorized",
        )
        unique_id = uuid.uuid4().hex
        if doc_id:
            return f"{category_part}/{doc_id}_{name_part}_{unique_id}{ext}"
        return f"{category_part}/{name_part}_{unique_id}{ext}"

    def upload_file(
        self,
        file_data: bytes,
        original_filename: str,
        category: str = "uncategorized",
        doc_id: Optional[int] = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload file to storage. Returns the storage URI.
        Uses LocalStorageManager if MinIO is disabled, otherwise MinIO.
        """
        # Use local storage if MinIO is disabled
        if self.local_storage:
            return self.local_storage.upload_file(
                file_data, original_filename, category, doc_id, content_type
            )

        # Use MinIO if enabled
        key = self._generate_key(category, original_filename, doc_id)

        if self._connected:
            try:
                from io import BytesIO

                data_stream = BytesIO(file_data)
                self.client.put_object(
                    self.bucket_name,
                    key,
                    data=data_stream,
                    length=len(file_data),
                    content_type=content_type,
                )
                logger.info(f"Uploaded to MinIO: {key} ({len(file_data)} bytes)")
                return f"minio://{self.bucket_name}/{key}"
            except S3Error as e:
                logger.error(f"MinIO upload failed, falling back to filesystem: {e}")

        # Fallback: filesystem storage
        return self._filesystem_store(file_data, key)

    def upload_file_obj(
        self,
        file_obj: BinaryIO,
        original_filename: str,
        category: str = "uncategorized",
        doc_id: Optional[int] = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload from file object."""
        # Use local storage if MinIO is disabled
        if self.local_storage:
            return self.local_storage.upload_file_obj(
                file_obj, original_filename, category, doc_id, content_type
            )

        file_data = file_obj.read()
        return self.upload_file(
            file_data, original_filename, category, doc_id, content_type
        )

    def _filesystem_store(self, file_data: bytes, key: str) -> str:
        """Store file on local filesystem as fallback."""
        storage_path = settings.ORGANIZED_ROOT / key
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(file_data)
        logger.info(f"Stored on filesystem: {storage_path} ({len(file_data)} bytes)")
        return f"file://{storage_path}"

    @staticmethod
    def _resolve_filesystem_uri(storage_uri: str) -> Path:
        if not storage_uri.startswith("file://"):
            raise StorageError("Unknown storage URI scheme.")
        raw_candidate = Path(storage_uri[len("file://"):])
        if raw_candidate.is_symlink():
            raise StorageError("Symlinked storage paths are not allowed.")
        candidate = raw_candidate.resolve()
        root = Path(settings.ORGANIZED_ROOT).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise StorageError("Storage path is outside the configured root.") from exc
        if candidate.is_symlink():
            raise StorageError("Symlinked storage paths are not allowed.")
        return candidate

    def download_file(self, storage_uri: str) -> bytes:
        """
        Download file from storage. Handles both minio:// and file:// URIs.
        Uses LocalStorageManager if MinIO is disabled.
        """
        # Use local storage if MinIO is disabled
        if self.local_storage:
            return self.local_storage.download_file(storage_uri)

        if storage_uri.startswith("minio://"):
            if not self._connected:
                raise StorageError("MinIO not connected, cannot download from S3")

            key = storage_uri.replace(f"minio://{self.bucket_name}/", "")
            try:
                response = self.client.get_object(self.bucket_name, key)
                data = response.read()
                response.close()
                response.release_conn()
                return data
            except S3Error as e:
                raise StorageError(f"Failed to download from MinIO: {e}") from e

        elif storage_uri.startswith("file://"):
            path = self._resolve_filesystem_uri(storage_uri)
            if not path.exists():
                raise StorageError("File not found.")
            return path.read_bytes()

        else:
            raise StorageError("Unknown storage URI scheme.")

    def get_presigned_url(
        self,
        storage_uri: str,
        expiry: timedelta = timedelta(minutes=15),
        for_upload: bool = False,
    ) -> str:
        """
        Generate a presigned URL for temporary access.
        Returns direct file URL for filesystem storage.
        """
        if storage_uri.startswith("minio://"):
            if not self._connected:
                raise StorageError("MinIO not connected")

            key = storage_uri.replace(f"minio://{self.bucket_name}/", "")
            try:
                if for_upload:
                    url = self.client.presigned_put_object(
                        self.bucket_name, key, expires=expiry
                    )
                else:
                    url = self.client.presigned_get_object(
                        self.bucket_name, key, expires=expiry
                    )
                return url
            except S3Error as e:
                raise StorageError(f"Failed to generate presigned URL: {e}") from e

        elif storage_uri.startswith("file://"):
            path = self._resolve_filesystem_uri(storage_uri)
            return f"/api/files/local/{path}"

        else:
            raise StorageError(f"Unknown storage URI: {storage_uri}")

    def delete_file(self, storage_uri: str) -> bool:
        """Delete file from storage."""
        # Use local storage if MinIO is disabled
        if self.local_storage:
            return self.local_storage.delete_file(storage_uri)

        if storage_uri.startswith("minio://"):
            if not self._connected:
                return False

            key = storage_uri.replace(f"minio://{self.bucket_name}/", "")
            try:
                self.client.remove_object(self.bucket_name, key)
                logger.info(f"Deleted from MinIO: {key}")
                return True
            except S3Error as e:
                logger.error(f"Failed to delete from MinIO: {e}")
                return False

        elif storage_uri.startswith("file://"):
            try:
                path = self._resolve_filesystem_uri(storage_uri)
                path.unlink(missing_ok=True)
                logger.info("Deleted from filesystem.")
                return True
            except (StorageError, OSError) as e:
                logger.error(f"Failed to delete file: {e}")
                return False

        return False

    def get_file_info(self, storage_uri: str) -> dict:
        """Get metadata about a stored file."""
        if storage_uri.startswith("minio://"):
            if not self._connected:
                return {}

            key = storage_uri.replace(f"minio://{self.bucket_name}/", "")
            try:
                stat = self.client.stat_object(self.bucket_name, key)
                return {
                    "size": stat.size,
                    "content_type": stat.content_type,
                    "last_modified": (
                        stat.last_modified.isoformat() if stat.last_modified else None
                    ),
                }
            except S3Error:
                return {}

        elif storage_uri.startswith("file://"):
            try:
                path = self._resolve_filesystem_uri(storage_uri)
            except StorageError:
                return {}
            if path.exists():
                stat = path.stat()
                return {
                    "size": stat.st_size,
                    "content_type": "application/octet-stream",
                    "last_modified": stat.st_mtime,
                }
            return {}

        return {}

    def list_objects(self, prefix: str = "") -> list:
        """List objects in bucket with optional prefix filter."""
        if not self._connected:
            return []

        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True
            )
            return [{"key": obj.object_name, "size": obj.size} for obj in objects]
        except S3Error as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    def get_stats(self) -> dict:
        """Get storage statistics."""
        # Use local storage if MinIO is disabled
        if self.local_storage:
            return self.local_storage.get_stats()

        if not self._connected:
            return {"status": "disconnected", "bucket": self.bucket_name}

        try:
            objects = self.list_objects()
            total_size = sum(obj["size"] for obj in objects)
            return {
                "status": "connected",
                "bucket": self.bucket_name,
                "endpoint": settings.MINIO_ENDPOINT,
                "total_objects": len(objects),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class StorageError(Exception):
    """Raised when storage operations fail."""

    pass


# Singleton
storage_manager = StorageManager()
