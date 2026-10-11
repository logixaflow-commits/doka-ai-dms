from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.services.ocr_benchmark import (
    edit_distance,
    grapheme_clusters,
    resolve_sample_path,
    run_ocr_benchmark,
    score_text,
)


def test_levenshtein_distance_supports_characters_and_words():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance(["one", "two"], ["one", "three"]) == 1


def test_ocr_scores_normalize_unicode_and_whitespace():
    result = score_text("  HELLO   world ", "hello world")
    assert result["cer"] == 0
    assert result["wer"] == 0
    assert result["character_errors"] == 0


def test_myanmar_cer_counts_graphemes_and_wer_segments_words():
    assert len(grapheme_clusters("ကာ")) == 1
    assert score_text("ကာ", "ကါ", "mya")["reference_characters"] == 1
    assert score_text(
        "မင်္ဂလာပါမိတ်ဆွေ",
        "မင်္ဂလာပါ မိတ်ဆွေ",
        "mya",
    )["wer"] == 0


def test_benchmark_uses_sample_language_for_configured_ocr(tmp_path, monkeypatch):
    from app.services.ocr_service import ocr_service

    root = tmp_path / "samples"
    root.mkdir()
    (root / "page.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["mya"],
        "samples": [{
            "path": "page.png",
            "language": "mya",
            "reference": "မင်္ဂလာပါ",
        }],
    }), encoding="utf-8")
    languages = []

    def fake_process_file(path, mime_type, *, language=None):
        languages.append(language)
        return "မင်္ဂလာပါ", language

    monkeypatch.setattr(ocr_service, "process_file", fake_process_file)
    report = run_ocr_benchmark(root, manifest)

    assert languages == ["mya"]
    assert report["scored_count"] == 1


def test_ocr_service_applies_requested_language(tmp_path, monkeypatch):
    from app.services.ocr_service import OCRError, ocr_service

    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"fixture")
    observed_languages = []

    def fake_process_image(path, language):
        observed_languages.append(language)
        return "မင်္ဂလာပါ"

    monkeypatch.setattr(ocr_service, "_process_image", fake_process_image)

    text, detected_language = ocr_service.process_file(
        str(image_path),
        "image/png",
        language="mya",
    )
    assert text == "မင်္ဂလာပါ"
    assert detected_language == "mya"
    assert observed_languages == ["mya"]
    with pytest.raises(OCRError, match="language is not configured"):
        ocr_service.process_file(str(image_path), "image/png", language="unknown")


def test_ocr_benchmark_rejects_path_escape_and_symlinks(tmp_path, make_symlink):
    root = tmp_path / "samples"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError):
        resolve_sample_path(root, "../outside.txt")
    make_symlink(root / "linked.txt", outside)
    with pytest.raises(ValueError):
        resolve_sample_path(root, "linked.txt")


def test_ocr_benchmark_report_does_not_include_reference_or_recognized_text(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()
    (root / "page.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "samples": [{
            "id": "myanmar-page-01",
            "path": "page.png",
            "mime_type": "image/png",
            "language": "mya",
            "source_document_id": "private-source-document",
            "reference": "မင်္ဂလာပါ world",
        }]
    }), encoding="utf-8")

    report = run_ocr_benchmark(
        root,
        manifest,
        ocr=lambda _path, _mime: ("မင်္ဂလာပါ world", "mya+eng"),
    )

    serialized = json.dumps(report, ensure_ascii=False)
    assert report["generated_at"].endswith("Z")
    assert report["scored_count"] == 1
    assert report["distinct_source_document_count"] == 1
    assert report["distinct_myanmar_source_document_count"] == 1
    assert report["toolchain"]["settings"]["timeout_seconds"] == 30
    assert report["summary_by_language"]["mya"]["mean_cer"] == 0
    assert report["scoring"]["myanmar_word_tokenizer"] == (
        "mmdt-tokenizer 0.1.3 grammar-based word segmentation"
    )
    assert report["privacy"]["recognized_text_included"] is False
    assert report["privacy"]["reference_text_included"] is False
    assert "မင်္ဂလာပါ" not in serialized
    assert str(root) not in serialized
    assert "private-source-document" not in serialized


