from pathlib import Path

import pytest

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
