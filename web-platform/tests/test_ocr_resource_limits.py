import importlib
from PIL import Image
import pytest

from app.core.exceptions import OCRError
ocr_module = importlib.import_module("app.services.ocr_service")


class FakePdf:
    def __init__(self, count):
        self.pages = [object() for _ in range(count)]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def make_service():
    service = object.__new__(ocr_module.OCRService)
    service.MAX_PDF_PAGES = 200
    service.dpi = 150
    service.timeout = 7
    service.preprocessing = False
    service.oem = 3
    service.psm = 6
    service.lang_string = "eng+mya"
    service._extract_pdf_text = lambda _path: ""
    service._clean_text = lambda value: value.strip()
    return service


def test_scanned_pdf_is_rendered_one_page_at_a_time_with_timeouts(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ocr_module.pdfplumber, "open", lambda _path: FakePdf(2))

    def fake_convert(_path, **kwargs):
        calls.append(kwargs)
        return [Image.new("RGB", (8, 8))]

    monkeypatch.setattr(ocr_module, "convert_from_path", fake_convert)
    monkeypatch.setattr(ocr_module.pytesseract, "image_to_string", lambda *_a, **_kw: "page text")
    result = make_service()._process_pdf(tmp_path / "scan.pdf")

    assert "Page 1" in result and "Page 2" in result
    assert [call["first_page"] for call in calls] == [1, 2]
    assert all(call["first_page"] == call["last_page"] for call in calls)
    assert all(call["thread_count"] == 1 and call["timeout"] == 7 for call in calls)


def test_pdf_page_limit_is_checked_before_rendering(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ocr_module.pdfplumber,
        "open",
        lambda _path: FakePdf(ocr_module.OCRService.MAX_PDF_PAGES + 1),
    )
    monkeypatch.setattr(
        ocr_module,
        "convert_from_path",
        lambda *_a, **_kw: pytest.fail("oversized PDF must not be rendered"),
    )

    with pytest.raises(OCRError, match="OCR limit"):
        make_service()._process_pdf(tmp_path / "oversized.pdf")



def test_oversized_image_is_rejected_before_opencv_decode(tmp_path, monkeypatch):
    class ImageHeader:
        size = (10_000, 10_000)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    service = make_service()
    service.fallback_enabled = False
    service.paddleocr_available = False
    service.easyocr_available = False
    monkeypatch.setattr(ocr_module.Image, "open", lambda _path: ImageHeader())
    monkeypatch.setattr(
        ocr_module.cv2,
        "imread",
        lambda *_args: pytest.fail("oversized image must be rejected before decoding"),
    )

    with pytest.raises(OCRError, match="dimensions exceed"):
        service._process_image(tmp_path / "oversized.png")
