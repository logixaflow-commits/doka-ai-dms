#!/usr/bin/env python3
"""Fail-closed D1 migration manifest verifier.

This tool does not apply migrations. It verifies that the checked-in migration
set is ordered, uniquely numbered, and matches a reviewed SHA-256 manifest.
Production apply remains an explicit deployment operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MIGRATION_RE = re.compile(r"^(\d{4})_[a-z0-9][a-z0-9_-]*\.sql$")


def migration_files(directory: Path) -> list[Path]:
    files = []
    for path in directory.glob("*.sql"):
        if MIGRATION_RE.match(path.name):
            files.append(path)
    return sorted(files, key=lambda p: int(MIGRATION_RE.match(p.name).group(1)))


def manifest_for(files: list[Path]) -> list[dict[str, str | int]]:
    return [
        {
            "number": int(MIGRATION_RE.match(path.name).group(1)),
            "name": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in files
    ]


def validate(files: list[Path], manifest: list[dict[str, str | int]]) -> None:
    numbers = [int(MIGRATION_RE.match(p.name).group(1)) for p in files]
    if numbers != list(range(1, len(numbers) + 1)):
        raise SystemExit(
            f"migration sequence must be contiguous from 0001; found {numbers}"
        )
    if manifest != manifest_for(files):
        raise SystemExit("migration manifest checksum mismatch; review/apply is blocked")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--directory",
        default="cloudflare_worker/migrations",
        type=Path,
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    files = migration_files(args.directory)
    if not files:
        raise SystemExit("no numbered D1 migrations found")

    generated = manifest_for(files)
    if args.write:
        if not args.manifest:
            raise SystemExit("--write requires --manifest")
        args.manifest.write_text(
            json.dumps(generated, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0

    if not args.manifest:
        raise SystemExit("--manifest is required for verification")
    try:
        expected = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("unable to read D1 migration manifest") from exc
    validate(files, expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