def test_ocr_benchmark_gate_fails_when_recognition_quality_exceeds_threshold(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()
    (root / "english.png").write_bytes(b"fixture")
    (root / "myanmar.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["eng", "mya"],
        "samples": [
            {"id": "english", "path": "english.png", "language": "eng", "reference": "this is the expected English text"},
            {"id": "myanmar", "path": "myanmar.png", "language": "mya", "reference": "မင်္ဂလာပါ မိတ်ဆွေ"},
        ],
    }), encoding="utf-8")

    def poor_ocr(path, _mime):
        if path.endswith("english.png"):
            return "this is the expected English text", "eng"
        return "unreadable output", "mya"

    report = run_ocr_benchmark(root, manifest, ocr=poor_ocr)
    assert report["scored_count"] == 2
    assert report["missing_scored_languages"] == []
    assert report["quality_failures"] == [
        {"language": "mya", "mean_cer_exceeded": True, "mean_wer_exceeded": True}
    ]
    assert report["gate_ready"] is False


def test_ocr_benchmark_rejects_invalid_quality_thresholds(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()
    (root / "page.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["eng"],
        "quality_thresholds": {"eng": {"max_mean_cer": 2}},
        "samples": [{"path": "page.png", "language": "eng", "reference": "hello"}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="between 0 and 1"):
        run_ocr_benchmark(root, manifest, ocr=lambda *_: ("hello", "eng"))


def test_checked_in_ocr_report_gate_matches_sample_metrics():
    from pathlib import Path

    repository_root = Path(__file__).resolve().parents[2]
    report_path = repository_root / "docs" / "Report" / "ocr-benchmark.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    quality_gate = report["quality_gate"]
    expected_failures = [
        {"sample_id": row["sample_id"], "reason": reason}
        for row in report["results"]
        if row["status"] == "scored"
        for reason, failed in (
            ("cer_exceeds_threshold", float(row["cer"]) > quality_gate["max_cer"]),
            ("wer_exceeds_threshold", float(row["wer"]) > quality_gate["max_wer"]),
        )
        if failed
    ]
    expected_passed = (
        report["sample_count"] >= 2
        and report["execution_ready"]
        and not report["missing_required_languages"]
        and not report["missing_scored_languages"]
        and not report["quality_failures"]
        and not expected_failures
    )

    assert quality_gate["failures"] == expected_failures
    assert quality_gate["failure_count"] == len(expected_failures)
    assert quality_gate["passed"] is expected_passed
    assert report["gate_ready"] is expected_passed
    assert datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))


def test_ocr_benchmark_mixed_sample_does_not_satisfy_required_myanmar_language(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()
    (root / "mixed.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["eng", "mya"],
        "samples": [{
            "id": "mixed-only",
            "path": "mixed.png",
            "language": "mya+eng",
            "reference": "မင်္ဂလာပါ hello",
        }],
    }), encoding="utf-8")

    report = run_ocr_benchmark(
        root,
        manifest,
        ocr=lambda *_: ("မင်္ဂလာပါ hello", "mya+eng"),
    )

    assert report["scored_count"] == 1
    assert report["missing_required_languages"] == ["eng", "mya"]
    assert report["missing_scored_languages"] == ["eng", "mya"]
    assert report["gate_ready"] is False


def test_missing_tesseract_language_and_ocr_errors_block_gate(tmp_path, monkeypatch):
    from app.services import ocr_benchmark

    root = tmp_path / "samples"
    root.mkdir()
    (root / "page.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["mya"],
        "samples": [{
            "path": "page.png",
            "language": "mya",
            "reference": "မင်္ဂလာပါ",
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(ocr_benchmark, "collect_ocr_toolchain", lambda: {
        "available": True,
        "languages": ["eng"],
        "version": "test",
        "command_configured": "tesseract",
    })

    report = run_ocr_benchmark(
        root,
        manifest,
        ocr=lambda *_: (_ for _ in ()).throw(RuntimeError("OCR failed")),
    )

    assert report["missing_tool_languages"] == ["mya"]
    assert report["error_count"] == 1
    assert report["execution_ready"] is False
    assert report["gate_ready"] is False
