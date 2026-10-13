"""Local OCR/reference comparison primitives.

This module performs no network calls and writes no files. Callers may render
returned spans in a local review UI; aggregate reports should store IDs/metrics.
"""
from __future__ import annotations
from collections.abc import Iterable, Mapping
from difflib import SequenceMatcher
from typing import Any
from app.services.ocr_benchmark import grapheme_clusters, score_text

DEFAULT_MAX_CER = 0.10
DEFAULT_MAX_WER = 0.20

def _diff_segments(reference: str, prediction: str) -> list[dict[str, str]]:
    """Return grapheme-level aligned segments for side-by-side highlighting."""
    ref_units = grapheme_clusters(reference)
    pred_units = grapheme_clusters(prediction)
    matcher = SequenceMatcher(a=ref_units, b=pred_units, autojunk=False)
    segments: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        segments.append({
            "kind": "equal" if tag == "equal" else (
                "inserted" if tag == "insert" else (
                    "deleted" if tag == "delete" else "changed"
                )
            ),
            "reference": "".join(ref_units[i1:i2]),
            "prediction": "".join(pred_units[j1:j2]),
        })
    return segments

def compare_ocr_text(
    reference: str,
    prediction: str,
    *,
    language: str = "mya+eng",
    max_cer: float = DEFAULT_MAX_CER,
    max_wer: float = DEFAULT_MAX_WER,
) -> dict[str, Any]:
    """Compare OCR output with owner-verified reference text.

    PASS means only that configured text-error thresholds passed; it does not
    certify critical fields or prove the reference itself is correct.
    """
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("A non-empty verified reference is required.")
    if not isinstance(prediction, str):
        raise ValueError("OCR prediction must be text.")
    for name, threshold in (("max_cer", max_cer), ("max_wer", max_wer)):
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise ValueError(f"{name} must be a number between 0 and 1.")
    metrics = score_text(reference, prediction, language)
    empty_prediction = not prediction.strip()
    passed = (
        not empty_prediction
        and float(metrics["cer"]) <= max_cer
        and float(metrics["wer"]) <= max_wer
    )
    return {
        "status": "FAIL" if empty_prediction else ("PASS" if passed else "REVIEW"),
        "language": language,
        "thresholds": {"max_cer": float(max_cer), "max_wer": float(max_wer)},
        "metrics": metrics,
        "diff": _diff_segments(reference, prediction),
        "privacy": {"network_used": False, "files_written": False},
    }

def compare_batch(
    records: Iterable[Mapping[str, Any]],
    *,
    max_cer: float = DEFAULT_MAX_CER,
    max_wer: float = DEFAULT_MAX_WER,
) -> dict[str, Any]:
    """Compare a batch. Raw text is included per item for local review only."""
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise ValueError(f"Record {index} must be an object.")
        file_id = record.get("file_id")
        if not isinstance(file_id, str) or not file_id.strip():
            raise ValueError(f"Record {index} requires a non-empty file_id.")
        file_id = file_id.strip()
        if file_id in seen_ids:
            raise ValueError(f"Duplicate file_id: {file_id}")
        seen_ids.add(file_id)
        try:
            comparison = compare_ocr_text(
                record.get("reference"),
                record.get("prediction"),
                language=str(record.get("language") or "mya+eng"),
                max_cer=max_cer,
                max_wer=max_wer,
            )
            results.append({"file_id": file_id, **comparison})
        except (TypeError, ValueError) as exc:
            results.append({
                "file_id": file_id,
                "status": "FAIL",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
    counts = {status: sum(item.get("status") == status for item in results)
              for status in ("PASS", "REVIEW", "FAIL")}
    return {
        "total": len(results),
        "status_counts": counts,
        "all_passed": bool(results) and counts["PASS"] == len(results),
        "results": results,
        "privacy": {"network_used": False, "source_files_modified": False},
    }
