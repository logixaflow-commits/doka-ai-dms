"""
Unit Tests for Enterprise AI DMS
Comprehensive unit tests for core services and functionality
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.database import User, Document, AuditLog
from app.services.function_detection import (
    FunctionDetectionService,
    FractureDetectionService,
    DocumentFunction,
    DocumentQuality
)
from app.services.document_versioning import DocumentVersioningService
from app.services.advanced_search import AdvancedSearchService
from app.services.rate_limiting import RateLimitingService


class TestFunctionDetectionService:
    """Test cases for Function Detection Service"""
    
    @pytest.fixture
    def function_service(self):
        """Create function detection service instance"""
        return FunctionDetectionService()
    
    def test_initialization(self, function_service):
        """Test service initialization"""
        assert function_service is not None
        assert len(function_service.function_keywords) > 0
        assert len(function_service.function_patterns) > 0
    
    def test_detect_function_invoice(self, function_service):
        """Test invoice detection"""
        text = "Invoice No: INV-001 Total: $5000 Due Date: 2025-03-15"
        result = function_service.detect_function(text)
        
        assert result.primary_function == DocumentFunction.INVOICE
        assert result.confidence > 0.5
        assert len(result.detected_keywords) > 0
    
    def test_detect_function_bill_of_lading(self, function_service):
        """Test bill of lading detection"""
        text = "Bill of Lading No: MAEU1234567 Vessel: OCEAN PRINCESS Port of Loading: Singapore"
        result = function_service.detect_function(text)
        
        assert result.primary_function == DocumentFunction.BILL_OF_LADING
        assert result.confidence > 0.5
    
    def test_detect_function_unknown(self, function_service):
        """Test unknown document detection"""
        text = "Random text with no specific keywords"
        result = function_service.detect_function(text)
        
        assert result.primary_function == DocumentFunction.UNKNOWN
        assert result.confidence < 0.5
    
    def test_detect_function_empty_text(self, function_service):
        """Test empty text handling"""
        result = function_service.detect_function("")
        
        assert result.primary_function == DocumentFunction.UNKNOWN
        assert result.confidence == 0.0


class TestFractureDetectionService:
    """Test cases for Fracture Detection Service"""
    
    @pytest.fixture
    def fracture_service(self):
        """Create fracture detection service instance"""
        return FractureDetectionService()
    
    def test_initialization(self, fracture_service):
        """Test service initialization"""
        assert fracture_service is not None
        assert len(fracture_service.damage_keywords) > 0
        assert len(fracture_service.quality_indicators) > 0
    
    def test_detect_fracture(self, fracture_service):
        """Test fracture detection"""
        text = "Document has fracture on page 3, cracked edges"
        result = fracture_service.detect_fracture(text)
        
        assert result.damage_detected == True
        assert result.damage_type == "fracture"
        assert result.damage_severity in ["low", "medium", "high", "critical"]
    
    def test_detect_quality_excellent(self, fracture_service):
        """Test excellent quality detection"""
        text = "Document is clear, sharp, and readable. Excellent quality."
        result = fracture_service.detect_fracture(text)
        
        assert result.quality_level == DocumentQuality.EXCELLENT
        assert result.damage_detected == False
    
    def test_detect_quality_poor(self, fracture_service):
        """Test poor quality detection"""
        text = "Document is blurry, faded, and difficult to read. Poor quality."
        result = fracture_service.detect_fracture(text)
        
        assert result.quality_level == DocumentQuality.POOR
        assert result.has_damage == True
    
    def test_detect_fracture_empty_text(self, fracture_service):
        """Test empty text handling"""
        result = fracture_service.detect_fracture("")
        
        assert result.quality_level == DocumentQuality.UNKNOWN
        assert result.confidence == 0.0
    
    def test_recommended_actions_generation(self, fracture_service):
        """Test recommended actions generation"""
        text = "Document has fracture"
        result = fracture_service.detect_fracture(text)
        
        assert len(result.recommended_actions) > 0
        assert any("replace" in action.lower() for action in result.recommended_actions)


class TestDocumentVersioningService:
    """Test cases for Document Versioning Service"""
    
    @pytest.fixture
    def versioning_service(self, tmp_path):
        """Create versioning service with temp directory"""
        service = DocumentVersioningService()
        service.versions_storage_path = tmp_path / "versions"
        service.versions_storage_path.mkdir(parents=True, exist_ok=True)
        return service
    
    def test_create_version(self, versioning_service, tmp_path):
        """Test version creation"""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        version = versioning_service.create_version(
            document_id=1,
            file_path=str(test_file),
            user_id=1,
            comment="Test version"
        )
        
        assert version is not None
        assert version.version_number == 1
        assert version.comment == "Test version"
        assert version.created_by == 1
    
    def test_get_document_versions(self, versioning_service, tmp_path):
        """Test getting document versions"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        # Create multiple versions
        versioning_service.create_version(1, str(test_file), 1, "Version 1")
        versioning_service.create_version(1, str(test_file), 1, "Version 2")
        
        versions = versioning_service.get_document_versions(1)
        
        assert len(versions) == 2
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
    
    def test_rollback_to_version(self, versioning_service, tmp_path):
        """Test rollback to previous version"""
        # Create test files
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text("Version 1 content")
        
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("Version 2 content")
        
        current_file = tmp_path / "current.txt"
        current_file.write_text("Current content")
        
        # Create versions
        version1 = versioning_service.create_version(1, str(test_file1), 1, "Version 1")
        version2 = versioning_service.create_version(1, str(test_file2), 1, "Version 2")
        
        # Rollback to version 1
        result = versioning_service.rollback_to_version(
            document_id=1,
            version_id=version1.id,
            current_file_path=str(current_file),
            user_id=1
        )
        
        assert result["success"] == True
        assert current_file.read_text() == "Version 1 content"
    
    def test_compare_versions(self, versioning_service, tmp_path):
        """Test version comparison"""
        # Create test files
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text("Version 1 content")
        
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("Version 2 content")
        
        # Create versions
        version1 = versioning_service.create_version(1, str(test_file1), 1, "Version 1")
        version2 = versioning_service.create_version(1, str(test_file2), 1, "Version 2")
        
        # Compare versions
        result = versioning_service.compare_versions(1, version1.id, version2.id)
        
        assert result["success"] == True
        assert result["files_identical"] == False
        assert "version_1" in result
        assert "version_2" in result


