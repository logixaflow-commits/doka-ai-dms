#!/usr/bin/env python3
"""Repository-local structural and evidence-completeness audit for Doka.

This tool never treats missing credentials, live checks, or real-world evidence as
success. It reports those gaps separately from repository-structure failures.
It uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "README.md",
    "CURRENT_STATE.md",
    "ROADMAP.md",
    "TOOL.md",
    "docs/TESTING.md",
    "docs/DEPLOYMENT.md",
)
REQUIRED_GATE_NUMBERS = (3, 4, 5, 6, 8, 9, 10, 11, 12)
EVIDENCE_REFERENCE_RE = re.compile(r"(?<![\w./-])((?:Phase0_Evidence|phase0_evidence)/[^\s)`<>\]]+)", re.I)


def _check(name: str, ok: bool, detail: str, category: str = "structure") -> dict[str, str]:
    return {
        "name": name,
        "status": "PASS" if ok else ("NEEDS_REVIEW" if category == "evidence" else "FAIL"),
        "category": category,
        "detail": detail,
    }


def audit_repo(root: Path) -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, str]] = []
    contents: dict[str, str] = {}

    for relative in REQUIRED_FILES:
        path = root / relative
        exists = path.is_file()
        checks.append(_check(
            f"required-file:{relative}", exists,
            f"Found {relative}." if exists else f"Required canonical file is missing: {relative}.",
        ))
        if exists:
            try:
                contents[relative] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                checks.append(_check(f"readable-file:{relative}", False, f"Cannot read {relative}: {exc}"))
            else:
                checks.append(_check(f"readable-file:{relative}", True, f"Read {relative} as UTF-8."))

    roadmap = contents.get("ROADMAP.md", "")
    for gate in REQUIRED_GATE_NUMBERS:
        # Accept common forms such as "Gate 10", "10. Gate", or a table row.
        pattern = re.compile(rf"(?:\bGate\s+{gate}\b|^\s*{gate}[.)]\s*Gate\b)", re.I | re.M)
        found = bool(pattern.search(roadmap))
        checks.append(_check(
            f"roadmap-gate:{gate}", found,
            f"Gate {gate} is referenced in ROADMAP.md." if found else
            f"Gate {gate} is not clearly referenced in ROADMAP.md; reconcile the canonical roadmap.",
        ))

    current = contents.get("CURRENT_STATE.md", "")
    has_next_action = bool(re.search(r"NEXT ACTION|NEXT ACTIONS|Next action", current, re.I))
    checks.append(_check(
        "current-state-next-action", has_next_action,
        "CURRENT_STATE.md contains a next-action marker." if has_next_action else
        "CURRENT_STATE.md has no obvious NEXT ACTION marker; add one so the next step is discoverable.",
    ))

    # Existing evidence references are checked as an advisory only. Historical
    # references may legitimately point to archived or externally-held evidence.
    missing_evidence: list[str] = []
    evidence_docs = {**contents}
    for relative in ("ROADMAP.md", "CURRENT_STATE.md", "docs/TESTING.md", "docs/DEPLOYMENT.md"):
        path = root / relative
        if path.is_file() and relative not in evidence_docs:
            try:
                evidence_docs[relative] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
    for source, text in evidence_docs.items():
        for match in EVIDENCE_REFERENCE_RE.finditer(text):
            raw = match.group(1).rstrip(".,;:")
            # Strip optional line anchors and query-like suffixes before checking.
            target = raw.split("#", 1)[0].split("?", 1)[0]
            if target and not (root / target).exists():
                missing_evidence.append(f"{source}: {target}")
    unique_missing = sorted(set(missing_evidence))
    checks.append(_check(
        "evidence-reference-presence", not unique_missing,
        "All referenced Phase0_Evidence paths exist." if not unique_missing else
        f"{len(unique_missing)} evidence path reference(s) were not found. Review the list in this report; "
        "historical or externally-held evidence may be intentional.",
        category="evidence",
    ))

    failures = sum(item["status"] == "FAIL" for item in checks)
    evidence_gaps = sum(item["status"] == "NEEDS_REVIEW" for item in checks)
    return {
        "schema_version": 1,
        "audit": "doka-self-audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root),
        "summary": {
            "status": "FAIL" if failures else ("NEEDS_EVIDENCE" if evidence_gaps else "PASS"),
            "checks": len(checks),
            "passed": sum(item["status"] == "PASS" for item in checks),
            "failed": failures,
            "needs_review": evidence_gaps,
        },
        "checks": checks,
        "missing_evidence_references": unique_missing,
        "interpretation": (
            "This is a structural/documentation preflight, not release approval. "
            "A PASS does not prove runtime, security, OCR, browser, recovery, or provider acceptance."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="Repository root (defaults to the checked-out repository).")
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    parser.add_argument("--strict-evidence", action="store_true",
                        help="Return a non-zero exit code when referenced evidence paths are missing.")
    args = parser.parse_args(argv)

    report = audit_repo(args.root)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else args.root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["summary"]["failed"]:
        return 1
    if args.strict_evidence and report["summary"]["needs_review"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
