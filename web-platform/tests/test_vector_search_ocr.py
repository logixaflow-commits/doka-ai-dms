"""OCR-aware retrieval safety tests."""
import pytest

from app.services.vector_search import VectorSearchService


def test_myanmar_language_detection_and_unicode_normalization():
    service = VectorSearchService()
    text = "မင်္ဂလာ\u200bပါ"
    assert service._detect_language(text) == "mya"
    assert "\u200b" not in service._normalize_text(text)


def test_english_language_detection():
    service = VectorSearchService()
    assert service._detect_language("Invoice number ABC-123") == "eng"


def test_myanmar_search_does_not_use_english_embedding_model():
    service = VectorSearchService()
    docs = [
        {"id": "mya-1", "ocr_text": "မင်္ဂလာပါ စာရွက်စာတမ်း"},
        {"id": "eng-1", "ocr_text": "hello document invoice"},
    ]
    result = service.search_similar_text("မင်္ဂလာပါ", docs, limit=10, threshold=0.1)
    assert [doc["id"] for doc, _ in result] == ["mya-1"]


def test_retrieval_rejects_unsupported_explicit_language():
    service = VectorSearchService()
    with pytest.raises(ValueError, match="Unsupported retrieval language"):
        service.search_similar_text(
            "hello",
            [{"id": "doc-1", "language": "fra", "ocr_text": "bonjour"}],
        )
