"""Privacy-conscious OCR benchmark helpers for the Personal Local pilot.

The benchmark records per-sample and aggregate error metrics but never writes
recognized text or ground-truth text into its report.
"""
from __future__ import annotations

import json
import mimetypes
import subprocess
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from mmdt_tokenizer import MyanmarTokenizer


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


def grapheme_clusters(value: str) -> list[str]:
    """Treat combining marks and Myanmar virama sequences as one CER unit."""
    clusters: list[str] = []
    for char in value:
        category = unicodedata.category(char)
        if clusters and (
            category in {"Mn", "Mc", "Me"}
            or char in {"\u200c", "\u200d"}
            or clusters[-1].endswith(("\u1039", "\u200d"))
        ):
            clusters[-1] += char
        else:
            clusters.append(char)
    return clusters


def word_tokens(value: str, language: str) -> list[str]:
    if "mya" in {part.strip().lower() for part in language.split("+")}:
        tokens: list[str] = []
        for segment in value.split():
            if any("\u1000" <= char <= "\u109f" for char in segment):
                tokenized = _myanmar_tokenizer().word_tokenize(segment)
                tokens.extend(tokenized[0] if tokenized else [])
            else:
                tokens.append(segment)
        return tokens
    return value.split()


@lru_cache(maxsize=1)
def _myanmar_tokenizer() -> MyanmarTokenizer:
    from mmdt_tokenizer import MyanmarTokenizer

    return MyanmarTokenizer()


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


def score_text(
    reference: str,
    prediction: str,
    language: str = "eng",
) -> dict[str, float | int]:
    ref = normalize_text(reference)
    pred = normalize_text(prediction)
    ref_characters = grapheme_clusters(ref)
    pred_characters = grapheme_clusters(pred)
    ref_words = word_tokens(ref, language)
    pred_words = word_tokens(pred, language)
    character_errors = edit_distance(ref_characters, pred_characters)
    word_errors = edit_distance(ref_words, pred_words)
    return {
        "character_errors": character_errors,
        "reference_characters": len(ref_characters),
        "cer": character_errors / max(1, len(ref_characters)),
        "word_errors": word_errors,
        "reference_words": len(ref_words),
        "wer": word_errors / max(1, len(ref_words)),
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
        ocr_config = settings.ocr
        return {
            "command_configured": command,
            "version": version_line or None,
            "languages": languages,
            "available": completed.returncode == 0,
            "settings": {
                "dpi": ocr_config.dpi,
                "oem": ocr_config.oem,
                "psm": ocr_config.psm,
                "preprocessing": ocr_config.preprocessing,
                "psm_layout_policy": "PSM 6 for width/height >= 2; configured PSM otherwise",
                "preprocessing_method": "adaptive Gaussian threshold, block size 41, C=5 for width/height >= 2 and C=10 otherwise",
                "text_line_ocr_policy": "Myanmar-containing portrait/square images: detect text rows and OCR a multipage TIFF with PSM 7; other images use layout PSM",
            },
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
    configured_ocr_service = None
    if ocr is None:
        from app.services.ocr_service import ocr_service
        configured_ocr_service = ocr_service

    results: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict) or not isinstance(sample.get("reference"), str) or not sample["reference"].strip():
            raise ValueError(f"Sample {index + 1} requires a non-empty reference string.")
        path = resolve_sample_path(root, str(sample.get("path", "")))
        mime_type = str(sample.get("mime_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        language = str(sample.get("language") or "mya+eng")
        try:
            if configured_ocr_service is not None:
                prediction, detected_language = configured_ocr_service.process_file(
                    str(path),
                    mime_type,
                    language=language,
                )
            else:
                if ocr is None:
                    raise RuntimeError("OCR callback is unavailable.")
                prediction, detected_language = ocr(str(path), mime_type)
            scores = score_text(sample["reference"], prediction or "", language)
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
    # A mixed-language sample is useful as a separate mixed-script check, but it
    # cannot stand in for a language-specific quality score. Require explicit
    # samples labelled exactly `mya` and `eng` so a poor Myanmar result cannot be
    # hidden inside a combined `mya+eng` aggregate.
    language_labels = {
        str(sample.get("language", "")).strip().lower()
        for sample in samples
        if isinstance(sample, dict)
    }
    missing_required_languages = [
        lang for lang in required_languages
        if str(lang).strip().lower() not in language_labels
    ]
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
    scored_language_labels = {
        str(row["language"]).strip().lower()
        for row in results
        if row["status"] == "scored"
    }
    missing_scored_languages = [
        lang for lang in required_languages
        if str(lang).strip().lower() not in scored_language_labels
    ]
    error_count = sum(row["status"] == "error" for row in results)
    execution_ready = (
        toolchain["available"]
        and not missing_tool_languages
        and error_count == 0
    )
    sample_quality_gate = {
        "max_cer": 0.10,
        "max_wer": 0.20,
        "failures": [
            {"sample_id": row["sample_id"], "reason": reason}
            for row in results
            if row["status"] == "scored"
            for reason, exceeded in (
                ("cer_exceeds_threshold", float(row["cer"]) > 0.10),
                ("wer_exceeds_threshold", float(row["wer"]) > 0.20),
            )
            if exceeded
        ],
    }
    sample_quality_gate["failure_count"] = len(sample_quality_gate["failures"])
    gate_ready = (
        len(samples) >= 2
        and not missing_required_languages
        and not missing_scored_languages
        and execution_ready
        and not quality_failures
        and sample_quality_gate["failure_count"] == 0
    )
    sample_quality_gate["passed"] = gate_ready
    return {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sample_count": len(samples),
        "scored_count": sum(row["status"] == "scored" for row in results),
        "error_count": error_count,
        "execution_ready": execution_ready,
        "summary_by_language": summary,
        "required_languages": required_languages,
        "missing_required_languages": missing_required_languages,
        "missing_tool_languages": missing_tool_languages,
        "missing_scored_languages": missing_scored_languages,
        "quality_thresholds": quality_thresholds,
        "quality_failures": quality_failures,
        "quality_gate": sample_quality_gate,
        "scoring": {
            "normalization": "NFC, case-folded, whitespace-collapsed",
            "character_unit": "Unicode grapheme cluster",
            "myanmar_word_tokenizer": "mmdt-tokenizer 0.1.3 grammar-based word segmentation",
            "other_word_tokenizer": "whitespace",
        },
        "gate_ready": gate_ready,
        "toolchain": toolchain,
        "results": results,
        "privacy": {
            "recognized_text_included": False,
            "reference_text_included": False,
            "source_files_modified": False,
        },
    }
