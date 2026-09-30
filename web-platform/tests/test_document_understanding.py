from pathlib import Path
from zipfile import ZipFile

from app.services.document_understanding_service import DocumentUnderstandingService
from app.services.safe_workspace_service import SafeWorkspaceService


def _write_docx(path: Path, text: str) -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def test_docx_text_extraction_is_local_only(tmp_path: Path):
    workspace = tmp_path / "workspace"
    session = workspace / "imports" / ("a" * 32)
    working = session / "working_copy"
    working.mkdir(parents=True)
    docx = working / "invoice.docx"
    _write_docx(docx, "Commercial Invoice 2025")

    service = DocumentUnderstandingService(SafeWorkspaceService())
    text, method = service._extract_text(docx)

    assert method == "docx"
    assert "Commercial Invoice 2025" in text


def test_unsupported_format_does_not_call_ai(tmp_path: Path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"binary")
    service = DocumentUnderstandingService(SafeWorkspaceService())

    text, method = service._extract_text(path)

    assert text == ""
    assert method == "not_text_extracted"
