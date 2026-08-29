"""
Office DMS - File Watcher
Watchdog-based monitoring of Watch_Folder and multiple social media sources with Celery task dispatch.
Keeps original files untouched - only copies to Processing_Workspace.
"""
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from app.core.config import settings
from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.core.storage import storage_manager
from app.core.tasks import process_document
from app.models.database import Document, User
from app.services.social_ingestor import social_ingestor

logger = get_logger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp",
    ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv",
}

# MIME type mapping
EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


class DMSFileHandler(FileSystemEventHandler):
    """
    Handles file system events in the Watch_Folder.
    On new file: copy to Processing_Workspace, create DB record, enqueue Celery task.
    """

    def __init__(self):
        super().__init__()
        self._processing: Set[str] = set()  # Track files currently being processed

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def on_moved(self, event):
        """Handle file move/rename event."""
        if event.is_directory:
            return
        self._handle_file(event.dest_path)

    def _handle_file(self, file_path: str):
        """Process a single file: validate, copy, enqueue."""
        path = Path(file_path)

        # Skip if already processing
        if file_path in self._processing:
            return

        # Skip hidden/temp files
        if path.name.startswith(".") or path.name.startswith("~"):
            return

        # Skip unsupported extensions
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug(f"Skipping unsupported file: {path.name}")
            return

        # Skip if file is still being written (wait for stability)
        if not self._is_file_stable(path):
            logger.debug(f"File still being written, deferring: {path.name}")
            return

        self._processing.add(file_path)

        try:
            self._process_file(path)
        except Exception as e:
            logger.error(f"Failed to process watched file {path.name}: {e}")
        finally:
            self._processing.discard(file_path)

    def _is_file_stable(self, path: Path, checks: int = 3, delay: float = 0.5) -> bool:
        """Check if file has finished writing by comparing size over time."""
        try:
            size1 = path.stat().st_size
            for _ in range(checks):
                import time
                time.sleep(delay)
                size2 = path.stat().st_size
                if size1 != size2:
                    return False
                size1 = size2
            return True
        except Exception:
            return False

    def _process_file(self, path: Path):
        """
        Core processing: copy to workspace, create DB entry, enqueue task.
        Original file is NEVER modified.
        """
        db = SessionLocal()

        try:
            logger.info(f"New file detected: {path.name} ({path.stat().st_size} bytes)")

            # Generate UUID-based working filename
            file_id = str(uuid.uuid4())
            safe_name = f"{file_id}_{path.name}"
            workspace_path = settings.PROCESSING_WORKSPACE / safe_name

            # Copy to Processing_Workspace (never touch original)
            shutil.copy2(str(path), str(workspace_path))
            logger.info(f"Copied to workspace: {workspace_path}")

            # Get MIME type
            mime_type = EXT_TO_MIME.get(path.suffix.lower(), "application/octet-stream")

            # Get or create default user (system watcher)
            default_user = db.query(User).filter(User.username == "system").first()
            if not default_user:
                # Find admin user
                default_user = db.query(User).filter(User.role == "admin").first()
                if not default_user:
                    logger.error("No admin user found. Cannot process watched file.")
                    return

            # Create database record
            doc = Document(
                original_filename=path.name,
                stored_filename=safe_name,
                storage_key=f"file://{workspace_path}",
                file_hash="pending",  # Will be computed in pipeline
                file_size=path.stat().st_size,
                mime_type=mime_type,
                status="pending",
                uploaded_by=default_user.id,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            logger.info(f"Document record created: id={doc.id}, filename={path.name}")

            # Enqueue Celery task for async processing
            task = process_document.delay(
                document_id=doc.id,
                file_path=str(workspace_path),
                original_filename=path.name,
                mime_type=mime_type,
            )

            doc.task_id = task.id
            db.commit()

            logger.info(f"Celery task enqueued: {task.id} for document {doc.id}")

        except Exception as e:
            db.rollback()
            logger.error(f"File processing error for {path.name}: {e}")
            raise

        finally:
            db.close()


class SocialMediaFileHandler(FileSystemEventHandler):
    """
    Handles file system events for social media sources (Viber, WhatsApp, etc.).
    Uses SocialMediaIngestor for daily folder organization and auto-naming.
    """

    def __init__(self, source_name: str):
        super().__init__()
        self.source_name = source_name
        self._processing: Set[str] = set()

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def on_moved(self, event):
        """Handle file move/rename event."""
        if event.is_directory:
            return
        self._handle_file(event.dest_path)

    def _handle_file(self, file_path: str):
        """Process a social media file using SocialMediaIngestor."""
        path = Path(file_path)

        # Skip if already processing
        if file_path in self._processing:
            return

        # Skip hidden/temp files
        if path.name.startswith(".") or path.name.startswith("~"):
            return

        # Skip unsupported extensions
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug(f"Skipping unsupported file: {path.name}")
            return

        # Skip if file is still being written
        if not self._is_file_stable(path):
            logger.debug(f"File still being written, deferring: {path.name}")
            return

        self._processing.add(file_path)

        try:
            import asyncio
            # Create new event loop for async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            db = SessionLocal()
            try:
                # Get default user
                default_user = db.query(User).filter(User.username == "system").first()
                if not default_user:
                    default_user = db.query(User).filter(User.role == "admin").first()
                    if not default_user:
                        logger.error("No admin user found. Cannot process social media file.")
                        return

                # Process using SocialMediaIngestor
                document = loop.run_until_complete(
                    social_ingestor.process_social_file(
                        source_path=path,
                        source_name=self.source_name,
                        uploaded_by=default_user.id,
                        db=db
                    )
                )

                if document:
                    logger.info(f"Social media file processed: {path.name} from {self.source_name}")

            finally:
                db.close()
                loop.close()

        except Exception as e:
            logger.error(f"Failed to process social media file {path.name}: {e}")
        finally:
            self._processing.discard(file_path)

    def _is_file_stable(self, path: Path, checks: int = 3, delay: float = 0.5) -> bool:
        """Check if file has finished writing by comparing size over time."""
        try:
            size1 = path.stat().st_size
            for _ in range(checks):
                import time
                time.sleep(delay)
                size2 = path.stat().st_size
                if size1 != size2:
                    return False
                size1 = size2
            return True
        except Exception:
            return False


class FileWatcher:
    """
    Manages multiple watchdog observers for Watch_Folder and social media sources.
    """

    def __init__(self):
        self.main_observer: Optional[Observer] = None
        self.main_handler = DMSFileHandler()
        self.social_observers: Dict[str, Observer] = {}  # source_name -> Observer
        self.is_running = False

    def start(self):
        """Start watching the Watch_Folder and all enabled social media sources."""
        if self.is_running:
            logger.warning("File watcher is already running")
            return

        # Start main Watch_Folder
        watch_path = settings.WATCH_FOLDER
        watch_path.mkdir(parents=True, exist_ok=True)

        self.main_observer = Observer()
        self.main_observer.schedule(self.main_handler, str(watch_path), recursive=False)
        self.main_observer.start()

        logger.info(f"Main file watcher started: monitoring {watch_path}")

        # Start social media sources
        watch_sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []
        for source_config in watch_sources:
            source_name = source_config.get('name')
            source_path = source_config.get('path')
            enabled = source_config.get('enabled', False)

            if enabled and source_path:
                try:
                    path = Path(source_path)
                    if path.exists():
                        observer = Observer()
                        handler = SocialMediaFileHandler(source_name)
                        observer.schedule(handler, str(path), recursive=False)
                        observer.start()
                        self.social_observers[source_name] = observer
                        logger.info(f"Social media watcher started for {source_name}: {source_path}")
                    else:
                        logger.warning(f"Source path does not exist: {source_path}")
                except Exception as e:
                    logger.error(f"Failed to start watcher for {source_name}: {e}")

        self.is_running = True
        logger.info("All file watchers started successfully")

    def stop(self):
        """Stop all file watchers."""
        if self.main_observer:
            self.main_observer.stop()
            self.main_observer.join()
            logger.info("Main file watcher stopped")

        for source_name, observer in self.social_observers.items():
            observer.stop()
            observer.join()
            logger.info(f"Social media watcher stopped for {source_name}")

        self.social_observers.clear()
        self.is_running = False

    def get_status(self) -> dict:
        """Get watcher status."""
        watch_path = settings.WATCH_FOLDER
        main_file_count = len([f for f in watch_path.iterdir() if f.is_file()]) if watch_path.exists() else 0

        social_sources_status = {}
        for source_name in self.social_observers.keys():
            source_config = social_ingestor.get_source_config(source_name)
            if source_config:
                source_path = Path(source_config.get('path', ''))
                file_count = len([f for f in source_path.iterdir() if f.is_file()]) if source_path.exists() else 0
                social_sources_status[source_name] = {
                    "path": str(source_path),
                    "enabled": source_config.get('enabled', False),
                    "file_count": file_count
                }

        return {
            "is_running": self.is_running,
            "watch_folder": str(watch_path),
            "pending_files": main_file_count,
            "social_sources": social_sources_status,
            "supported_extensions": list(SUPPORTED_EXTENSIONS),
        }

    def restart_source(self, source_name: str):
        """Restart a specific social media source watcher."""
        if source_name in self.social_observers:
            self.social_observers[source_name].stop()
            self.social_observers[source_name].join()
            del self.social_observers[source_name]

        source_config = social_ingestor.get_source_config(source_name)
        if source_config and source_config.get('enabled', False):
            source_path = Path(source_config.get('path', ''))
            if source_path.exists():
                observer = Observer()
                handler = SocialMediaFileHandler(source_name)
                observer.schedule(handler, str(source_path), recursive=False)
                observer.start()
                self.social_observers[source_name] = observer
                logger.info(f"Social media watcher restarted for {source_name}")


# Singleton
file_watcher = FileWatcher()
