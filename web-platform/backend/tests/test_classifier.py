"""
Office DMS - Classifier Tests
Tests for document classification logic.
"""

import pytest
from app.services.classifier import DocumentClassifier


class TestClassifier:
    @pytest.fixture
    def classifier(self):
        return DocumentClassifier()

    def test_invoice_classification(self, classifier):
        text = "This is a commercial invoice number INV-2024-001 for goods shipped"
        category, confidence, method = classifier.classify(text)
        assert category == "Invoices"
        assert confidence > 0.4

    def test_bl_classification(self, classifier):
        text = "Bill of Lading BL number MAEU1234567 shipped from Yangon"
        category, confidence, method = classifier.classify(text)
        assert category == "BL"
        assert confidence > 0.4

    def test_nrc_classification(self, classifier):
        text = "Myanmar citizen NRC card number ၁၂/ကကက(နိုင်)၀၁၂၃၄၅"
        category, confidence, method = classifier.classify(text)
        assert category == "NRC"

    def test_low_confidence_returns_unknown(self, classifier):
        text = "random text with no meaningful content about documents"
        category, confidence, method = classifier.classify(text)
        assert category == "Unknown"
        assert confidence < 0.4

    def test_empty_text(self, classifier):
        category, confidence, method = classifier.classify("")
        assert category == "Unknown"
        assert confidence == 0.0

    def test_folder_suggestion(self, classifier):
        folder, conf = classifier.suggest_folder("Invoices")
        assert folder == "Invoices"
        assert conf > 0


class TestDuplicateDetector:
    def test_hash_computation(self):
        from app.services.duplicate_detector import DuplicateDetector

        detector = DuplicateDetector()
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()
            hash1 = detector.compute_hash(f.name)
            hash2 = detector.compute_hash(f.name)
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex length
