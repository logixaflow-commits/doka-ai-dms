#!/usr/bin/env python3
"""Export the dedicated Cloud API OpenAPI schema as a CI artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "web-platform" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    from app.cloud_main import app

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/cloud-openapi.json")
    if not output.is_absolute():
        output = Path.cwd() / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported Cloud API OpenAPI schema to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
