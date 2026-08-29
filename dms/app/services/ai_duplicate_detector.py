"""
AI-Powered Duplicate Detection Service
Supports multiple AI providers: OpenAI, Gemini, Hugging Face, OpenRouter, Groq
"""
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.services.unified_ai_service import ai_service

logger = get_logger(__name__)

class AIDuplicateDetector:
    """AI-powered duplicate detection using multiple AI providers"""

    def __init__(self):
        self.enabled = settings.AI_ENHANCED_DUPLICATE_DETECTION
        self.classification_enabled = settings.AI_CLASSIFICATION_ENABLED

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
            provider = ai_service.get_available_providers()[0] if ai_service.get_available_providers() else None
            result = await ai_service.analyze_document(text, provider=provider)
            logger.info(f"AI classified document using {provider}")
            return result

        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {}

    def _calculate_similarity(self, doc1: Dict[str, Any], doc2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two documents using AI

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            Similarity score (0-1)
        """
        try:
            text1 = doc1.get("ocr_text", "")[:2000]  # Limit text length
            text2 = doc2.get("ocr_text", "")[:2000]
            
            if not text1 or not text2:
                return 0.0
            
            # Use OpenAI to compare documents
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a document similarity analyzer. Compare two documents and return a similarity score between 0 and 1. Return ONLY the number, no other text."
                    },
                    {
                        "role": "user", 
                        "content": f"Document 1:\n{text1}\n\nDocument 2:\n{text2}\n\nSimilarity score (0-1):"
                    }
                ],
                temperature=0,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            similarity = float(score_text)
            
            return min(max(similarity, 0.0), 1.0)  # Ensure between 0 and 1
            
        except Exception as e:
            logger.error(f"AI similarity calculation failed: {e}")
            return 0.0
    
    def classify_document(self, text: str) -> Dict[str, Any]:
        """
        Classify document using AI
        
        Args:
            text: Document text content
            
        Returns:
            Classification result with category and confidence
        """
        if not self.enabled or not self.api_key:
            return {"category": "unknown", "confidence": 0.0, "method": "local"}
        
        try:
            text = text[:3000]  # Limit text length
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a document classifier. Classify documents into these categories:
                        - Invoice
                        - Bill of Lading (BL)
                        - NRC (National Registration Card)
                        - FDA (Food and Drug Administration)
                        - License
                        - Contract
                        - Receipt
                        - Other
                        
                        Return JSON format: {"category": "category_name", "confidence": 0.95}"""
                    },
                    {
                        "role": "user",
                        "content": f"Classify this document:\n{text}"
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            result["method"] = "ai_openai"
            
            return result
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {"category": "unknown", "confidence": 0.0, "method": "local"}

# Global instance
ai_detector = AIDuplicateDetector()