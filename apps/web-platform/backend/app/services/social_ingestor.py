"""
Office DMS - Social Media Ingestion Service
Handles automatic ingestion, daily organization, and naming of social media documents.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.database import get_db
from app.models.database import Document, User
from app.services.ocr_service import ocr_service
from app.services.classifier import classifier
from app.services.metadata_extractor import metadata_extractor
from app.core.storage import storage_manager

logger = get_logger(__name__)


class SocialMediaIngestor:
    """
    Service for processing social media downloaded documents.
    Handles daily folder organization, auto-naming, and metadata extraction.
    """

    def __init__(self):
        self.base_folder = settings.ORGANIZED_ROOT / "Social_Media"
        self.watch_sources = settings.watch_sources if hasattr(settings, 'watch_sources') else []
        self.date_format = settings.social_media.get('date_format', '%Y-%m-%d') if hasattr(settings, 'social_media') else '%Y-%m-%d'
        self.naming_template = settings.social_media.get('naming_template', '{date}_{source}_{category}_{original_name}') if hasattr(settings, 'social_media') else '{date}_{source}_{category}_{original_name}'
        self.create_daily_folders = settings.social_media.get('create_daily_folders', True) if hasattr(settings, 'social_media') else True

        # Create base folder if it doesn't exist
        self.base_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Social Media Ingestor initialized with base folder: {self.base_folder}")

    def get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific social media source."""
        for source in self.watch_sources:
            if source.get('name') == source_name:
                return source
        return None

    def get_daily_folder(self, date: Optional[datetime] = None) -> Path:
        """
        Get the daily folder path for a given date.
        Format: base_folder/YYYY-MM-DD/
        """
        if date is None:
            date = datetime.utcnow()

        date_str = date.strftime(self.date_format)
        daily_folder = self.base_folder / date_str

        if self.create_daily_folders:
            daily_folder.mkdir(parents=True, exist_ok=True)

        return daily_folder

    def generate_filename(self, source: str, category: str, original_filename: str, date: Optional[datetime] = None) -> str:
        """
        Generate filename according to the naming template.
        Template: {date}_{source}_{category}_{original_name}.pdf
        """
        if date is None:
            date = datetime.utcnow()

        date_str = date.strftime(self.date_format)

        # Clean up original filename
        clean_original = original_filename.replace(' ', '_')
        if not clean_original.lower().endswith('.pdf'):
            clean_original += '.pdf'

        # Apply naming template
        filename = self.naming_template.format(
            date=date_str,
            source=source,
            category=category if category else 'Unknown',
            original_name=clean_original
        )

        return filename

    async def process_social_file(
        self,
        source_path: Path,
        source_name: str,
        uploaded_by: int,
        db: Session
    ) -> Optional[Document]:
        """
        Process a social media downloaded file.

        Steps:
        1. Copy file to daily folder
        2. Generate new filename
        3. Extract OCR text
        4. Classify document
        5. Extract metadata
        6. Create database record with status = "pending_review"

        Args:
            source_path: Path to the original file
            source_name: Name of the source (Viber, WhatsApp, etc.)
            uploaded_by: User ID who uploaded/owns the document
            db: Database session

        Returns:
            Created Document record or None if failed
        """
        try:
            source_config = self.get_source_config(source_name)
            if not source_config:
                logger.error(f"Source configuration not found for: {source_name}")
                return None

            if not source_config.get('enabled', False):
                logger.info(f"Source {source_name} is disabled, skipping")
                return None

            # Verify file exists
            if not source_path.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return None

            # Get daily folder
            daily_folder = self.get_daily_folder()

            # Step 1: OCR extraction
            logger.info(f"Extracting OCR text from {source_path}")
            ocr_text = await ocr_service.extract_text(str(source_path))

            if not ocr_text:
                logger.warning(f"No OCR text extracted from {source_path}")
                ocr_text = ""

            # Step 2: Classify document
            logger.info(f"Classifying document from {source_name}")
            classification = classifier.classify(ocr_text)
            category = classification.get('category', 'Unknown')
            confidence = classification.get('confidence', 0.0)

            # Step 3: Extract metadata
            logger.info(f"Extracting metadata from {source_path}")
            metadata = metadata_extractor.extract_metadata(ocr_text)

            # Step 4: Generate new filename
            original_filename = source_path.name
            new_filename = self.generate_filename(
                source=source_name,
                category=category,
                original_filename=original_filename
            )

            # Step 5: Copy to daily folder
            target_path = daily_folder / new_filename

            # Check if auto_rename is enabled
            auto_rename = source_config.get('auto_rename', True)

            if auto_rename:
                # Copy with new filename
                shutil.copy2(source_path, target_path)
                logger.info(f"Copied {source_path} to {target_path}")
            else:
                # Copy with original filename
                target_path = daily_folder / original_filename
                shutil.copy2(source_path, target_path)
                logger.info(f"Copied {source_path} to {target_path} (original name)")

            # Check if we should preserve original
            preserve_original = source_config.get('preserve_original', True)
            if not preserve_original:
                # Delete original file
                try:
                    source_path.unlink()
                    logger.info(f"Deleted original file: {source_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete original file: {e}")

            # Step 6: Create database record
            # CRITICAL: Status is always "pending_review" - NO AUTO-APPROVE
            document = Document(
                original_filename=original_filename,
                stored_filename=new_filename,
                storage_key=str(target_path.relative_to(settings.ORGANIZED_ROOT)),
                file_hash=metadata_extractor.compute_file_hash(str(target_path)),
                file_size=target_path.stat().st_size,
                mime_type="application/pdf",
                ocr_text=ocr_text,
                category=category,
                confidence=confidence,
                suggested_folder=f"Social_Media/{daily_folder.name}",
                status="pending_review",  # CRITICAL: Always pending review
                uploaded_by=uploaded_by,
                source=source_name,  # Track where it came from
                source_metadata={
                    "original_path": str(source_path),
                    "downloaded_at": datetime.utcnow().isoformat(),
                    "source_config": source_config
                },
                daily_folder=daily_folder.name,  # YYYY-MM-DD
                is_daily_archived=True  # Mark as archived to daily folder
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            logger.info(f"Successfully processed social media file: {new_filename}")
            logger.info(f"Document ID: {document.id}, Status: pending_review, Source: {source_name}")

            return document

        except Exception as e:
            logger.error(f"Failed to process social media file {source_path}: {e}")
            db.rollback()
            return None

    async def process_batch_social_files(
        self,
        file_paths: List[Path],
        source_name: str,
        uploaded_by: int,
        db: Session
    ) -> List[Document]:
        """
        Process multiple social media files in batch.

        Args:
            file_paths: List of file paths to process
            source_name: Name of the source
            uploaded_by: User ID
            db: Database session

        Returns:
            List of created Document records
        """
        results = []
        for file_path in file_paths:
            try:
                document = await self.process_social_file(file_path, source_name, uploaded_by, db)
                if document:
                    results.append(document)
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")
                continue

        logger.info(f"Processed {len(results)}/{len(file_paths)} files from {source_name}")
        return results

    def get_source_stats(self, db: Session, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for social media documents.

        Args:
            db: Database session
            source_name: Optional filter by source name

        Returns:
            Dictionary with statistics
        """
        query = db.query(Document).filter(
            Document.source.isnot(None),
            Document.is_daily_archived == True
        )

        if source_name:
            query = query.filter(Document.source == source_name)

        total = query.count()
        pending = query.filter(Document.status == "pending_review").count()
        approved = query.filter(Document.status == "approved").count()
        rejected = query.filter(Document.status == "rejected").count()

        # Get documents by source
        by_source = {}
        for source in ["Viber", "WhatsApp", "Facebook", "Telegram"]:
            count = db.query(Document).filter(
                Document.source == source,
                Document.is_daily_archived == True
            ).count()
            if count > 0:
                by_source[source] = count

        # Get documents by date
        by_date = {}
        recent_docs = query.order_by(Document.created_at.desc()).limit(30).all()
        for doc in recent_docs:
            if doc.daily_folder:
                by_date[doc.daily_folder] = by_date.get(doc.daily_folder, 0) + 1

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "by_source": by_source,
            "by_date": by_date
        }

    def get_documents_by_date(self, db: Session, date_str: str) -> List[Document]:
        """
        Get all social media documents for a specific date.

        Args:
            db: Database session
            date_str: Date string in YYYY-MM-DD format

        Returns:
            List of Document records
        """
        documents = db.query(Document).filter(
            Document.source.isnot(None),
            Document.is_daily_archived == True,
            Document.daily_folder == date_str
        ).order_by(Document.created_at.desc()).all()

        return documents

    def get_pending_by_source(self, db: Session, source_name: Optional[str] = None) -> List[Document]:
        """
        Get pending review documents by source.

        Args:
            db: Database session
            source_name: Optional filter by source name

        Returns:
            List of pending Document records
        """
        query = db.query(Document).filter(
            Document.source.isnot(None),
            Document.is_daily_archived == True,
            Document.status == "pending_review"
        )

        if source_name:
            query = query.filter(Document.source == source_name)

        documents = query.order_by(Document.created_at.desc()).all()

        return documents


# Global instance
social_ingestor = SocialMediaIngestor()