"""Regression tests for the fail-closed local acceptance preflight."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "local_acceptance_preflight.py"
SPEC = importlib.util.spec_from_file_location("local_acceptance_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _paths(tmp_path: Path) -> tuple[dict[str, str], Path]:
    source = tmp_path / "source-copy"
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    ocr_root = tmp_path / "ocr-samples"
    evidence = tmp_path / "evidence"
    for directory in (source, workspace, backups, ocr_root, evidence):
        directory.mkdir()
    (source / "example.txt").write_text("synthetic copy only", encoding="utf-8")
    (ocr_root / "sample.txt").write_text("synthetic sample", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "required_languages": ["mya", "eng"],
        "samples": [{"id": "synthetic-1", "path": "sample.txt", "language": "eng", "reference": "synthetic"}],
    }), encoding="utf-8")
    env = {
        "DOKA_PILOT_SOURCE": str(source),
        "DOKA_PILOT_WORKSPACE": str(workspace),
        "DOKA_PILOT_BACKUPS": str(backups),
        "DOKA_OCR_ROOT": str(ocr_root),
        "DOKA_OCR_MANIFEST": str(manifest),
        "BOOTSTRAP_ADMIN_PASSWORD": "synthetic-only-password-123",
        "AI_ENABLED": "false",
        "AI_EXTERNAL_PROCESSING_CONSENT": "false",
        "ALLOW_SOURCE_WRITE": "false",
        "ORIGINAL_READ_ONLY": "true",
    }
    return env, evidence


def test_preflight_fails_closed_when_required_configuration_is_missing(tmp_path):
    report = MODULE.validate_environment({}, tmp_path / "evidence")
    assert report["ready"] is False
    assert any("Missing required environment variables" in error for error in report["errors"])
    assert report["privacy"]["secret_values_recorded"] is False
    assert report["privacy"]["paths_recorded"] is False


def test_preflight_rejects_overlapping_evidence_and_source_paths(tmp_path):
    env, _ = _paths(tmp_path)
    report = MODULE.validate_environment(env, Path(env["DOKA_PILOT_SOURCE"]) / "evidence")
    assert report["ready"] is False
    assert any("paths must be separate and non-overlapping" in error for error in report["errors"])


def test_preflight_rejects_workspace_with_existing_files(tmp_path):
    env, evidence = _paths(tmp_path)
    (Path(env["DOKA_PILOT_WORKSPACE"]) / "keep-me.txt").write_text("do not overwrite", encoding="utf-8")
    report = MODULE.validate_environment(env, evidence)
    assert report["ready"] is False
    assert any("must be empty before acceptance" in error for error in report["errors"])


def test_preflight_rejects_manifest_path_escape(tmp_path):
    env, evidence = _paths(tmp_path)
    payload = json.loads(Path(env["DOKA_OCR_MANIFEST"]).read_text(encoding="utf-8"))
    payload["samples"][0]["path"] = "../source-copy/example.txt"
    Path(env["DOKA_OCR_MANIFEST"]).write_text(json.dumps(payload), encoding="utf-8")
    report = MODULE.validate_environment(env, evidence)
    assert report["ready"] is False
    assert any("invalid relative path" in error for error in report["errors"])


def test_preflight_report_cannot_overwrite_manifest_or_enter_evidence(tmp_path):
    env, evidence = _paths(tmp_path)
    manifest = Path(env["DOKA_OCR_MANIFEST"])
    assert MODULE._safe_report_path(evidence / "preflight.json", env, evidence)
    assert not MODULE._safe_report_path(tmp_path / "safe-report.json", env, evidence)
    assert not MODULE._safe_report_path(manifest, env, evidence)
    assert not MODULE._safe_report_path(Path(env["DOKA_PILOT_SOURCE"]) / "preflight.json", env, evidence)
    assert not MODULE._safe_report_path(evidence, env, evidence)
