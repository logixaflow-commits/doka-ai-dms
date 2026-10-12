from pathlib import Path

import pytest
from PIL import Image

from app.services.ocr_service import OCRService
from app.core.config import settings
from app.core.exceptions import OCRError


def test_ocr_rejects_oversized_input(tmp_path: Path):
    service = OCRService.__new__(OCRService)
    service.max_file_bytes = 3
    service.SUPPORTED_IMAGE_TYPES = {"image/png"}
    service.SUPPORTED_PDF_TYPES = {"application/pdf"}

    source = tmp_path / "large.bin"
    source.write_bytes(b"1234")

    with pytest.raises(OCRError, match="configured limit"):
        service.process_file(str(source), "image/png")


def test_ocr_rejects_symlink_input(tmp_path: Path):
    service = OCRService.__new__(OCRService)
    service.SUPPORTED_IMAGE_TYPES = {"image/png"}
    service.SUPPORTED_PDF_TYPES = {"application/pdf"}
    service.max_file_bytes = 1024

    source = tmp_path / "source.png"
    source.write_bytes(b"x")
    link = tmp_path / "link.png"
    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")

    with pytest.raises(OCRError, match="symbolic-link"):
        service.process_file(str(link), "image/png")


def test_ocr_poppler_path_is_not_hard_coded():
    assert getattr(settings.ocr, "poppler_path", "") == settings.OCR_POPPLER_PATH


def test_ocr_timeout_is_configured_and_bounded():
    assert settings.ocr.timeout == settings.OCR_TIMEOUT_SECONDS
    assert 5 <= settings.ocr.timeout <= 120


def test_pdf_retries_without_preprocessing_when_page_has_no_text(monkeypatch: pytest.MonkeyPatch):
    class PdfPages:
        pages = [object()]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("app.services.ocr_service.pdfplumber.open", lambda _path: PdfPages())
    monkeypatch.setattr(
        "app.services.ocr_service.convert_from_path",
        lambda *_args, **_kwargs: [Image.new("RGB", (2, 2), "white")],
    )

    service = OCRService.__new__(OCRService)
    service.max_pdf_pages = 1
    service.dpi = 300
    service.timeout = 120
    service.lang_string = "eng+mya"
    service.preprocessing = True
    service._extract_pdf_text = lambda _path: ""
    preprocessing_options = []

    def recognize(_image, _language, *, preprocess=None):
        preprocessing_options.append(preprocess)
        return "\n" if preprocess is None else "Recovered text"

    service._recognize_image = recognize
    text = service._process_pdf(Path("scanned.pdf"))

    assert "Recovered text" in text
    assert preprocessing_options == [None, False]


def test_pdf_does_not_retry_raw_image_when_preprocessing_returns_text(
    monkeypatch: pytest.MonkeyPatch,
):
    class PdfPages:
        pages = [object()]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("app.services.ocr_service.pdfplumber.open", lambda _path: PdfPages())
    monkeypatch.setattr(
        "app.services.ocr_service.convert_from_path",
        lambda *_args, **_kwargs: [Image.new("RGB", (2, 2), "white")],
    )

    service = OCRService.__new__(OCRService)
    service.max_pdf_pages = 1
    service.dpi = 300
    service.timeout = 120
    service.lang_string = "eng+mya"
    service.preprocessing = True
    service._extract_pdf_text = lambda _path: ""
    preprocessing_options = []

    def recognize(_image, _language, *, preprocess=None):
        preprocessing_options.append(preprocess)
        return "Existing OCR text"

    service._recognize_image = recognize
    text = service._process_pdf(Path("scanned.pdf"))

    assert "Existing OCR text" in text
    assert preprocessing_options == [None]


def test_myanmar_line_crops_are_upscaled_without_shrinking_large_text():
    import numpy as np

    service = OCRService.__new__(OCRService)
    # Two separate, small horizontal text bands with ink on a white page.
    image = np.full((100, 240), 255, dtype=np.uint8)
    image[10:20, 30:180] = 0
    image[45:80, 20:200] = 0

    lines = service._text_line_images(image)

    assert len(lines) == 2
    assert lines[0].height >= 48
    assert lines[1].height >= 48
    # The naturally tall second crop must not be downscaled.
    assert lines[1].height >= 50

