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


def test_analyze_uses_session_bound_verified_copy_not_manifest_absolute_paths(tmp_path, monkeypatch):
    import hashlib
    import json

    import pytest
    from app.core.config import settings

    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    source.mkdir()
    session_id = "c" * 32
    session = workspace / "imports" / session_id
    working_copy = session / "source_copy"
    working_copy.mkdir(parents=True)
    copied = working_copy / "note.txt"
    copied.write_text("safe working copy text", encoding="utf-8")
    external = tmp_path / "external-secret.txt"
    external.write_text("must not be read", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)

    manifest = {
        "session_id": session_id,
        "source_root": str(source),
        "working_copy": str(working_copy),
        "files": {
            "note.txt": {
                "relative_path": "note.txt",
                "working_path": str(external),
                "filename": "note.txt",
                "extension": ".txt",
                "sha256": hashlib.sha256(copied.read_bytes()).hexdigest(),
                "verified": True,
            }
        },
    }
    (session / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)

    service = DocumentUnderstandingService(SafeWorkspaceService())
    result = service.analyze(session_id)
    assert result["analyzed_files"] == 1
    saved = json.loads((session / "understanding.json").read_text(encoding="utf-8"))
    assert "safe working copy text" in saved["results"][0]["text_preview"]
    assert "must not be read" not in saved["results"][0]["text_preview"]


def test_analyze_rejects_manifest_working_copy_escape(tmp_path, monkeypatch):
    import json

    import pytest
    from app.core.config import settings

    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    session_id = "d" * 32
    session = workspace / "imports" / session_id
    session.mkdir(parents=True)
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    manifest = {
        "session_id": session_id,
        "source_root": str(source),
        "working_copy": str(outside),
        "files": {},
    }
    (session / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)

    service = DocumentUnderstandingService(SafeWorkspaceService())
    with pytest.raises(ValueError, match="working-copy path is invalid"):
        service.analyze(session_id)


def test_analyze_records_ocr_method_separately_from_detected_language(tmp_path, monkeypatch):
    import hashlib
    import json
    from app.core.config import settings

    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    source.mkdir()
    session_id = "e" * 32
    session = workspace / "imports" / session_id
    working_copy = session / "source_copy"
    working_copy.mkdir(parents=True)
    image = working_copy / "scan.png"
    image.write_bytes(b"fixture")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)

    manifest = {
        "session_id": session_id,
        "source_root": str(source),
        "working_copy": str(working_copy),
        "files": {
            "scan.png": {
                "relative_path": "scan.png",
                "filename": "scan.png",
                "extension": ".png",
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "verified": True,
            }
        },
    }
    (session / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)

    service = DocumentUnderstandingService(SafeWorkspaceService())
    service._extract_text = lambda _path: ("recognized Myanmar and English text", "mya+eng")
    service.analyze(session_id)

    saved = json.loads((session / "understanding.json").read_text(encoding="utf-8"))
    result = saved["results"][0]
    assert result["extraction_method"] == "ocr"
    assert result["language"] == "mya+eng"


def test_analyze_resumability_and_deduplication(tmp_path, monkeypatch):
    import hashlib
    import json
    from app.core.config import settings

    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    source.mkdir()
    session_id = "f" * 32
    session = workspace / "imports" / session_id
    working_copy = session / "source_copy"
    working_copy.mkdir(parents=True)

    file1 = working_copy / "doc1.txt"
    file1.write_text("Unique content 1", encoding="utf-8")
    file2 = working_copy / "doc2.txt"
    file2.write_text("Identical content", encoding="utf-8")
    file3 = working_copy / "doc3_copy.txt"
    file3.write_text("Identical content", encoding="utf-8")

    h1 = hashlib.sha256(file1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(file2.read_bytes()).hexdigest()
    h3 = hashlib.sha256(file3.read_bytes()).hexdigest()
    assert h2 == h3

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)

    manifest = {
        "session_id": session_id,
        "source_root": str(source),
        "working_copy": str(working_copy),
        "files": {
            "doc1.txt": {"relative_path": "doc1.txt", "filename": "doc1.txt", "extension": ".txt", "sha256": h1, "verified": True},
            "doc2.txt": {"relative_path": "doc2.txt", "filename": "doc2.txt", "extension": ".txt", "sha256": h2, "verified": True},
            "doc3_copy.txt": {"relative_path": "doc3_copy.txt", "filename": "doc3_copy.txt", "extension": ".txt", "sha256": h3, "verified": True},
        },
    }
    (session / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Simulate an earlier partial run that already processed doc1.txt
    prior_understanding = {
        "schema_version": 1,
        "session_id": session_id,
        "analyzed_files": 1,
        "results": [
            {
                "relative_path": "doc1.txt",
                "filename": "doc1.txt",
                "extension": ".txt",
                "sha256": h1,
                "extraction_method": "text",
                "text_length": 16,
                "language": None,
                "metadata": {},
                "text_preview": "Unique content 1 (from prior run)",
            }
        ]
    }
    (session / "understanding.json").write_text(json.dumps(prior_understanding), encoding="utf-8")

    service = DocumentUnderstandingService(SafeWorkspaceService())
    result = service.analyze(session_id)
    assert result["analyzed_files"] == 3

    saved = json.loads((session / "understanding.json").read_text(encoding="utf-8"))
    results_by_rel = {r["relative_path"]: r for r in saved["results"]}

    # doc1 was resumed from prior run
    assert results_by_rel["doc1.txt"]["text_preview"] == "Unique content 1 (from prior run)"

    # doc2 was freshly extracted
    assert results_by_rel["doc2.txt"]["extraction_method"] == "text"

    # doc3 was deduplicated from doc2 without re-extraction
    assert "dedup" in results_by_rel["doc3_copy.txt"]["extraction_method"]
    assert results_by_rel["doc3_copy.txt"]["deduplicated_from"] == "doc2.txt"

