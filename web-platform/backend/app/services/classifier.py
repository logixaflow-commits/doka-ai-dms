"""
Office DMS - Document Classifier
Hybrid classification using keyword matching with TF-IDF fallback.
Supports: Invoice, BL, NRC, FDA, License, Household, Customs, Certificate, etc.
"""

import re
from typing import Dict, List, Optional, Tuple
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentClassifier:
    """
    Hybrid document classifier with two strategies:
    1. Keyword-based: Fast, exact keyword matching with configurable weights
    2. TF-IDF fallback: Vector similarity when keyword matching is ambiguous
    """

    def __init__(self):
        self.keyword_mapping = settings.keyword_mapping
        self.folder_mapping = settings.folder_mapping
        self.thresholds = settings.thresholds
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.category_labels: List[str] = []
        self._build_tfidf_model()
        logger.info(
            f"Classifier initialized: {len(self.keyword_mapping)} keyword categories"
        )

    def _build_tfidf_model(self):
        """Build TF-IDF model from keyword descriptions as training data."""
        corpus = []
        labels = []

        for key, config in self.keyword_mapping.items():
            # Create synthetic documents from keywords
            keyword_text = " ".join(config.keywords)
            # Augment with repeated keywords for weight
            weighted_text = " ".join([kw for kw in config.keywords for _ in range(3)])
            corpus.append(f"{keyword_text} {weighted_text}")
            labels.append(config.category)

        if corpus:
            self.tfidf_vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=500,
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(corpus)
            self.category_labels = labels
            logger.debug(f"TF-IDF model built with {len(corpus)} training documents")

    def classify(
        self, text: str, extracted_metadata: Optional[Dict] = None
    ) -> Tuple[str, float, str]:
        """
        Classify document text into a category.

        Returns:
            Tuple of (category, confidence, method)
        """
        if not text or not text.strip():
            return "Unknown", 0.0, "none"

        text_lower = text.lower()

        # Strategy 1: Keyword matching (primary)
        keyword_scores = self._keyword_classify(text_lower)

        if not keyword_scores:
            return "Unknown", 0.1, "none"

        best_category = max(keyword_scores, key=keyword_scores.get)
        best_score = keyword_scores[best_category]

        if best_score < max(self.thresholds.unknown, 0.6):
            return "Unknown", 0.0, "keyword"

        # Strategy 2: TF-IDF fallback (if keyword results are ambiguous)
        if self.tfidf_vectorizer and len(keyword_scores) > 1:
            max_kw_score = best_score
            if max_kw_score < 0.5:  # Ambiguous keyword match
                tfidf_category, tfidf_score = self._tfidf_classify(text_lower)
                if tfidf_score > max_kw_score:
                    # Blend scores
                    blended_category = self._blend_scores(
                        keyword_scores, tfidf_category, tfidf_score
                    )
                    confidence = tfidf_score * 0.7 + max_kw_score * 0.3
                    return blended_category, min(confidence, 0.95), "tfidf+keyword"

        # Determine confidence level
        if best_score >= self.thresholds.approved:
            confidence = best_score
        elif best_score >= self.thresholds.review:
            confidence = best_score * 0.85
        elif best_score >= self.thresholds.unknown:
            confidence = best_score * 0.7
        else:
            return "Unknown", 0.0, "keyword"

        return best_category, min(confidence, 0.98), "keyword"

        # No match at all
        return "Unknown", 0.1, "none"

    def _keyword_classify(self, text: str) -> Dict[str, float]:
        """
        Score each category based on keyword occurrences.
        Returns: {category: score}
        """
        scores = Counter()
        text_words = set(re.findall(r"\b\w+\b", text))

        for key, config in self.keyword_mapping.items():
            category = config.category
            boost = config.confidence_boost

            for keyword in config.keywords:
                keyword_lower = keyword.lower()
                # Full phrase match (higher weight)
                if keyword_lower in text:
                    scores[category] += boost * 2.0
                # Word boundary match
                elif keyword_lower in text_words:
                    scores[category] += boost * 1.0
                # Partial match (lower weight)
                elif any(
                    kw_part in text
                    for kw_part in keyword_lower.split()
                    if len(kw_part) > 3
                ):
                    scores[category] += boost * 0.5

        return dict(scores)

    def _tfidf_classify(self, text: str) -> Tuple[str, float]:
        """
        Classify using TF-IDF cosine similarity.
        Returns: (category, score)
        """
        if not self.tfidf_vectorizer:
            return "Unknown", 0.0

        try:
            text_vector = self.tfidf_vectorizer.transform([text])
            similarities = cosine_similarity(text_vector, self.tfidf_matrix)[0]

            best_idx = np.argmax(similarities)
            best_score = float(similarities[best_idx])
            best_category = self.category_labels[best_idx]

            return best_category, best_score
        except Exception as e:
            logger.warning(f"TF-IDF classification failed: {e}")
            return "Unknown", 0.0

    def _blend_scores(
        self, keyword_scores: Dict[str, float], tfidf_category: str, tfidf_score: float
    ) -> str:
        """Blend keyword and TF-IDF results."""
        # If TF-IDF category has some keyword support, use it
        if tfidf_category in keyword_scores and keyword_scores[tfidf_category] > 0:
            return tfidf_category
        # If TF-IDF score is strong, trust it
        if tfidf_score > 0.4:
            return tfidf_category
        # Otherwise use best keyword category
        return (
            max(keyword_scores, key=keyword_scores.get)
            if keyword_scores
            else tfidf_category
        )

    def suggest_folder(
        self, category: str, text: str = "", metadata: Optional[Dict] = None
    ) -> Tuple[str, float]:
        """
        Suggest organized folder path based on category and metadata.

        Returns:
            Tuple of (folder_path, confidence)
        """
        # Get base folder from category mapping
        base_folder = self.folder_mapping.get(category, "Other")

        # Check for supplier subfolder
        supplier = None
        if metadata and metadata.get("supplier"):
            supplier = settings.get_supplier_by_alias(metadata["supplier"])

        if not supplier and text:
            supplier = settings.get_supplier_by_alias(text)

        if supplier and base_folder in ["Import", "Export"]:
            # Place under supplier subfolder
            folder = f"{base_folder}/{supplier.folder}"
            return folder, 0.9

        return base_folder, 0.8

    def get_category_confidence_level(self, confidence: float) -> str:
        """Determine confidence level for UI display."""
        if confidence >= self.thresholds.approved:
            return "high"
        elif confidence >= self.thresholds.review:
            return "medium"
        elif confidence >= self.thresholds.unknown:
            return "low"
        return "unknown"

    def get_supported_categories(self) -> List[str]:
        """Return list of supported classification categories."""
        categories = set()
        for config in self.keyword_mapping.values():
            categories.add(config.category)
        return sorted(categories)

    def retrain(self):
        """Rebuild TF-IDF model (call after config changes)."""
        self._build_tfidf_model()
        logger.info("Classifier TF-IDF model retrained")


# Singleton
classifier = DocumentClassifier()
