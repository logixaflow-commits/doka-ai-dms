"""
Office DMS - Processing Pipeline
6-step orchestrator: OCR -> Metadata Extraction -> Classification ->
Duplicate Detection -> Folder Suggestion -> Database Update
"""
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.encryption import encryption_manager
from app.core.storage import storage_manager
from app.core.exceptions import PipelineError
from app.services.ocr_service import ocr_service
from app.services.metadata_extractor import metadata_extractor
from app.services.classifier import classifier
from app.services.duplicate_detector import duplicate_detector
from app.models.database import Document

logger = get_logger(__name__)


class ProcessingPipeline:
    """
    Orchestrates the 6-step AI processing pipeline for each document.
    Each step is independent and failures are handled gracefully.
    """

    def __init__(self, db: Session):
        self.db = db
        self.step_times: Dict[str, float] = {}

    def process(
        self,
        document_id: int,
        file_path: str,
        original_filename: str,
        mime_type: str,
    ) -> Dict[str, Any]:
        """
        Run the full processing pipeline on a document.

        Args:
            document_id: Database ID of the document
            file_path: Path to the file in Processing_Workspace
            original_filename: Original filename
            mime_type: MIME type of the file

        Returns:
            Pipeline result dictionary
        """
        start_time = time.time()
        logger.info(f"Pipeline started for document {document_id}: {original_filename}")

        result = {
            "document_id": document_id,
            "status": "failed",
            "ocr_text": None,
            "category": None,
            "confidence": 0.0,
            "suggested_folder": None,
            "metadata": {},
            "is_duplicate": False,
            "duplicate_of_id": None,
            "is_suspicious": False,
            "suspicious_reason": None,
            "processing_time_ms": 0,
            "steps_completed": [],
        }

        try:
            # =====================================================================
            # Step 1: OCR Text Extraction
            # =====================================================================
            step_start = time.time()
            ocr_text, ocr_lang = self._step_ocr(file_path, mime_type)
            self.step_times["ocr"] = time.time() - step_start
            result["ocr_text"] = ocr_text
            result["steps_completed"].append("ocr")
            logger.info(f"Step 1 (OCR) complete: {len(ocr_text) if ocr_text else 0} chars, lang={ocr_lang}")

            # =====================================================================
            # Step 2: Metadata Extraction
            # =====================================================================
            step_start = time.time()
            metadata = self._step_metadata(ocr_text)
            self.step_times["metadata"] = time.time() - step_start
            result["metadata"] = metadata
            result["steps_completed"].append("metadata")
            logger.info(f"Step 2 (Metadata) complete: {list(metadata.keys()) if metadata else 'none'}")

            # =====================================================================
            # Step 3: Document Classification
            # =====================================================================
            step_start = time.time()
            category, confidence, method = self._step_classify(ocr_text, metadata)
            self.step_times["classification"] = time.time() - step_start
            result["category"] = category
            result["confidence"] = confidence
            result["steps_completed"].append("classification")
            logger.info(f"Step 3 (Classification) complete: {category} (confidence: {confidence:.3f}, method: {method})")

            # =====================================================================
            # Step 4: Duplicate Detection
            # =====================================================================
            step_start = time.time()
            dup_result = self._step_duplicate(document_id, file_path, ocr_text)
            self.step_times["duplicate"] = time.time() - step_start
            result["is_duplicate"] = dup_result["is_duplicate"]
            result["duplicate_of_id"] = dup_result.get("duplicate_of_id")
            result["steps_completed"].append("duplicate")
            logger.info(f"Step 4 (Duplicate) complete: is_duplicate={dup_result['is_duplicate']}")

            # =====================================================================
            # Step 5: Folder Suggestion
            # =====================================================================
            step_start = time.time()
            folder, folder_conf = self._step_folder_suggestion(category, ocr_text, metadata)
            self.step_times["folder"] = time.time() - step_start
            result["suggested_folder"] = folder
            result["steps_completed"].append("folder_suggestion")
            logger.info(f"Step 5 (Folder) complete: suggested={folder}")

            # =====================================================================
            # Step 6: Determine Final Status
            # =====================================================================
            status = self._step_determine_status(
                confidence=confidence,
                is_duplicate=result["is_duplicate"],
                category=category,
            )
            result["status"] = status
            result["steps_completed"].append("status_determination")

            # =====================================================================
            # Phase 4: Version Check (before database update)
            # =====================================================================
            try:
                from app.models.database import Document
                # Check if document with similar filename exists
                existing_doc = db.query(Document).filter(
                    Document.original_filename.ilike(f"%{original_filename}%"),
                    Document.id != document_id
                ).first()
                
                if existing_doc:
                    logger.info(f"Similar document found: {existing_doc.id} - {existing_doc.original_filename}")
                    logger.info(f"Consider using versioning via /api/documents/{document_id}/versions")
            except Exception as e:
                logger.warning(f"Version check failed: {e}")

            # =====================================================================
            # Step 7: Update Database (optional - encrypt sensitive docs)
            # =====================================================================
            step_start = time.time()
            self._step_update_database(
                document_id=document_id,
                ocr_text=ocr_text,
                ocr_language=ocr_lang,
                category=category,
                confidence=confidence,
                suggested_folder=folder,
                metadata=metadata,
                dup_result=dup_result,
                status=status,
            )
            self.step_times["database"] = time.time() - step_start
            result["steps_completed"].append("database_update")

            # =====================================================================
            # Phase 3: Step 8 - AI Tagging
            # =====================================================================
            try:
                from app.services.ai_tagging_service import ai_tagging_service
                
                step_start = time.time()
                ai_metadata = ai_tagging_service.extract_document_metadata(ocr_text)
                
                # Update result with AI metadata
                result["tags"] = ai_metadata['tags']
                result["urgency"] = ai_metadata['urgency']
                result["customs_code"] = ai_metadata['customs_code']
                result["entities"] = ai_metadata['entities']
                
                self.step_times["ai_tagging"] = time.time() - step_start
                result["steps_completed"].append("ai_tagging")
                logger.info(f"Step 8 (AI Tagging) complete: {len(result['tags'])} tags, urgency={result['urgency']}")
                
            except Exception as e:
                logger.warning(f"AI Tagging step failed: {e}. Continuing without tags.")
                result["tags"] = []
                result["urgency"] = "normal"

            # =====================================================================
            # Phase 3: Step 9 - Rule Processing
            # =====================================================================
            try:
                from app.services.rule_manager_service import rule_manager_service
                
                step_start = time.time()
                
                # Prepare document data for rule evaluation
                doc_data = {
                    "id": document_id,
                    "category": category,
                    "confidence": confidence,
                    "urgency": result.get("urgency", "normal"),
                    "status": status,
                    "filename": original_filename,
                    **metadata
                }
                
                # Process against rules
                rule_result = rule_manager_service.process_document(doc_data)
                
                result["rule_matches"] = rule_result['matched_rules']
                result["rule_execution"] = rule_result['execution_results']
                
                self.step_times["rule_processing"] = time.time() - step_start
                result["steps_completed"].append("rule_processing")
                logger.info(f"Step 9 (Rule Processing) complete: {len(rule_result['matched_rules'])} rules matched")
                
            except Exception as e:
                logger.warning(f"Rule processing step failed: {e}. Continuing without rules.")
                result["rule_matches"] = []
                result["rule_execution"] = []

            result["processing_time_ms"] = int((time.time() - start_time) * 1000)

            logger.info(
                f"Pipeline completed for document {document_id}: "
                f"status={status}, category={category}, "
                f"time={result['processing_time_ms']}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Pipeline failed for document {document_id}: {e}")
            result["status"] = "failed"
            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            self._step_update_database(
                document_id=document_id,
                status="failed",
                error=str(e),
            )
            raise PipelineError(f"Processing pipeline failed: {e}") from e

    def _step_ocr(self, file_path: str, mime_type: str) -> tuple:
        """Step 1: Extract text via OCR."""
        try:
            text, lang = ocr_service.process_file(file_path, mime_type)
            return text or "", lang
        except Exception as e:
            logger.warning(f"OCR step failed: {e}. Continuing with empty text.")
            return "", None

    def _step_metadata(self, ocr_text: str) -> Dict[str, Any]:
        """Step 2: Extract structured metadata from OCR text."""
        if not ocr_text:
            return {}
        try:
            return metadata_extractor.extract(ocr_text)
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            return {}

    def _step_classify(self, ocr_text: str, metadata: Dict) -> tuple:
        """Step 3: Classify document category."""
        if not ocr_text:
            return "Unknown", 0.0, "none"
        try:
            return classifier.classify(ocr_text, metadata)
        except Exception as e:
            logger.warning(f"Classification failed: {e}")
            return "Unknown", 0.0, "error"

    def _step_duplicate(self, document_id: int, file_path: str, ocr_text: str) -> dict:
        """Step 4: Check for duplicates."""
        try:
            file_hash = duplicate_detector.compute_hash(file_path)

            # Update file hash in DB
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.file_hash = file_hash
                self.db.commit()

            return duplicate_detector.detect(
                db=self.db,
                file_hash=file_hash,
                ocr_text=ocr_text,
                exclude_id=document_id,
            )
        except Exception as e:
            logger.warning(f"Duplicate detection failed: {e}")
            return {"is_duplicate": False, "duplicate_type": None, "similarity": 0.0}

    def _step_folder_suggestion(self, category: str, ocr_text: str, metadata: Dict) -> tuple:
        """Step 5: Suggest organized folder."""
        try:
            return classifier.suggest_folder(category, ocr_text, metadata)
        except Exception as e:
            logger.warning(f"Folder suggestion failed: {e}")
            return "Other", 0.0

    def _step_determine_status(self, confidence: float, is_duplicate: bool, category: str) -> str:
        """Step 6: Determine final document status based on confidence and duplicates."""
        if is_duplicate:
            return "duplicate"

        if confidence < settings.thresholds.unknown:
            return "unknown"
        elif confidence < settings.thresholds.review:
            return "review"
        else:
            return "completed"

    def _step_update_database(
        self,
        document_id: int,
        ocr_text: Optional[str] = None,
        ocr_language: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        suggested_folder: Optional[str] = None,
        metadata: Optional[Dict] = None,
        dup_result: Optional[Dict] = None,
        status: str = "pending",
        error: Optional[str] = None,
    ):
        """Step 7: Persist all results to database."""
        try:
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Document {document_id} not found for update")
                return

            if ocr_text is not None:
                doc.ocr_text = ocr_text[:50000] if ocr_text else None  # Limit size
                doc.ocr_language = ocr_language

            if category is not None:
                doc.category = category
                doc.confidence = confidence
                doc.classification_method = "pipeline"

            if suggested_folder is not None:
                doc.suggested_folder = suggested_folder

            if metadata is not None:
                doc.extracted_metadata = metadata

            if dup_result is not None:
                doc.is_duplicate = dup_result.get("is_duplicate", False)
                doc.duplicate_of_id = dup_result.get("duplicate_of_id")
                doc.duplicate_similarity = dup_result.get("similarity")

            if error:
                meta = doc.extracted_metadata or {}
                meta["processing_error"] = error
                doc.extracted_metadata = meta

            # Phase 3: Update AI tagging fields (if not already set)
            if not doc.tags and category and confidence:
                try:
                    from app.services.ai_tagging_service import ai_tagging_service
                    ai_metadata = ai_tagging_service.extract_document_metadata(ocr_text)
                    doc.tags = ai_metadata.get('tags', [])
                    doc.urgency = ai_metadata.get('urgency', 'normal')
                    doc.customs_code = ai_metadata.get('customs_code')
                except Exception as e:
                    logger.warning(f"AI tagging failed during update: {e}")

            doc.status = status
            doc.updated_at = datetime.utcnow()

            self.db.commit()
            logger.debug(f"Document {document_id} updated with status={status}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Database update failed for document {document_id}: {e}")
