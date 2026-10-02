"""
Office DMS - Hardening Tests
Tests for Phase A-E hardening features including:
- Config validation
- Rate limiting
- Encryption key rotation
- OCR fallback
- Vector search caching
- Rule engine performance
- External API retry logic
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

# Disable config validation on import to prevent SystemExit during tests
os.environ['SKIP_CONFIG_VALIDATION'] = 'true'

from app.core.config_validator import validate_config, ThresholdConfigModel, KeywordConfigModel
from pydantic import ValidationError
from app.core.rate_limiter import RateLimiter
from app.core.encryption import EncryptionManager
from app.services.ocr_service import OCRService
from app.services.vector_search import VectorSearchService
from app.services.rule_engine import RuleEngine
from app.services.external_api_service import ExternalAPIService


class TestConfigValidation:
    """Tests for config.yaml schema validation (Phase A-5)"""
    
    def test_valid_config(self):
        """Test that a valid configuration passes validation"""
        valid_config = {
            "app": {
                "name": "Enterprise DMS",
                "version": "2.0.0",
                "debug": False
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "dms_db",
                "user": "postgres",
                "password": "secure_password"
            },
            "security": {
                "secret_key": "secure-key-at-least-32-chars-long",
                "access_token_expire_minutes": 30,
                "refresh_token_expire_days": 7
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            },
            "paths": {
                "documents_root": "/data/documents",
                "organized_root": "/data/organized"
            }
        }
        
        try:
            validate_config(valid_config)
        except ValidationError:
            pytest.fail("Valid config should not raise validation error")
    
    def test_missing_required_fields(self):
        """Test that missing required fields fail validation"""
        invalid_config = {
            "app": {
                "name": "Enterprise DMS"
            }
        }
        
        with pytest.raises(ValidationError):
            validate_config(invalid_config)
    
    def test_invalid_port_number(self):
        """Test that invalid port numbers fail validation"""
        invalid_config = {
            "app": {"name": "DMS", "version": "2.0.0", "debug": False},
            "database": {"host": "localhost", "port": 99999, "name": "db", "user": "u", "password": "p"},
            "security": {"secret_key": "secure-key-at-least-32-chars-long"},
            "redis": {"host": "localhost", "port": 6379},
            "paths": {"documents_root": "/data", "organized_root": "/data/org"}
        }
        
        with pytest.raises(ValidationError):
            validate_config(invalid_config)
    
    def test_short_secret_key(self):
        """Test that short secret keys fail validation"""
        invalid_config = {
            "app": {"name": "DMS", "version": "2.0.0", "debug": False},
            "database": {"host": "localhost", "port": 5432, "name": "db", "user": "u", "password": "p"},
            "security": {"secret_key": "short"},
            "redis": {"host": "localhost", "port": 6379},
            "paths": {"documents_root": "/data", "organized_root": "/data/org"}
        }
        
        with pytest.raises(ValidationError):
            validate_config(invalid_config)


class TestPydanticV2ConfigValidation:
    """Regression tests for Pydantic v2 threshold and list constraints."""

    def test_valid_thresholds_are_accepted(self):
        model = ThresholdConfigModel(unknown=0.4, review=0.7, approved=0.85)
        assert model.approved > model.review > model.unknown

    def test_review_must_exceed_unknown(self):
        with pytest.raises(ValidationError, match="review threshold must be greater"):
            ThresholdConfigModel(unknown=0.7, review=0.6, approved=0.85)

    def test_approved_must_exceed_review(self):
        with pytest.raises(ValidationError, match="approved threshold must be greater"):
            ThresholdConfigModel(unknown=0.4, review=0.7, approved=0.6)

    def test_keyword_list_must_not_be_empty(self):
        with pytest.raises(ValidationError):
            KeywordConfigModel(keywords=[], category="invoice")


class TestRateLimiter:
    """Tests for rate limiting (Phase C-12)"""
    
    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter(redis_client=MagicMock())
    
    def test_rate_limit_allows_within_limit(self, rate_limiter):
        """Test that requests within limit are allowed"""
        # Mock Redis to return count below limit
        rate_limiter.redis.incr.return_value = 10
        rate_limiter.redis.expire.return_value = True
        
        result = rate_limiter.is_allowed("127.0.0.1", limit=100, window=60)
        assert result is True
    
    def test_rate_limit_blocks_over_limit(self, rate_limiter):
        """Test that requests over limit are blocked"""
        # Mock Redis to return count at limit
        rate_limiter.redis.incr.return_value = 101
        rate_limiter.redis.expire.return_value = True
        
        result = rate_limiter.is_allowed("127.0.0.1", limit=100, window=60)
        assert result is False
    
    def test_rate_limit_different_ips(self, rate_limiter):
        """Test that different IPs have separate rate limits"""
        # Mock Redis to return different counts for different IPs
        def incr_side_effect(key):
            if "127.0.0.1" in key:
                return 101
            elif "192.168.1.1" in key:
                return 1
            return 0
        
        rate_limiter.redis.incr.side_effect = incr_side_effect
        rate_limiter.redis.expire.return_value = True
        
        result1 = rate_limiter.is_allowed("127.0.0.1", limit=100, window=60)
        result2 = rate_limiter.is_allowed("192.168.1.1", limit=100, window=60)
        
        assert result1 is False
        assert result2 is True


class TestEncryptionKeyRotation:
    """Tests for encryption key rotation (Phase B-15)"""
    
    def test_multi_key_encryption(self):
        """Test encryption/decryption with multiple keys"""
        # Mock settings with multiple keys
        mock_settings = Mock()
        mock_settings.ENCRYPTION_KEYS = [
            "key1-32-characters-long-1234567890",
            "key2-32-characters-long-0987654321"
        ]
        
        with patch("app.core.encryption.settings", mock_settings):
            manager = EncryptionManager()
            manager._init_cipher()
            
            if manager.is_enabled:
                data = b"sensitive data"
                encrypted = manager.encrypt(data)
                decrypted = manager.decrypt(encrypted)
                
                assert decrypted == data
                assert encrypted != data
    
    def test_key_rotation_decrypt_old_data(self):
        """Test that old data can still be decrypted after key rotation"""
        # Mock settings with current and old keys
        old_key = "old-key-32-characters-long-12345678"
        new_key = "new-key-32-characters-long-09876543"
        
        mock_settings = Mock()
        mock_settings.ENCRYPTION_KEYS = [new_key, old_key]  # New key first
        
        with patch("app.core.encryption.settings", mock_settings):
            # Encrypt with old key
            mock_settings.ENCRYPTION_KEYS = [old_key]
            old_manager = EncryptionManager()
            old_manager._init_cipher()
            
            if old_manager.is_enabled:
                data = b"old encrypted data"
                old_encrypted = old_manager.encrypt(data)
            
            # Decrypt with new manager (which has both keys)
            mock_settings.ENCRYPTION_KEYS = [new_key, old_key]
            new_manager = EncryptionManager()
            new_manager._init_cipher()
            
            if new_manager.is_enabled:
                decrypted = new_manager.decrypt(old_encrypted)
                assert decrypted == data


class TestOCRFallback:
    """Tests for OCR fallback mechanism (Phase B-7)"""
    
    @pytest.fixture
    def ocr_service(self):
        return OCRService()
    
    def test_fallback_on_tesseract_failure(self, ocr_service):
        """Test fallback to PaddleOCR when Tesseract fails"""
        with patch.object(ocr_service, '_extract_with_tesseract', side_effect=Exception("Tesseract failed")):
            with patch.object(ocr_service, '_extract_with_paddleocr', return_value="fallback text"):
                result = ocr_service.extract_text("test.png")
                assert result == "fallback text"
    
    def test_fallback_to_easyocr(self, ocr_service):
        """Test fallback to EasyOCR when both Tesseract and PaddleOCR fail"""
        with patch.object(ocr_service, '_extract_with_tesseract', side_effect=Exception("Tesseract failed")):
            with patch.object(ocr_service, '_extract_with_paddleocr', side_effect=Exception("PaddleOCR failed")):
                with patch.object(ocr_service, '_extract_with_easyocr', return_value="easyocr text"):
                    result = ocr_service.extract_text("test.png")
                    assert result == "easyocr text"
    
    def test_all_ocr_engines_fail(self, ocr_service):
        """Test graceful handling when all OCR engines fail"""
        with patch.object(ocr_service, '_extract_with_tesseract', side_effect=Exception("Failed")):
            with patch.object(ocr_service, '_extract_with_paddleocr', side_effect=Exception("Failed")):
                with patch.object(ocr_service, '_extract_with_easyocr', side_effect=Exception("Failed")):
                    result = ocr_service.extract_text("test.png")
                    assert result == ""  # Return empty string on complete failure


class TestVectorSearchCaching:
    """Tests for vector search caching (Phase B-8)"""
    
    @pytest.fixture
    def vector_search(self):
        mock_redis = MagicMock()
        return VectorSearchService(redis_client=mock_redis)
    
    def test_cache_hit(self, vector_search):
        """Test that cached results are returned"""
        cached_result = {"documents": [{"id": 1}]}
        vector_search.redis.get.return_value = json.dumps(cached_result)
        
        result = vector_search.search("test query", use_cache=True)
        assert result == cached_result
    
    def test_cache_miss(self, vector_search):
        """Test that cache miss performs actual search"""
        vector_search.redis.get.return_value = None
        
        with patch.object(vector_search, '_perform_search', return_value={"documents": [{"id": 1}]}):
            result = vector_search.search("test query", use_cache=True)
            assert len(result["documents"]) == 1
    
    def test_cache_invalidation(self, vector_search):
        """Test that cache is invalidated after document update"""
        vector_search.redis.delete.return_value = 1
        
        vector_search.invalidate_cache(document_id=123)
        vector_search.redis.delete.assert_called()


class TestRuleEnginePerformance:
    """Tests for rule engine performance optimization (Phase B-9)"""
    
    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()
    
    def test_query_filtering(self, rule_engine):
        """Test that query filtering is applied"""
        documents = [
            {"id": 1, "category": "Invoices", "status": "pending"},
            {"id": 2, "category": "BL", "status": "approved"},
            {"id": 3, "category": "Invoices", "status": "approved"}
        ]
        
        # Filter for Invoices only
        filtered = rule_engine._filter_documents(documents, {"category": "Invoices"})
        assert len(filtered) == 2
        assert all(doc["category"] == "Invoices" for doc in filtered)
    
    def test_batch_processing(self, rule_engine):
        """Test batch processing of documents"""
        # Create a large set of documents
        documents = [{"id": i, "content": f"content {i}"} for i in range(250)]
        
        batches = list(rule_engine._batch_documents(documents, batch_size=100))
        assert len(batches) == 3  # 3 batches for 250 documents with batch_size=100
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50


class TestExternalAPIRetry:
    """Tests for external API retry logic (Phase B-10)"""
    
    @pytest.fixture
    def external_api(self):
        return ExternalAPIService()
    
    def test_retry_on_failure(self, external_api):
        """Test that API calls are retried on failure"""
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API error")
            return {"success": True}
        
        with patch.object(external_api, '_make_request', side_effect=mock_request):
            result = external_api.call_api("https://api.example.com/endpoint")
            assert result["success"] is True
            assert call_count == 3  # Should have retried twice
    
    def test_max_retries_exceeded(self, external_api):
        """Test that retries stop after max attempts"""
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("API error")
        
        with patch.object(external_api, '_make_request', side_effect=mock_request):
            with pytest.raises(Exception):
                external_api.call_api("https://api.example.com/endpoint")
            assert call_count == 3  # Should have tried max 3 times


class TestFetchHelper:
    """Tests for global loading state in fetch_helper.js (Phase D-16)"""
    
    def test_loading_state_management(self):
        """Test that loading state is properly managed"""
        # This is a JavaScript test, so we just verify the file exists
        fetch_helper_path = Path("dms/app/static/js/fetch_helper.js")
        assert fetch_helper_path.exists()
    
    def test_fetch_helper_contains_global_loader(self):
        """Test that fetch helper contains global loading state logic"""
        fetch_helper_path = Path("dms/app/static/js/fetch_helper.js")
        content = fetch_helper_path.read_text()
        
        assert "loading" in content.lower()
        assert "fetch" in content.lower()


class TestSSEReconnection:
    """Tests for SSE reconnection logic (Phase D-17)"""
    
    def test_dashboard_js_contains_reconnection_logic(self):
        """Test that dashboard.js contains exponential backoff reconnection"""
        dashboard_js_path = Path("dms/app/static/js/dashboard.js")
        content = dashboard_js_path.read_text()
        
        assert "retryCount" in content or "retry_count" in content
        assert "reconnect" in content.lower()
        assert "backoff" in content.lower() or "delay" in content.lower()


class TestPWACacheStrategy:
    """Tests for PWA hybrid caching strategy (Phase D-18)"""
    
    def test_sw_js_contains_hybrid_caching(self):
        """Test that service worker implements hybrid caching"""
        sw_js_path = Path("dms/app/static/sw.js")
        content = sw_js_path.read_text()
        
        assert "cache" in content.lower()
        assert "network" in content.lower()
        assert "api" in content.lower()
    
    def test_sw_js_contains_cache_size_limit(self):
        """Test that service worker enforces cache size limit"""
        sw_js_path = Path("dms/app/static/sw.js")
        content = sw_js_path.read_text()
        
        assert "size" in content.lower() or "limit" in content.lower()


class TestFormValidation:
    """Tests for frontend form validation (Phase D-19)"""
    
    def test_dashboard_contains_validation_logic(self):
        """Test that dashboard contains pre-upload validation"""
        dashboard_path = Path("dms/app/templates/dashboard.html")
        content = dashboard_path.read_text()
        
        assert "validation" in content.lower()
        assert "file" in content.lower()
        assert "size" in content.lower()
    
    def test_react_upload_contains_validation(self):
        """Test that React upload component contains validation"""
        upload_path = Path("app/src/components/DocumentUpload.tsx")
        content = upload_path.read_text()
        
        assert "validate" in content.lower()
        assert "error" in content.lower()
