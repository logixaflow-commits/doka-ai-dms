#!/usr/bin/env python3
"""Prepare a deterministic exact-50-MiB cloud acceptance fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SIZE = 50 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    block = b"DOKA-CLOUD-50MIB-ACCEPTANCE\n"
    remaining = SIZE
    with output.open("wb") as fh:
        while remaining:
            chunk = block if remaining >= len(block) else block[:remaining]
            fh.write(chunk)
            remaining -= len(chunk)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "filename": output.name,
        "size_bytes": SIZE,
        "sha256": digest,
        "privacy": {"secrets_recorded": False},
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
