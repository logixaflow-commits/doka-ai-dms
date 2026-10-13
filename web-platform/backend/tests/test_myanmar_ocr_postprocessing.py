import unicodedata

from app.services.myanmar_ocr import MyanmarOCRService


def test_post_process_preserves_english_identifiers_and_myanmar_numerals():
    service = MyanmarOCRService.__new__(MyanmarOCRService)

    assert service._post_process_myanmar("ID: I1l\n၁") == "ID: I1l\n၁"


def test_post_process_normalizes_unicode_and_removes_control_artifacts():
    service = MyanmarOCRService.__new__(MyanmarOCRService)
    decomposed = unicodedata.normalize("NFD", "မြန်မာစာ")

    assert service._post_process_myanmar(decomposed + "\x0c\n") == unicodedata.normalize("NFC", decomposed)



def test_myanmar_ocr_fallback_uses_original_image_after_preprocessing():
    from types import SimpleNamespace
    from unittest.mock import patch

    service = MyanmarOCRService.__new__(MyanmarOCRService)
    service.is_available = True
    service.tesseract_path = "tesseract"
    service._preprocess_image = lambda _path: "document_processed.png"
    fallback_paths = []
    service._fallback_ocr = lambda path: fallback_paths.append(path) or {"success": True, "text": "fallback"}

    with (
        patch("app.core.performance.CacheManager", return_value=SimpleNamespace(get=lambda *_: None, set=lambda *_: False)),
        patch("app.services.myanmar_ocr.subprocess.run", return_value=SimpleNamespace(returncode=1, stderr="ocr failed", stdout="")),
    ):
        result = service.extract_text_myanmar("document.png", preprocess=True)

    assert result["text"] == "fallback"
    assert fallback_paths == ["document.png"]
