"""Focused safety tests for OCR input boundaries."""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.exceptions import OCRError
from app.services.ocr_service import OCRService


def test_ocr_rejects_unsupported_mime_before_parsing(tmp_path: Path):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"%PDF-1.7")
    service = OCRService()

    with pytest.raises(OCRError, match="Unsupported file type"):
        service.process_file(str(path), "application/octet-stream")


def test_ocr_rejects_files_over_configured_size(tmp_path: Path):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"%PDF-1.7")
    service = OCRService()
    service.max_file_bytes = 4

    with pytest.raises(OCRError, match="configured limit"):
        service.process_file(str(path), "application/pdf")


def test_ocr_rejects_non_pdf_content_with_pdf_mime(tmp_path: Path):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"not-a-pdf")
    service = OCRService()

    with pytest.raises(OCRError, match="valid PDF header"):
        service.process_file(str(path), "application/pdf")


def test_ocr_rejects_empty_input(tmp_path: Path):
    path = tmp_path / "empty.png"
    path.write_bytes(b"")
    service = OCRService()

    with pytest.raises(OCRError, match="empty"):
        service.process_file(str(path), "image/png")


def test_ocr_rejects_symlink_inputs(tmp_path: Path):
    target = tmp_path / "document.pdf"
    target.write_bytes(b"%PDF-1.7")
    link = tmp_path / "document-link.pdf"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this test platform")

    service = OCRService()
    with pytest.raises(OCRError, match="symbolic-link"):
        service.process_file(str(link), "application/pdf")


def test_ocr_adaptive_preprocessing_preserves_dimensions_and_binary_output():
    service = OCRService()
    image = np.full((100, 200, 3), 255, dtype=np.uint8)
    image[45:55, 20:180] = 0

    processed = service._preprocess_image(image)

    assert processed.shape == image.shape
    assert set(np.unique(processed)) == {0, 255}


def test_ocr_layout_settings_select_block_mode_for_wide_images():
    service = OCRService()
    wide_crop = np.zeros((825, 2550, 3), dtype=np.uint8)
    portrait_page = np.zeros((3300, 2550, 3), dtype=np.uint8)

    assert service._layout_ocr_settings(wide_crop) == (6, 5)
    assert service._layout_ocr_settings(portrait_page) == (service.psm, 10)


def test_ocr_line_recognition_uses_one_tesseract_call_and_cleans_temp_files(tmp_path, monkeypatch):
    import pytesseract

    service = OCRService()
    image = np.full((200, 100, 3), 255, dtype=np.uint8)
    image[30:40, 10:90] = 0
    image[150:160, 15:85] = 0
    captured = {}

    def fake_image_to_string(path, *, lang, config, timeout):
        captured.update(path=Path(path), lang=lang, config=config, timeout=timeout)
        with Image.open(path) as multipage:
            captured["frames"] = multipage.n_frames
        return "မင်္ဂလာပါ\nမိတ်ဆွေ"

    monkeypatch.setattr(pytesseract, "image_to_string", fake_image_to_string)

    result = service._recognize_image(image, "mya+eng")

    assert result == "မင်္ဂလာပါ\nမိတ်ဆွေ"
    assert captured["frames"] == 2
    assert captured["lang"] == "mya+eng"
    assert captured["config"] == f"--oem {service.oem} --psm 7"
    assert captured["timeout"] == service.timeout
    assert not captured["path"].exists()
