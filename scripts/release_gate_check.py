#!/usr/bin/env python3
"""Evaluate Doka release gates from privacy-safe evidence JSON files.

This tool never turns missing live evidence into PASS. It is intentionally
strict so CI/readiness checks cannot accidentally become a release claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_GATES = tuple(range(1, 13))


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: evidence must be a JSON object")
    return data


def gate_ready(gate: int, evidence: dict[int, dict[str, Any]]) -> bool:
    item = evidence.get(gate, {})
    if gate == 3:
        return item.get("gate_ready") is True
    if gate == 4:
        return item.get("passed") is True
    if gate == 5:
        return item.get("source_unchanged") is True and item.get("recovery_verified") is True
    if gate == 6:
        return item.get("recovery_verified") is True and item.get("rto_seconds") is not None
    if gate == 7:
        return item.get("passed") is True
    if gate == 8:
        return all(gate_ready(g, evidence) for g in range(1, 8))
    if gate == 9:
        return item.get("gate9_ready") is True
    if gate == 10:
        return item.get("checks", {}).get("two_user_isolation") is True
    if gate == 11:
        checks = item.get("checks", {})
        return all(checks.get(name) is True for name in (
            "supabase_storage", "b2_recovery", "cloudinary_application_path",
            "google_drive_recovery", "exact_50_mib_boundary",
        ))
    if gate == 12:
        return all(gate_ready(g, evidence) for g in range(8, 12))
    return item.get("passed") is True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.evidence_dir)
    evidence: dict[int, dict[str, Any]] = {}
    for gate in REQUIRED_GATES:
        candidates = sorted(root.glob(f"gate-{gate}-*.json")) + sorted(root.glob(f"gate-{gate}.json"))
        if candidates:
            evidence[gate] = load(candidates[-1])

    status = {
        f"gate_{gate}": {
            "status": "PASS" if gate_ready(gate, evidence) else "PENDING",
            "evidence_present": gate in evidence,
        }
        for gate in REQUIRED_GATES
    }
    result = {
        "schema_version": 1,
        "release_claim_allowed": status["gate_12"]["status"] == "PASS",
        "gates": status,
        "policy": {
            "missing_live_evidence_is_pending": True,
            "code_or_ci_alone_is_not_release_evidence": True,
            "tokens_and_secrets_recorded": False,
        },
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["release_claim_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
