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
