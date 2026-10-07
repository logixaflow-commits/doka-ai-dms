"""
AI-Powered Duplicate Detection Service
Uses the shared capability-based provider router for AI classification and local-first embeddings
"""
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.services.unified_ai_service import ai_service

logger = get_logger(__name__)

class AIDuplicateDetector:
    """AI-powered duplicate detection using multiple AI providers"""

    def __init__(self):
        self.enabled = settings.AI_ENABLED and settings.AI_ENHANCED_DUPLICATE_DETECTION
        self.classification_enabled = settings.AI_ENABLED and settings.AI_CLASSIFICATION_ENABLED

        if self.enabled:
            available_providers = ai_service.get_available_providers()
            if available_providers:
                logger.info(f"AI Duplicate Detector initialized with providers: {available_providers}")
            else:
                logger.warning("No AI providers available, AI detection disabled")
                self.enabled = False
        else:
            logger.info("AI Duplicate Detection disabled")
    
    async def detect_duplicates(
        self,
        documents: List[Dict[str, Any]],
        threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Detect duplicate documents using AI

        Args:
            documents: List of documents with text content
            threshold: Similarity threshold (0-1)

        Returns:
            List of duplicate pairs with similarity scores
        """
        if not self.enabled:
            logger.info("AI detection not enabled, falling back to local methods")
            return []

        try:
            duplicates = []
            provider = ai_service.get_available_providers()[0] if ai_service.get_available_providers() else None

            for i, doc1 in enumerate(documents):
                for j, doc2 in enumerate(documents[i+1:], i+1):
                    similarity = await ai_service.compare_similarity(
                        doc1.get("text", ""),
                        doc2.get("text", "")
                    )

                    if similarity >= threshold:
                        duplicates.append({
                            "doc1_id": doc1.get("id"),
                            "doc2_id": doc2.get("id"),
                            "similarity": similarity,
                            "method": f"ai_{provider}"
                        })

            logger.info(f"AI detected {len(duplicates)} duplicate pairs")
            return duplicates

        except Exception as e:
            logger.error(f"AI duplicate detection failed: {e}")
            return []

    async def classify_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify document using AI

        Args:
            text: Document text
            metadata: Optional metadata

        Returns:
            Classification result with category, confidence, etc.
        """
        if not self.classification_enabled:
            logger.info("AI classification not enabled")
            return {}

        try:
            result = await ai_service.analyze_document(text)
            logger.info("AI classified document using the configured classification chain")
            return result

        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {}


# Global instance
ai_detector = AIDuplicateDetector()