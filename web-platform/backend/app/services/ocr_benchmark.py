"""Privacy-conscious OCR benchmark helpers for the Personal Local pilot.

The benchmark records aggregate character/word error rates and never writes
recognized text or ground-truth text into its report.
"""
from __future__ import annotations

import json
import mimetypes
import subprocess
import unicodedata
from pathlib import Path
from collections.abc import Sequence
from typing import Any, Callable


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


def edit_distance(left: Sequence[str], right: Sequence[str]) -> int:
    """Levenshtein distance using O(min(n, m)) memory."""
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def score_text(reference: str, prediction: str) -> dict[str, float | int]:
    ref = normalize_text(reference)
    pred = normalize_text(prediction)
    ref_words = ref.split()
    pred_words = pred.split()
    return {
        "character_errors": edit_distance(ref, pred),
        "reference_characters": len(ref),
        "cer": edit_distance(ref, pred) / max(1, len(ref)),
        "word_errors": edit_distance(ref_words, pred_words),
        "reference_words": len(ref_words),
        "wer": edit_distance(ref_words, pred_words) / max(1, len(ref_words)),
    }


def resolve_sample_path(root: Path, relative_path: str) -> Path:
    root = root.resolve(strict=True)
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError("Sample paths must be relative to the benchmark root.")
    candidate = root / relative_path
    current = root
    for part in Path(relative_path).parts:
        if part in {"", ".", ".."}:
            raise ValueError("Sample path contains an unsafe segment.")
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink samples are not allowed.")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("Sample path escapes the benchmark root or is not a file.")
    return resolved


def collect_ocr_toolchain() -> dict[str, Any]:
    """Return privacy-safe OCR runtime metadata for release evidence."""
    try:
        from app.core.config import settings
        command = settings.TESSERACT_CMD or "tesseract"
        completed = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version_line = (completed.stdout or completed.stderr).splitlines()[0].strip() if (completed.stdout or completed.stderr) else ""
        languages = []
        lang_proc = subprocess.run(
            [command, "--list-langs"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if lang_proc.returncode == 0:
            languages = [line.strip() for line in lang_proc.stdout.splitlines()[1:] if line.strip()]
        return {
            "command_configured": command,
            "version": version_line or None,
            "languages": languages,
            "available": completed.returncode == 0,
        }
    except Exception as exc:
        return {
            "command_configured": None,
            "version": None,
            "languages": [],
            "available": False,
            "error_type": type(exc).__name__,
        }


def run_ocr_benchmark(
    root: Path,
    manifest_path: Path,
    *,
    ocr: Callable[[str, str], tuple[str, str | None]] | None = None,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Benchmark root must be a directory.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest.get("samples") if isinstance(manifest, dict) else None
    required_languages = manifest.get("required_languages", ["mya", "eng"]) if isinstance(manifest, dict) else ["mya", "eng"]
    if not isinstance(samples, list) or not samples:
        raise ValueError("Manifest must contain a non-empty 'samples' array.")
    if ocr is None:
        from app.services.ocr_service import ocr_service
        ocr = ocr_service.process_file

    results: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict) or not isinstance(sample.get("reference"), str) or not sample["reference"].strip():
            raise ValueError(f"Sample {index + 1} requires a non-empty reference string.")
        path = resolve_sample_path(root, str(sample.get("path", "")))
        mime_type = str(sample.get("mime_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        language = str(sample.get("language") or "mya+eng")
        try:
            prediction, detected_language = ocr(str(path), mime_type)
            scores = score_text(sample["reference"], prediction or "")
            results.append({
                "sample_id": str(sample.get("id") or f"sample-{index + 1:03d}"),
                "language": language,
                "detected_language": detected_language,
                "status": "scored",
                **scores,
            })
        except Exception as exc:
            results.append({
                "sample_id": str(sample.get("id") or f"sample-{index + 1:03d}"),
                "language": language,
                "status": "error",
                "error_type": type(exc).__name__,
            })

    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        if result["status"] == "scored":
            grouped.setdefault(result["language"], []).append(result)
    summary = {}
    for language, rows in grouped.items():
        summary[language] = {
            "samples": len(rows),
            "mean_cer": sum(float(row["cer"]) for row in rows) / len(rows),
            "mean_wer": sum(float(row["wer"]) for row in rows) / len(rows),
        }
    language_labels = {str(sample.get("language", "")).lower() for sample in samples if isinstance(sample, dict)}
    missing_required_languages = [lang for lang in required_languages if not any(lang in label.split("+") for label in language_labels)]
    toolchain = collect_ocr_toolchain()
    missing_tool_languages = [lang for lang in required_languages if lang not in toolchain.get("languages", [])]
    configured_thresholds = manifest.get("quality_thresholds", {}) if isinstance(manifest, dict) else {}
    if not isinstance(configured_thresholds, dict):
        raise ValueError("quality_thresholds must be an object keyed by language label.")
    quality_thresholds: dict[str, dict[str, float]] = {}
    quality_failures: list[dict[str, Any]] = []
    for language, metrics in summary.items():
        configured = configured_thresholds.get(language, {})
        if not isinstance(configured, dict):
            raise ValueError(f"Quality thresholds for {language!r} must be an object.")
        max_cer = configured.get("max_mean_cer", 0.30)
        max_wer = configured.get("max_mean_wer", 0.60)
        if (
            isinstance(max_cer, bool) or not isinstance(max_cer, (int, float))
            or not 0 <= max_cer <= 1
            or isinstance(max_wer, bool) or not isinstance(max_wer, (int, float))
            or not 0 <= max_wer <= 1
        ):
            raise ValueError(f"Quality thresholds for {language!r} must be between 0 and 1.")
        quality_thresholds[language] = {
            "max_mean_cer": float(max_cer),
            "max_mean_wer": float(max_wer),
        }
        if metrics["mean_cer"] > max_cer or metrics["mean_wer"] > max_wer:
            quality_failures.append({
                "language": language,
                "mean_cer_exceeded": metrics["mean_cer"] > max_cer,
                "mean_wer_exceeded": metrics["mean_wer"] > max_wer,
            })
    # Every required language must have a scored sample, not merely a manifest entry.
    scored_language_labels = {row["language"].lower() for row in results if row["status"] == "scored"}
    missing_scored_languages = [
        lang for lang in required_languages
        if not any(lang in label.split("+") for label in scored_language_labels)
    ]
    return {
        "schema_version": 2,
        "sample_count": len(samples),
        "scored_count": sum(row["status"] == "scored" for row in results),
        "error_count": sum(row["status"] == "error" for row in results),
        "summary_by_language": summary,
        "required_languages": required_languages,
        "missing_required_languages": missing_required_languages,
        "missing_tool_languages": missing_tool_languages,
        "missing_scored_languages": missing_scored_languages,
        "quality_thresholds": quality_thresholds,
        "quality_failures": quality_failures,
        "gate_ready": (
            len(samples) >= 2
            and not missing_required_languages
            and not missing_tool_languages
            and not missing_scored_languages
            and not quality_failures
            and not any(row["status"] == "error" for row in results)
            and toolchain["available"]
        ),
        "toolchain": toolchain,
        "results": results,
        "privacy": {
            "recognized_text_included": False,
            "reference_text_included": False,
            "source_files_modified": False,
        },
    }
