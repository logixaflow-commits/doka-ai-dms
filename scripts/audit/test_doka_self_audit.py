"""Unit tests for the repository-local Doka self-audit."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from doka_self_audit import audit_repo  # noqa: E402

REQUIRED = (
    "README.md", "CURRENT_STATE.md", "ROADMAP.md", "TOOL.md",
    "docs/TESTING.md", "docs/DEPLOYMENT.md",
)


class SelfAuditTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        for relative in REQUIRED:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Documentation placeholder.\n", encoding="utf-8")
        (root / "CURRENT_STATE.md").write_text(
            "## NEXT ACTION\nReconcile pending release evidence.\n", encoding="utf-8"
        )
        (root / "ROADMAP.md").write_text(
            "\n".join(f"- Gate {n} — pending evidence" for n in (3, 4, 5, 6, 8, 9, 10, 11, 12)),
            encoding="utf-8",
        )

    def test_complete_structure_passes_without_claiming_release_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_repo(root)
            report = audit_repo(root)
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertEqual(report["summary"]["status"], "PASS")
            self.assertIn("not release approval", report["interpretation"])

    def test_missing_canonical_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_repo(root)
            (root / "TOOL.md").unlink()
            report = audit_repo(root)
            self.assertGreater(report["summary"]["failed"], 0)
            self.assertEqual(report["summary"]["status"], "FAIL")

    def test_missing_gate_is_a_structural_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_repo(root)
            (root / "ROADMAP.md").write_text("- Gate 3\n", encoding="utf-8")
            report = audit_repo(root)
            failed = [c["name"] for c in report["checks"] if c["status"] == "FAIL"]
            self.assertIn("roadmap-gate:12", failed)

    def test_missing_evidence_reference_is_advisory_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_repo(root)
            (root / "CURRENT_STATE.md").write_text(
                "## NEXT ACTION\nEvidence: Phase0_Evidence/not-created.json\n", encoding="utf-8"
            )
            report = audit_repo(root)
            self.assertEqual(report["summary"]["status"], "NEEDS_EVIDENCE")
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertEqual(len(report["missing_evidence_references"]), 1)


if __name__ == "__main__":
    unittest.main()
