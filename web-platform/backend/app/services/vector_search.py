"""
Vector Search Service - Semantic search using embeddings
Uses sentence-transformers for document similarity search.
"""
from typing import List, Dict, Optional, Tuple
from loguru import logger
import numpy as np
import hashlib
import json
import os
import unicodedata
import re

from app.services.train1_safety_contracts import RetrievalDocument, validate_retrieval_documents

# sentence-transformers is optional and loaded lazily so importing the service
# never downloads a model or performs network I/O.
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None
model = None


# Try to import Redis for caching
try:
    import redis
    REDIS_AVAILABLE = True
    try:
        redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        redis_client.ping()
        logger.info("Redis connected for vector search caching")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
        REDIS_AVAILABLE = False
        redis_client = None
except ImportError:
    logger.warning("Redis not installed. Using in-memory cache.")
    REDIS_AVAILABLE = False
    redis_client = None


class VectorSearchService:
    """Service for semantic document search using vector embeddings."""

    def __init__(self):
        self.model = model
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        self.cache_enabled = True
        self.cache_ttl = int(os.getenv('VECTOR_CACHE_TTL', '3600'))  # Default 1 hour
        self.redis_client = redis_client
        self.embedding_cache = {}  # Fallback in-memory cache
        
        logger.info(f"Vector Search Service: cache_enabled={self.cache_enabled}, cache_ttl={self.cache_ttl}s, redis={'enabled' if REDIS_AVAILABLE else 'disabled'}")

    def _get_cache_key(self, text: str, suffix: str = "embed") -> str:
        """Generate cache key for text."""
        text_hash = hashlib.sha256(self._normalize_text(text)[:500].encode("utf-8")).hexdigest()
        return f"vector_search:{suffix}:{text_hash}"

    def _get_cache(self, cache_key: str) -> Optional[List[float]]:
        """Get value from cache (Redis or in-memory)."""
        if not self.cache_enabled:
            return None
            
        # Try Redis first
        if REDIS_AVAILABLE and self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
        
        # Fallback to in-memory cache
        return self.embedding_cache.get(cache_key)

    def _set_cache(self, cache_key: str, value: List[float]):
        """Set value in cache (Redis or in-memory)."""
        if not self.cache_enabled:
            return
            
        # Try Redis first
        if REDIS_AVAILABLE and self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(value)
                )
                return
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
        
        # Fallback to in-memory cache
        self.embedding_cache[cache_key] = value

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize OCR text to canonical Unicode NFC."""
        if not isinstance(text, str):
            return ""
        return unicodedata.normalize("NFC", text).replace("\u200b", " ").strip()

    @staticmethod
    def _detect_language(text: str) -> str:
        """Classify the dominant supported OCR script as mya or eng."""
        normalized = VectorSearchService._normalize_text(text)
        mya = sum(
            1 for char in normalized
            if "\u1000" <= char <= "\u109f"
            or "\ua9e0" <= char <= "\ua9ff"
            or "\uaa60" <= char <= "\ua9ff"
            or "\u116d0" <= char <= "\u116ff"
        )
        latin = sum(1 for char in normalized.casefold() if "a" <= char <= "z")
        return "mya" if mya and mya >= max(1, latin) else "eng"

    @staticmethod
    def _retrieval_identity(doc: Dict, text: str) -> RetrievalDocument:
        document_id = str(doc.get("id") or doc.get("document_id") or "").strip()
        language = str(doc.get("language") or VectorSearchService._detect_language(text)).strip().lower()
        digest = hashlib.sha256(VectorSearchService._normalize_text(text).encode("utf-8")).hexdigest()
        return RetrievalDocument(document_id=document_id, language=language, text_hash=digest)

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate vector embedding from text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (embedding vector) or None if unavailable
        """
        text = self._normalize_text(text)
        if not text or not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
        if self.model is None:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as exc:
                logger.warning("Failed to load semantic retrieval model: %s", exc)
                return None

        # Check cache
        cache_key = self._get_cache_key(text, "embed")
        cached_value = self._get_cache(cache_key)
        if cached_value:
            logger.debug(f"Cache hit for embedding: {text[:50]}...")
            return cached_value

        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Convert to list for JSON serialization
            embedding_list = embedding.tolist()
            
            # Cache result
            self._set_cache(cache_key, embedding_list)
            
            return embedding_list

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts at once.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts or not SENTENCE_TRANSFORMERS_AVAILABLE or not self.model:
            return [None] * len(texts)

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() if emb is not None else None for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))

        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            return 0.0

    def search_similar(
        self,
        query_vector: List[float],
        document_vectors: List[Tuple[int, List[float]]],
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Tuple[int, float]]:
        """
        Find semantically similar documents with result caching.
        
        Args:
            query_vector: Query embedding vector
            document_vectors: List of (document_id, embedding) tuples
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of (document_id, similarity_score) tuples, sorted by similarity
        """
        if not query_vector or not document_vectors:
            return []

        # Generate cache key for search results
        doc_ids = str(sorted([doc_id for doc_id, _ in document_vectors]))
        query_hash = hashlib.sha256(json.dumps(query_vector, separators=(",", ":")).encode("utf-8")).hexdigest()
        cache_key = f"vector_search:result:{query_hash}:{limit}:{threshold}:{doc_ids}"
        
        # Check cache
        cached_results = self._get_cache(cache_key)
        if cached_results:
            logger.debug("Cache hit for vector search results")
            return cached_results

        similarities = []
        
        for doc_id, doc_vector in document_vectors:
            if not doc_vector:
                continue
            
            similarity = self.compute_similarity(query_vector, doc_vector)
            
            if similarity >= threshold:
                similarities.append((doc_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        results = similarities[:limit]
        
        # Cache results
        self._set_cache(cache_key, results)
        
        return results

    def search_similar_text(
        self,
        query_text: str,
        documents: List[Dict],
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Tuple[Dict, float]]:
        """
        Search similar documents using text query.
        
        Args:
            query_text: Search query text
            documents: List of document dictionaries with 'id' and 'text' keys
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of (document, similarity_score) tuples
        """
        query_text = self._normalize_text(query_text)
        if not query_text or not documents:
            return []

        query_language = self._detect_language(query_text)
        eligible = []
        identities = []
        for doc in documents:
            text = self._normalize_text(doc.get("ocr_text", "") or doc.get("text", "") or doc.get("original_filename", ""))
            identities.append(self._retrieval_identity(doc, text))
            eligible.append((doc, text))
        validate_retrieval_documents(identities)
        eligible = [(doc, text) for doc, text in eligible if self._detect_language(text) == query_language]
        if not eligible:
            return []

        if query_language == "mya":
            query_terms = set(re.findall(r"\w+", query_text.casefold(), flags=re.UNICODE))
            scored = []
            for doc, text in eligible:
                terms = set(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))
                score = len(query_terms & terms) / len(query_terms | terms) if query_terms and terms else 0.0
                if score >= threshold:
                    scored.append((doc, score))
            scored.sort(key=lambda item: item[1], reverse=True)
            return scored[offset:offset + limit]

        documents = [doc for doc, _ in eligible]
        query_vector = self.generate_embedding(query_text)
        if not query_vector:
            return []

        # Prepare document vectors
        document_vectors = []
        for doc in documents:
            text_to_embed = self._normalize_text(doc.get("ocr_text", "") or doc.get("text", "") or doc.get("original_filename", ""))
            if text_to_embed:
                embedding = self.generate_embedding(text_to_embed)
                if embedding:
                    document_vectors.append((doc['id'], embedding))

        # Search
        similar_ids = self.search_similar(query_vector, document_vectors, limit, threshold)

        # Return full documents with similarity scores
        doc_map = {doc['id']: doc for doc in documents}
        results = []
        for doc_id, similarity in similar_ids:
            if doc_id in doc_map:
                results.append((doc_map[doc_id], similarity))

        return results

    def clear_cache(self):
        """Clear the embedding cache (both Redis and in-memory)."""
        # Clear in-memory cache
        self.embedding_cache.clear()
        
        # Clear Redis cache
        if REDIS_AVAILABLE and self.redis_client:
            try:
                # Clear all vector_search keys
                keys = self.redis_client.keys("vector_search:*")
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} Redis cache entries")
            except Exception as e:
                logger.warning(f"Failed to clear Redis cache: {e}")
        
        logger.info("Embedding cache cleared")

    def invalidate_document_cache(self, document_id: int):
        """
        Invalidate cache for a specific document when it's updated.
        
        Args:
            document_id: ID of the document that was updated
        """
        if not self.cache_enabled:
            return
            
        # In a real implementation, we would have a mapping of document_id to cache keys
        # For now, we clear all vector_search result caches
        if REDIS_AVAILABLE and self.redis_client:
            try:
                keys = self.redis_client.keys("vector_search:result:*")
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} search result caches for document {document_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate document cache: {e}")

    def get_cache_size(self) -> int:
        """Get current cache size."""
        # Return in-memory cache size
        size = len(self.embedding_cache)
        
        # Add Redis cache size if available
        if REDIS_AVAILABLE and self.redis_client:
            try:
                redis_keys = self.redis_client.keys("vector_search:*")
                size += len(redis_keys)
            except Exception:
                pass
        
        return size


# Global vector search service instance
vector_search_service = VectorSearchService()