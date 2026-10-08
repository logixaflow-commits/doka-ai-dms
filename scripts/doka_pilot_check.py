#!/usr/bin/env python3
"""Doka real-machine pilot gate.

Run this only against a COPY of representative office data. The script never
writes to the supplied source directory; all generated state lives under the
configured Doka WORKING_ROOT/BACKUP_ROOT.

Example:
    python scripts/doka_pilot_check.py --source D:\\DokaPilotCopy --require-ocr

The gate intentionally stops before organization unless --apply-safe is given.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

# Make the local backend importable when this script is run from repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "web-platform" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.document_understanding_service import document_understanding_service  # noqa: E402
from app.services.ocr_validation_service import ocr_validation_service  # noqa: E402
from app.services.organization_planner import organization_planner  # noqa: E402
from app.services.safe_workspace_service import (  # noqa: E402
    SafeWorkspaceService,
    is_session_coordination_file,
    sha256_file,
)
from app.services.workspace_backup_service import workspace_backup_service  # noqa: E402


def source_snapshot(root: Path) -> dict[str, str]:
    """Hash every regular file so the pilot can prove the supplied copy stayed unchanged."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[path.relative_to(root).as_posix()] = sha256_file(path)
    return snapshot


def workspace_backup_snapshot(root: Path) -> dict[str, str]:
    """Mirror WorkspaceBackupService exclusions for a like-for-like restore check."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.name.endswith(".tmp"):
            continue
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == "Recovery":
            continue
        if is_session_coordination_file(relative):
            continue
        snapshot[relative.as_posix()] = sha256_file(path)
    return snapshot


def inspect_ocr_results(results: list[dict]) -> dict:
    supported = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
    ocr_files = [item for item in results if str(item.get("extension", "")).lower() in supported]
    failed_count = sum(
        item.get("extraction_method") == "ocr_failed" or int(item.get("text_length") or 0) <= 0
        for item in ocr_files
    )
    languages = {
        str(item.get("language") or "")
        for item in ocr_files
        if item.get("language")
    }
    has_myanmar = bool(languages & {"mya", "mya+eng"})
    has_english = bool(languages & {"eng", "mya+eng"})
    return {
        "files_total": len(ocr_files),
        "files_failed": failed_count,
        "languages_detected": sorted(languages),
        "myanmar_detected": has_myanmar,
        "english_detected": has_english,
        "representative_ocr_passed": bool(ocr_files) and failed_count == 0 and has_myanmar and has_english,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Doka Personal Local real-machine pilot gate.")
    parser.add_argument("--source", required=True, help="COPY of representative office data; never the original source.")
    parser.add_argument("--workspace", required=True, help="Dedicated empty Doka WORKING_ROOT for this pilot run.")
    parser.add_argument("--backup-root", required=True, help="Dedicated backup root for this pilot run.")
    parser.add_argument("--output", required=True, help="Path for the privacy-safe JSON evidence report.")
    parser.add_argument("--require-ocr", action="store_true", help="Require OCR tooling and successful Myanmar + English OCR on representative image/PDF files.")
    parser.add_argument("--apply-safe", action="store_true", help="Apply only non-review organization proposals after the plan is generated.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    pilot_workspace = Path(args.workspace).expanduser().resolve()
    pilot_backup_root = Path(args.backup_root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Source copy does not exist: {source}")

    # Refuse an obviously unsafe source/workspace relationship before doing any work.
    if pilot_workspace == source or pilot_workspace.is_relative_to(source) or source.is_relative_to(pilot_workspace):
        raise SystemExit("Refusing pilot: source and WORKING_ROOT overlap.")
    if pilot_backup_root == source or pilot_backup_root.is_relative_to(source):
        raise SystemExit("Refusing pilot: source and BACKUP_ROOT overlap.")
    pilot_workspace.mkdir(parents=True, exist_ok=True)
    pilot_backup_root.mkdir(parents=True, exist_ok=True)
    if any(pilot_workspace.iterdir()):
        raise SystemExit("Pilot WORKING_ROOT must be empty before the run.")
    settings.SOURCE_ROOT = source
    settings.WORKING_ROOT = pilot_workspace
    settings.FINAL_ROOT = pilot_workspace / "Final"
    settings.QUARANTINE_ROOT = pilot_workspace / "Quarantine"
    settings.BACKUP_ROOT = pilot_backup_root
    workspace = settings.WORKING_ROOT.resolve()
    if source == workspace or source.is_relative_to(workspace) or workspace.is_relative_to(source):
        raise SystemExit("Refusing pilot: source and WORKING_ROOT overlap.")

    before = source_snapshot(source)
    source_symlinks = [str(path.relative_to(source)) for path in source.rglob("*") if path.is_symlink()]
    if source_symlinks:
        raise SystemExit(f"Acceptance source contains symbolic links: {source_symlinks[:10]}")
    if not before:
        print(json.dumps({
            "gate": "blocked",
            "reason": "The supplied source copy contains no regular files to validate.",
        }, ensure_ascii=False, indent=2))
        return 2

    started_at = time.monotonic()
    ocr = ocr_validation_service.validate()
    if args.require_ocr and not ocr.get("available"):
        print(json.dumps({"gate": "blocked", "reason": "OCR unavailable", "ocr": ocr}, ensure_ascii=False, indent=2))
        return 2

    service = SafeWorkspaceService()
    status = service.create_import(str(source))
    session_id = status["session_id"]
    status = service.run_import(session_id)
    if status["state"] not in {"completed", "completed_with_errors"}:
        raise SystemExit(f"Import did not complete: {status}")

    scan = service.scan(session_id)
    understanding = document_understanding_service.analyze(session_id)
    understanding_details = service._read(service._json_path(session_id, "understanding.json"))
    ocr_results = inspect_ocr_results(understanding_details.get("results", []))
    plan = organization_planner.plan(session_id)

    apply_result = None
    if args.apply_safe:
        safe_paths = [
            p["relative_path"]
            for p in plan.get("proposals", [])
            if p.get("action") == "suggest_move" and p.get("target")
        ]
        apply_result = organization_planner.apply(session_id, safe_paths) if safe_paths else {"results": []}

    workspace_before_backup = workspace_backup_snapshot(workspace)
    backup = workspace_backup_service.create(session_id=session_id)
    backup_name = Path(backup["archive"]).name
    backup_verify = workspace_backup_service.verify(backup_name)
    recovery = workspace_backup_service.restore_to_recovery(backup_name, confirm=True)
    recovery_root = Path(recovery["recovery_path"])
    try:
        recovery_snapshot = source_snapshot(recovery_root)
        recovery_verified = (
            backup_verify.get("verified") is True
            and recovery_snapshot == workspace_before_backup
            and recovery.get("active_workspace_changed") is False
        )
    finally:
        shutil.rmtree(recovery_root, ignore_errors=True)
    after = source_snapshot(source)

    source_unchanged = before == after
    import_complete = (
        status.get("state") == "completed"
        and status.get("files_failed", 0) == 0
        and status.get("files_verified", 0) == status.get("files_total", -1)
    )
    scan_complete = (
        scan.get("files_unreadable", 0) == 0
        and scan.get("files_readable", 0) == scan.get("files_total", -1)
    )
    ocr_gate_passed = not args.require_ocr or (
        ocr.get("available") is True and ocr_results["representative_ocr_passed"]
    )
    gate_reasons = []
    if not source_unchanged:
        gate_reasons.append("The supplied source copy changed during the pilot.")
    if not import_complete:
        gate_reasons.append("Not every source file was imported and SHA-256 verified.")
    if not scan_complete:
        gate_reasons.append("The workspace scan reported unreadable or unaccounted files.")
    if not recovery_verified:
        gate_reasons.append("Backup verification or Recovery manifest comparison failed.")
    if not ocr_gate_passed:
        gate_reasons.append("Required Myanmar + English OCR was not successfully exercised on representative image/PDF files.")
    gate_passed = source_unchanged and import_complete and scan_complete and recovery_verified and ocr_gate_passed
    elapsed_seconds = round(time.monotonic() - started_at, 3)
    report = {
        "gate": "passed" if gate_passed else "failed",
        "gate_reasons": gate_reasons,
        "session_id": session_id,
        "source": {"file_count": len(before), "path_recorded": False},
        "source_unchanged": source_unchanged,
        "source_files": len(before),
        "elapsed_seconds": elapsed_seconds,
        "import": {
            "state": status.get("state"),
            "files_total": status.get("files_total"),
            "files_verified": status.get("files_verified"),
            "files_failed": status.get("files_failed"),
        },
        "scan": {
            "files_total": scan.get("files_total"),
            "files_readable": scan.get("files_readable"),
            "files_unreadable": scan.get("files_unreadable"),
            "exact_duplicate_groups": scan.get("exact_duplicate_groups"),
            "filename_collision_groups": scan.get("filename_collision_groups"),
        },
        "understanding": {
            "analyzed_files": understanding.get("analyzed_files"),
            "ai_used": understanding.get("ai_used"),
        },
        "organization_plan": {
            "proposals_total": plan.get("proposals_total"),
            "review_required": plan.get("review_required"),
            "requires_user_approval": plan.get("requires_user_approval"),
        },
        "ocr": {**ocr, **ocr_results, "required": args.require_ocr, "gate_passed": ocr_gate_passed},
        "backup": {
            "archive_filename": Path(str(backup.get("archive", ""))).name,
            "sha256": backup.get("sha256"),
            "verified": backup_verify.get("verified"),
            "recovery_verified": recovery_verified,
            "recovery_active_workspace_changed": recovery.get("active_workspace_changed"),
        },
        "apply_safe": apply_result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["evidence_report_filename"] = output.name
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if gate_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
