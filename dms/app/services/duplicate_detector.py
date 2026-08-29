"""
Office DMS - Duplicate Detector
Three-stage detection: SHA-256 exact match + TF-IDF cosine similarity + AI-powered detection.
"""
import hashlib
from typing import Optional, Tuple, List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database import Document
from sqlalchemy.orm import Session

logger = get_logger(__name__)

# Import AI detector if available
try:
    from app.services.ai_duplicate_detector import ai_detector
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("AI duplicate detector not available")


class DuplicateDetector:
    """
    Detects exact and near-duplicate documents.
    Stage 1: SHA-256 hash comparison (exact duplicates)
    Stage 2: TF-IDF cosine similarity (near-duplicates)
    Stage 3: AI-powered detection (optional, enhanced similarity)
    """

    def __init__(self):
        self.config = settings.duplicate
        self.similarity_threshold = self.config.similarity_threshold
        self.near_duplicate_threshold = self.config.near_duplicate_threshold
        self.recent_docs_limit = self.config.recent_docs_limit
        self.min_text_length = self.config.min_text_length
        self.use_ai = AI_AVAILABLE and ai_detector.enabled

    def compute_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file contents."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compute_hash_bytes(self, data: bytes) -> str:
        """Compute SHA-256 hash of bytes."""
        return hashlib.sha256(data).hexdigest()

    def check_exact_duplicate(self, db: Session, file_hash: str) -> Optional[Document]:
        """
        Check if a document with the same hash already exists.
        Returns the existing document if found.
        """
        existing = db.query(Document).filter(
            Document.file_hash == file_hash,
            Document.is_duplicate == False,
            Document.status.notin_(["rejected", "failed"]),
        ).first()

        if existing:
            logger.info(f"Exact duplicate detected: {existing.id} (hash: {file_hash[:16]}...)")

        return existing

    def _check_with_ai(self, ocr_text: str, candidates: List[Document]) -> Tuple[Optional[Document], float]:
        """
        Check for duplicates using AI-powered detection.
        Returns: (existing_document, similarity_score)
        """
        if not AI_AVAILABLE or not ai_detector.enabled:
            return None, 0.0
            
        try:
            # Prepare documents for AI
            docs_data = []
            for doc in candidates:
                docs_data.append({
                    "id": doc.id,
                    "ocr_text": doc.ocr_text or ""
                })
            
            # Add new document
            new_doc = {"id": 0, "ocr_text": ocr_text}
            docs_data.append(new_doc)
            
            # Detect duplicates with AI
            ai_duplicates = ai_detector.detect_duplicates(docs_data, threshold=self.near_duplicate_threshold)
            
            if ai_duplicates:
                # Find the best match
                best_match = max(ai_duplicates, key=lambda x: x["similarity"])
                matched_doc_id = best_match["doc2_id"]  # Since new_doc has id=0
                
                # Find the actual document
                for doc in candidates:
                    if doc.id == matched_doc_id:
                        similarity = best_match["similarity"]
                        logger.info(f"AI-detected duplicate: new_doc vs {doc.id} (similarity: {similarity:.3f})")
                        return doc, similarity
                        
            return None, 0.0
            
        except Exception as e:
            logger.warning(f"AI duplicate check failed: {e}")
            return None, 0.0

    def check_near_duplicate(
        self,
        db: Session,
        ocr_text: str,
        exclude_id: Optional[int] = None,
    ) -> Tuple[Optional[Document], float]:
        """
        Check for near-duplicate documents using TF-IDF cosine similarity.
        Returns: (existing_document, similarity_score)
        """
        if not ocr_text or len(ocr_text.strip()) < self.min_text_length:
            return None, 0.0

        # Get recent documents with OCR text
        query = db.query(Document).filter(
            Document.ocr_text.isnot(None),
            Document.is_duplicate == False,
            Document.status.notin_(["rejected", "failed"]),
        ).order_by(Document.created_at.desc()).limit(self.recent_docs_limit)

        if exclude_id:
            query = query.filter(Document.id != exclude_id)

        candidates = query.all()

        if not candidates:
            return None, 0.0

        # Try AI-powered detection first if enabled
        if self.use_ai:
            try:
                ai_result = self._check_with_ai(ocr_text, candidates)
                if ai_result[0] is not None:
                    return ai_result
            except Exception as e:
                logger.warning(f"AI detection failed, falling back to local: {e}")

        # Prepare corpus
        corpus = [ocr_text]
        for doc in candidates:
            corpus.append(doc.ocr_text or "")

        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=1000,
                min_df=1,
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)

            # Compare first document (new) with all candidates
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])

            if best_score >= self.near_duplicate_threshold:
                matched_doc = candidates[best_idx]
                level = "exact" if best_score >= 0.95 else "near"
                logger.info(
                    f"{level.capitalize()}-duplicate detected: new_doc vs "
                    f"{matched_doc.id} (similarity: {best_score:.3f})"
                )
                return matched_doc, best_score

            return None, best_score

        except Exception as e:
            logger.warning(f"Near-duplicate detection failed: {e}")
            return None, 0.0

    def detect(
        self,
        db: Session,
        file_hash: str,
        ocr_text: str,
        exclude_id: Optional[int] = None,
    ) -> dict:
        """
        Full duplicate detection pipeline.
        Checks exact hash match first, then near-duplicate similarity.

        Returns:
            {
                "is_duplicate": bool,
                "duplicate_type": str or None,  # "exact", "near"
                "duplicate_of_id": int or None,
                "similarity": float,
                "message": str,
            }
        """
        result = {
            "is_duplicate": False,
            "duplicate_type": None,
            "duplicate_of_id": None,
            "similarity": 0.0,
            "message": "No duplicate detected",
        }

        # Stage 1: Exact hash match
        exact_match = self.check_exact_duplicate(db, file_hash)
        if exact_match:
            result.update({
                "is_duplicate": True,
                "duplicate_type": "exact",
                "duplicate_of_id": exact_match.id,
                "similarity": 1.0,
                "message": f"Exact duplicate of document {exact_match.id} ({exact_match.original_filename})",
            })
            return result

        # Stage 2: Near-duplicate check
        if ocr_text and len(ocr_text.strip()) >= self.min_text_length:
            near_match, similarity = self.check_near_duplicate(db, ocr_text, exclude_id)

            if near_match and similarity >= self.similarity_threshold:
                result.update({
                    "is_duplicate": True,
                    "duplicate_type": "near",
                    "duplicate_of_id": near_match.id,
                    "similarity": similarity,
                    "message": (
                        f"Near-duplicate of document {near_match.id} "
                        f"({near_match.original_filename}, similarity: {similarity:.1%})"
                    ),
                })
            elif near_match and similarity >= self.near_duplicate_threshold:
                # Suspiciously similar but below strict threshold
                result.update({
                    "is_duplicate": False,
                    "duplicate_type": "suspicious_similarity",
                    "duplicate_of_id": near_match.id,
                    "similarity": similarity,
                    "message": (
                        f"Suspicious similarity ({similarity:.1%}) with "
                        f"document {near_match.id} ({near_match.original_filename})"
                    ),
                })

        return result


def quick_hash_check(db: Session, file_hash: str) -> Optional[int]:
    """Quick check if hash exists. Returns document ID or None."""
    doc = db.query(Document).filter(
        Document.file_hash == file_hash,
    ).first()
    return doc.id if doc else None


# Singleton
duplicate_detector = DuplicateDetector()
