"""Regression tests for fail-closed, language-specific OCR acceptance."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ocr_benchmark import run_ocr_benchmark, score_text  # noqa: E402


def _run(root: Path, manifest: dict, ocr):
    manifest_path = root.parent / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    with patch(
        "app.services.ocr_benchmark.collect_ocr_toolchain",
        return_value={"command_configured": "tesseract", "version": "test", "languages": ["eng", "mya"], "available": True},
    ):
        return run_ocr_benchmark(root, manifest_path, ocr=ocr)


def test_mixed_sample_does_not_substitute_for_language_specific_samples(tmp_path: Path):
    sample_root = tmp_path / "samples"
    sample_root.mkdir()
    (sample_root / "mixed.txt").write_text("sample", encoding="utf-8")
    report = _run(
        sample_root,
        {
            "required_languages": ["mya", "eng"],
            "samples": [{"id": "mixed", "path": "mixed.txt", "language": "mya+eng", "reference": "hello မြန်မာ"}],
        },
        lambda _path, _mime: ("hello မြန်မာ", "eng"),
    )
    assert report["missing_required_languages"] == ["mya", "eng"]
    assert report["missing_scored_languages"] == ["mya", "eng"]
    assert report["gate_ready"] is False


def test_language_specific_english_and_myanmar_samples_can_pass(tmp_path: Path):
    sample_root = tmp_path / "samples"
    sample_root.mkdir()
    for name in ("english.txt", "myanmar.txt"):
        (sample_root / name).write_text("sample", encoding="utf-8")
    report = _run(
        sample_root,
        {
            "required_languages": ["mya", "eng"],
            "samples": [
                {"id": "english", "path": "english.txt", "language": "eng", "reference": "hello world"},
                {"id": "myanmar", "path": "myanmar.txt", "language": "mya", "reference": "မြန်မာစာ"},
            ],
        },
        lambda path, _mime: ("hello world" if path.endswith("english.txt") else "မြန်မာစာ", "eng"),
    )
    assert report["missing_required_languages"] == []
    assert report["missing_scored_languages"] == []
    assert report["quality_failures"] == []
    assert report["gate_ready"] is True
    assert set(report["summary_by_language"]) == {"eng", "mya"}


def test_score_normalizes_unicode_nfc():
    assert score_text("é", "e\u0301")["cer"] == 0
