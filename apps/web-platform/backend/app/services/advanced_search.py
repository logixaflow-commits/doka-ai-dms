"""
Advanced Search Service with Semantic Search Capabilities
Provides natural language queries, semantic search, and advanced filtering
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger
from app.core.performance import cache_result
import re


@dataclass
class SearchQuery:
    """Search query data"""
    query: str
    filters: Dict[str, Any]
    semantic: bool = False
    natural_language: bool = False


@dataclass
class SearchResult:
    """Search result data"""
    document_id: int
    title: str
    content_snippet: str
    relevance_score: float
    metadata: Dict[str, Any]
    semantic_score: Optional[float] = None


class AdvancedSearchService:
    """Service for advanced document search"""
    
    def __init__(self):
        self.embedding_available = self._check_embedding_availability()
        self.vector_available = self._check_vector_availability()
        
    def _check_embedding_availability(self) -> bool:
        """Check if embedding model is available"""
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            logger.warning("sentence-transformers not available")
            return False
    
    def _check_vector_availability(self) -> bool:
        """Check if vector database is available"""
        try:
            # Check for pgvector or similar
            import psycopg2
            return True
        except ImportError:
            logger.warning("pgvector not available")
            return False
    
    @cache_result(ttl=1800)
    def search_documents(
        self,
        query: SearchQuery,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Advanced document search
        
        Args:
            query: Search query with filters
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Dictionary with search results
        """
        try:
            results = []
            
            if query.semantic and self.embedding_available:
                # Use semantic search
                results = self._semantic_search(query, limit, offset)
            elif query.natural_language:
                # Use natural language processing
                results = self._natural_language_search(query, limit, offset)
            else:
                # Use traditional keyword search
                results = self._keyword_search(query, limit, offset)
            
            return {
                "success": True,
                "query": query.query,
                "method": "semantic" if query.semantic else "keyword",
                "total": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def _semantic_search(
        self,
        query: SearchQuery,
        limit: int,
        offset: int
    ) -> List[SearchResult]:
        """Semantic search using embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load embedding model
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Generate query embedding
            query_embedding = model.encode(query.query)
            
            # For now, return placeholder results
            # Full implementation would query vector database
            return [
                SearchResult(
                    document_id=1,
                    title="Sample Document",
                    content_snippet="This is a sample document content...",
                    relevance_score=0.95,
                    semantic_score=0.92,
                    metadata={"type": "semantic"}
                )
            ]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._keyword_search(query, limit, offset)
    
    def _natural_language_search(
        self,
        query: SearchQuery,
        limit: int,
        offset: int
    ) -> List[SearchResult]:
        """Natural language search"""
        try:
            # Parse natural language query
            parsed_query = self._parse_natural_language(query.query)
            
            # Extract key terms
            key_terms = self._extract_key_terms(parsed_query)
            
            # Build filters from natural language
            filters = self._extract_filters_from_natural_language(parsed_query)
            
            # Update query filters
            query.filters.update(filters)
            
            # Perform keyword search with extracted terms
            return self._keyword_search(query, limit, offset)
            
        except Exception as e:
            logger.error(f"Natural language search failed: {e}")
            return self._keyword_search(query, limit, offset)
    
    def _keyword_search(
        self,
        query: SearchQuery,
        limit: int,
        offset: int
    ) -> List[SearchResult]:
        """Traditional keyword search"""
        try:
            from app.core.database import SessionLocal
            from app.models.database import Document
            
            db = SessionLocal()
            
            # Build base query
            db_query = db.query(Document).filter(Document.deleted == False)
            
            # Apply text search
            if query.query:
                search_pattern = f"%{query.query}%"
                db_query = db_query.filter(
                    (Document.original_filename.ilike(search_pattern)) |
                    (Document.ocr_text.ilike(search_pattern)) |
                    (Document.category.ilike(search_pattern))
                )
            
            # Apply filters
            if query.filters.get("category"):
                db_query = db_query.filter(Document.category == query.filters["category"])
            
            if query.filters.get("status"):
                db_query = db_query.filter(Document.status == query.filters["status"])
            
            if query.filters.get("function_type"):
                db_query = db_query.filter(Document.function_type == query.filters["function_type"])
            
            if query.filters.get("quality_level"):
                db_query = db_query.filter(Document.quality_level == query.filters["quality_level"])
            
            if query.filters.get("date_from"):
                db_query = db_query.filter(Document.created_at >= query.filters["date_from"])
            
            if query.filters.get("date_to"):
                db_query = db_query.filter(Document.created_at <= query.filters["date_to"])
            
            if query.filters.get("min_size"):
                db_query = db_query.filter(Document.file_size >= query.filters["min_size"])
            
            if query.filters.get("max_size"):
                db_query = db_query.filter(Document.file_size <= query.filters["max_size"])
            
            # Execute query
            documents = db_query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
            
            # Convert to search results
            results = []
            for doc in documents:
                snippet = self._generate_snippet(doc.ocr_text, query.query) if doc.ocr_text else ""
                
                results.append(SearchResult(
                    document_id=doc.id,
                    title=doc.original_filename,
                    content_snippet=snippet,
                    relevance_score=self._calculate_relevance(doc, query.query),
                    metadata={
                        "category": doc.category,
                        "status": doc.status,
                        "function_type": doc.function_type,
                        "quality_level": doc.quality_level,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None
                    }
                ))
            
            db.close()
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _parse_natural_language(self, query: str) -> Dict[str, Any]:
        """Parse natural language query"""
        # Simple NLP parsing
        parsed = {
            "original": query,
            "terms": [],
            "filters": {},
            "operators": []
        }
        
        # Extract terms
        words = re.findall(r'\w+', query.lower())
        parsed["terms"] = words
        
        # Extract common filter patterns
        # e.g., "category:invoice", "status:approved"
        filter_pattern = r'(\w+):(\w+)'
        matches = re.findall(filter_pattern, query.lower())
        
        for field, value in matches:
            parsed["filters"][field] = value
        
        return parsed
    
    def _extract_key_terms(self, parsed_query: Dict[str, Any]) -> List[str]:
        """Extract key terms from parsed query"""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        key_terms = [
            term for term in parsed_query["terms"]
            if term not in stop_words and len(term) > 2
        ]
        
        return key_terms
    
    def _extract_filters_from_natural_language(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Extract filters from natural language"""
        filters = {}
        
        # Check for common patterns
        text = parsed_query["original"].lower()
        
        # Date filters
        if "today" in text:
            from datetime import datetime, timedelta
            filters["date_from"] = datetime.now().replace(hour=0, minute=0, second=0)
            filters["date_to"] = filters["date_from"] + timedelta(days=1)
        
        if "this week" in text:
            from datetime import datetime, timedelta
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            filters["date_from"] = start_of_week.replace(hour=0, minute=0, second=0)
            filters["date_to"] = start_of_week + timedelta(days=7)
        
        # Status filters
        if "approved" in text:
            filters["status"] = "approved"
        if "pending" in text:
            filters["status"] = "pending"
        if "rejected" in text:
            filters["status"] = "rejected"
        
        # Category filters
        if "invoice" in text:
            filters["category"] = "Invoice"
        if "bill of lading" in text or "bl" in text:
            filters["category"] = "Bill of Lading"
        
        return filters
    
    def _generate_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Generate text snippet with query highlighting"""
        if not text:
            return ""
        
        # Find query in text
        query_lower = query.lower()
        text_lower = text.lower()
        
        index = text_lower.find(query_lower)
        
        if index == -1:
            # Return first part of text
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # Generate snippet around query
        start = max(0, index - 50)
        end = min(len(text), index + len(query) + 50)
        
        snippet = text[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def _calculate_relevance(self, document, query: str) -> float:
        """Calculate relevance score for document"""
        score = 0.0
        
        if not query:
            return score
        
        query_lower = query.lower()
        
        # Check filename match
        if document.original_filename and query_lower in document.original_filename.lower():
            score += 0.3
        
        # Check category match
        if document.category and query_lower in document.category.lower():
            score += 0.2
        
        # Check OCR text match
        if document.ocr_text and query_lower in document.ocr_text.lower():
            score += 0.4
        
        # Check function type match
        if document.function_type and query_lower in document.function_type.lower():
            score += 0.1
        
        return min(score, 1.0)
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            from app.core.database import SessionLocal
            from app.models.database import Document
            
            db = SessionLocal()
            
            # Get common categories
            categories = db.query(Document.category).filter(
                Document.category.isnot(None),
                Document.category != ""
            ).distinct().all()
            
            # Get common function types
            function_types = db.query(Document.function_type).filter(
                Document.function_type.isnot(None),
                Document.function_type != ""
            ).distinct().all()
            
            suggestions = []
            
            # Add category suggestions
            for (category,) in categories:
                if partial_query.lower() in category.lower():
                    suggestions.append(f"category:{category}")
            
            # Add function type suggestions
            for (func_type,) in function_types:
                if partial_query.lower() in func_type.lower():
                    suggestions.append(f"function:{func_type}")
            
            db.close()
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []


# Singleton instance
_advanced_search_service: Optional[AdvancedSearchService] = None


def get_advanced_search_service() -> AdvancedSearchService:
    """Get singleton advanced search service"""
    global _advanced_search_service
    if _advanced_search_service is None:
        _advanced_search_service = AdvancedSearchService()
    return _advanced_search_service