class TestAdvancedSearchService:
    """Test cases for Advanced Search Service"""
    
    @pytest.fixture
    def search_service(self):
        """Create advanced search service instance"""
        return AdvancedSearchService()
    
    def test_initialization(self, search_service):
        """Test service initialization"""
        assert search_service is not None
        assert search_service.embedding_available is not None
        assert search_service.vector_available is not None
    
    def test_keyword_search(self, search_service):
        """Test keyword search"""
        from app.services.advanced_search import SearchQuery
        
        query = SearchQuery(
            query="invoice",
            filters={"category": "Invoice"},
            semantic=False,
            natural_language=False
        )
        
        result = search_service.search_documents(query, limit=10)
        
        assert result["success"] == True
        assert "results" in result
        assert "method" in result
    
    def test_natural_language_search(self, search_service):
        """Test natural language search"""
        from app.services.advanced_search import SearchQuery
        
        query = SearchQuery(
            query="find all invoices approved today",
            filters={},
            semantic=False,
            natural_language=True
        )
        
        result = search_service.search_documents(query, limit=10)
        
        assert result["success"] == True
        assert "results" in result
    
    def test_search_suggestions(self, search_service):
        """Test search suggestions"""
        suggestions = search_service.get_search_suggestions("inv", limit=5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
    
    def test_relevance_calculation(self, search_service):
        """Test relevance score calculation"""
        # Create mock document
        mock_doc = Mock()
        mock_doc.original_filename = "invoice_001.pdf"
        mock_doc.category = "Invoice"
        mock_doc.ocr_text = "Invoice for goods and services"
        mock_doc.function_type = "invoice"
        
        score = search_service._calculate_relevance(mock_doc, "invoice")
        
        assert 0 <= score <= 1
        assert score > 0.5  # Should have high relevance


class TestRateLimitingService:
    """Test cases for Rate Limiting Service"""
    
    @pytest.fixture
    def rate_limit_service(self, tmp_path):
        """Create rate limiting service with temp directory"""
        service = RateLimitingService()
        service.rules_storage_path = tmp_path / "rules"
        service.rules_storage_path.mkdir(parents=True, exist_ok=True)
        service.usage_storage_path = tmp_path / "usage"
        service.usage_storage_path.mkdir(parents=True, exist_ok=True)
        service.quotas_storage_path = tmp_path / "quotas"
        service.quotas_storage_path.mkdir(parents=True, exist_ok=True)
        return service
    
    def test_initialization(self, rate_limit_service):
        """Test service initialization"""
        assert rate_limit_service is not None
        assert len(rate_limit_service.request_cache) == 0
    
    def test_check_rate_limit_allowed(self, rate_limit_service):
        """Test rate limit check - allowed"""
        result = rate_limit_service.check_rate_limit(
            user_id=1,
            user_role="staff",
            endpoint="/api/documents"
        )
        
        assert result["allowed"] == True
    
    def test_check_rate_limit_exceeded(self, rate_limit_service):
        """Test rate limit check - exceeded"""
        # Add many requests to exceed limit
        for _ in range(100):
            rate_limit_service.check_rate_limit(1, "staff", "/api/documents")
        
        result = rate_limit_service.check_rate_limit(1, "staff", "/api/documents")
        
        # Should eventually be limited
        if not result["allowed"]:
            assert "error" in result
            assert "reset" in result
    
    def test_track_api_usage(self, rate_limit_service):
        """Test API usage tracking"""
        rate_limit_service.track_api_usage(
            user_id=1,
            endpoint="/api/documents",
            status_code=200,
            response_time_ms=150.5
        )
        
        # Verify usage was tracked
        usage = rate_limit_service.get_user_usage_stats(1)
        
        assert usage["success"] == True
        assert usage["total_requests"] >= 1
    
    def test_set_user_quota(self, rate_limit_service):
        """Test setting user quota"""
        quota = rate_limit_service.set_user_quota(
            user_id=1,
            daily_requests=1000,
            daily_storage_mb=100,
            monthly_requests=30000,
            monthly_storage_mb=3000
        )
        
        assert quota is not None
        assert quota.daily_requests == 1000
        assert quota.user_id == 1
    
    def test_check_user_quota(self, rate_limit_service):
        """Test checking user quota"""
        # Set quota
        rate_limit_service.set_user_quota(1, 100, 10, 3000, 300)
        
        result = rate_limit_service.check_user_quota(1)
        
        assert result["allowed"] == True
        assert "quota" in result


class TestDatabaseModels:
    """Test cases for Database Models"""
    
    def test_user_model_creation(self):
        """Test User model creation"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role="staff"
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "staff"
        assert user.is_active == True
    
    def test_document_model_creation(self):
        """Test Document model creation"""
        doc = Document(
            original_filename="test.pdf",
            stored_filename="stored_test.pdf",
            storage_key="test_key",
            file_hash="abc123",
            file_size=1024,
            mime_type="application/pdf",
            status="pending",
            uploaded_by=1
        )
        
        assert doc.original_filename == "test.pdf"
        assert doc.status == "pending"
        assert doc.is_duplicate == False
    
    def test_document_with_advanced_fields(self):
        """Test Document model with advanced fields"""
        doc = Document(
            original_filename="test.pdf",
            stored_filename="stored_test.pdf",
            storage_key="test_key",
            file_hash="abc123",
            file_size=1024,
            mime_type="application/pdf",
            status="pending",
            uploaded_by=1,
            function_type="invoice",
            function_confidence=0.95,
            quality_level="excellent",
            has_damage=False,
            damage_type=None,
            damage_severity=None
        )
        
        assert doc.function_type == "invoice"
        assert doc.function_confidence == 0.95
        assert doc.quality_level == "excellent"
        assert doc.has_damage == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])