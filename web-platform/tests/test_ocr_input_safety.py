"""Focused safety tests for OCR input boundaries."""
from pathlib import Path

import pytest

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
