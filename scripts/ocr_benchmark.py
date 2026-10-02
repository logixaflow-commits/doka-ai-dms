#!/usr/bin/env python3
"""Run an OCR accuracy benchmark against a COPY of representative office scans."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "web-platform" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ocr_benchmark import run_ocr_benchmark  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure OCR CER/WER on a copied sample set.")
    parser.add_argument("--root", required=True, help="Directory containing copied OCR samples.")
    parser.add_argument("--manifest", required=True, help="JSON manifest with relative paths and reference text.")
    parser.add_argument("--output", required=True, help="Path to write the privacy-scrubbed JSON report.")
    args = parser.parse_args()

    report = run_ocr_benchmark(Path(args.root), Path(args.manifest))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "report": str(output),
        "sample_count": report["sample_count"],
        "scored_count": report["scored_count"],
        "error_count": report["error_count"],
        "summary_by_language": report["summary_by_language"],
        "privacy": report["privacy"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
