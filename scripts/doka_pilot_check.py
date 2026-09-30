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
import os
import sys
from pathlib import Path

# Make the local backend importable when this script is run from repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "web-platform" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.document_understanding_service import document_understanding_service  # noqa: E402
from app.services.ocr_validation_service import ocr_validation_service  # noqa: E402
from app.services.organization_planner import organization_planner  # noqa: E402
from app.services.safe_workspace_service import SafeWorkspaceService, sha256_file  # noqa: E402
from app.services.workspace_backup_service import workspace_backup_service  # noqa: E402


def source_snapshot(root: Path) -> dict[str, str]:
    """Hash every regular file so the pilot can prove the source stayed unchanged."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[path.relative_to(root).as_posix()] = sha256_file(path)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Doka Personal Local real-machine pilot gate.")
    parser.add_argument("--source", required=True, help="COPY of representative office data; never the original source.")
    parser.add_argument("--require-ocr", action="store_true", help="Fail the gate when Myanmar/English OCR is unavailable.")
    parser.add_argument("--apply-safe", action="store_true", help="Apply only non-review organization proposals after the plan is generated.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Source copy does not exist: {source}")

    # Refuse an obviously unsafe source/workspace relationship before doing any work.
    workspace = settings.WORKING_ROOT.resolve()
    if source == workspace or source.is_relative_to(workspace) or workspace.is_relative_to(source):
        raise SystemExit("Refusing pilot: source and WORKING_ROOT overlap.")

    before = source_snapshot(source)
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
    plan = organization_planner.plan(session_id)

    apply_result = None
    if args.apply_safe:
        safe_paths = [
            p["relative_path"]
            for p in plan.get("proposals", [])
            if p.get("action") == "suggest_move" and p.get("target")
        ]
        apply_result = organization_planner.apply(session_id, safe_paths) if safe_paths else {"results": []}

    backup = workspace_backup_service.create()
    after = source_snapshot(source)

    source_unchanged = before == after
    report = {
        "gate": "passed" if source_unchanged else "failed",
        "session_id": session_id,
        "source": str(source),
        "source_unchanged": source_unchanged,
        "source_files": len(before),
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
        "ocr": ocr,
        "backup": {
            "archive": backup.get("archive"),
            "sha256": backup.get("sha256"),
        },
        "apply_safe": apply_result,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if source_unchanged else 3


if __name__ == "__main__":
    raise SystemExit(main())
