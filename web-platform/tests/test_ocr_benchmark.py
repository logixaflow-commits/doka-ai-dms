from __future__ import annotations

import json

import pytest

from app.services.ocr_benchmark import edit_distance, resolve_sample_path, run_ocr_benchmark, score_text


def test_levenshtein_distance_supports_characters_and_words():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance(["one", "two"], ["one", "three"]) == 1


def test_ocr_scores_normalize_unicode_and_whitespace():
    result = score_text("  HELLO   world ", "hello world")
    assert result["cer"] == 0
    assert result["wer"] == 0
    assert result["character_errors"] == 0


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
            "language": "mya+eng",
            "reference": "မင်္ဂလာပါ world",
        }]
    }), encoding="utf-8")

    report = run_ocr_benchmark(
        root,
        manifest,
        ocr=lambda _path, _mime: ("မင်္ဂလာပါ world", "mya+eng"),
    )

    serialized = json.dumps(report, ensure_ascii=False)
    assert report["scored_count"] == 1
    assert report["summary_by_language"]["mya+eng"]["mean_cer"] == 0
    assert report["privacy"]["recognized_text_included"] is False
    assert report["privacy"]["reference_text_included"] is False
    assert "မင်္ဂလာပါ" not in serialized
    assert str(root) not in serialized


def test_ocr_quality_gate_fails_when_accuracy_exceeds_balanced_thresholds(tmp_path, monkeypatch):
    root = tmp_path / "samples"
    root.mkdir()
    (root / "page.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["eng"],
        "samples": [
            {"id": "page-1", "path": "page.png", "mime_type": "image/png", "language": "eng", "reference": "hello world"},
            {"id": "page-2", "path": "page.png", "mime_type": "image/png", "language": "eng", "reference": "hello world"},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr("app.services.ocr_benchmark.collect_ocr_toolchain", lambda: {"available": True, "languages": ["eng"]})

    report = run_ocr_benchmark(root, manifest, ocr=lambda _path, _mime: ("unrelated words", "eng"))

    assert report["execution_ready"] is True
    assert report["quality_gate"]["max_cer"] == 0.10
    assert report["quality_gate"]["max_wer"] == 0.20
    assert report["quality_gate"]["passed"] is False
    assert report["gate_ready"] is False
    assert report["quality_gate"]["failure_count"] > 0


def test_ocr_quality_gate_passes_when_accuracy_is_within_thresholds(tmp_path, monkeypatch):
    root = tmp_path / "samples"
    root.mkdir()
    (root / "page.png").write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["eng"],
        "samples": [
            {"id": "page-1", "path": "page.png", "mime_type": "image/png", "language": "eng", "reference": "hello world"},
            {"id": "page-2", "path": "page.png", "mime_type": "image/png", "language": "eng", "reference": "hello world"},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr("app.services.ocr_benchmark.collect_ocr_toolchain", lambda: {"available": True, "languages": ["eng"]})

    report = run_ocr_benchmark(root, manifest, ocr=lambda _path, _mime: ("hello world", "eng"))

    assert report["quality_gate"]["passed"] is True
    assert report["gate_ready"] is True


def test_ocr_quality_thresholds_are_validated(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": [{"path": "missing.png", "reference": "text"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="thresholds"):
        run_ocr_benchmark(root, manifest, max_cer=1.1)
