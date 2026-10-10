from __future__ import annotations

import json
from pathlib import Path

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


def test_checked_in_ocr_report_gate_matches_sample_metrics():
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
    expected_passed = report["execution_ready"] and not expected_failures

    assert quality_gate["failures"] == expected_failures
    assert quality_gate["failure_count"] == len(expected_failures)
    assert quality_gate["passed"] is expected_passed
    assert report["gate_ready"] is expected_passed
