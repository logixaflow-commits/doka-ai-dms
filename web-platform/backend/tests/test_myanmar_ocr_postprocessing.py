import unicodedata

from app.services.myanmar_ocr import MyanmarOCRService


def test_post_process_preserves_english_identifiers_and_myanmar_numerals():
    service = MyanmarOCRService.__new__(MyanmarOCRService)

    assert service._post_process_myanmar("ID: I1l\n၁") == "ID: I1l\n၁"


def test_post_process_normalizes_unicode_and_removes_control_artifacts():
    service = MyanmarOCRService.__new__(MyanmarOCRService)
    decomposed = unicodedata.normalize("NFD", "မြန်မာစာ")

    assert service._post_process_myanmar(decomposed + "\x0c\n") == unicodedata.normalize("NFC", decomposed)
