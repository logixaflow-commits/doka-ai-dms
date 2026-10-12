#!/usr/bin/env python3
"""Fail-closed preflight for Personal Local acceptance; never prints secrets or paths."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REQUIRED_ENV = (
    "DOKA_PILOT_SOURCE",
    "DOKA_PILOT_WORKSPACE",
    "DOKA_PILOT_BACKUPS",
    "DOKA_OCR_ROOT",
    "DOKA_OCR_MANIFEST",
    "BOOTSTRAP_ADMIN_PASSWORD",
)


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _command_output(command: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
        return proc.returncode, (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def validate_environment(env: dict[str, str], evidence_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    missing = [name for name in REQUIRED_ENV if not env.get(name, "").strip()]
    if missing:
        errors.append("Missing required environment variables: " + ", ".join(missing))
    password = env.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if password and len(password) < 16:
        errors.append("BOOTSTRAP_ADMIN_PASSWORD must contain at least 16 characters.")
    if env.get("AI_ENABLED", "false").strip().lower() == "true":
        errors.append("AI_ENABLED must be false for the initial local acceptance run.")
    if env.get("AI_EXTERNAL_PROCESSING_CONSENT", "false").strip().lower() == "true":
        errors.append("AI_EXTERNAL_PROCESSING_CONSENT must be false for the initial local acceptance run.")
    if env.get("ALLOW_SOURCE_WRITE", "false").strip().lower() == "true":
        errors.append("ALLOW_SOURCE_WRITE must be false for the initial local acceptance run.")
    if env.get("ORIGINAL_READ_ONLY", "true").strip().lower() != "true":
        errors.append("ORIGINAL_READ_ONLY must be true for the initial local acceptance run.")

    if missing:
        return {"ready": False, "errors": errors, "privacy": {"paths_recorded": False, "secret_values_recorded": False}}

    path_names = {
        "source": "DOKA_PILOT_SOURCE",
        "workspace": "DOKA_PILOT_WORKSPACE",
        "backups": "DOKA_PILOT_BACKUPS",
        "ocr_root": "DOKA_OCR_ROOT",
        "manifest": "DOKA_OCR_MANIFEST",
    }
    paths: dict[str, Path] = {}
    for label, variable in path_names.items():
        candidate = Path(env[variable]).expanduser()
        if candidate.is_symlink():
            errors.append(f"{variable} must not be a symbolic link.")
        try:
            paths[label] = candidate.resolve(strict=(label in {"source", "ocr_root", "manifest"}))
        except (OSError, RuntimeError):
            errors.append(f"{variable} does not resolve to an accessible path.")

    try:
        evidence = evidence_root.expanduser().resolve()
    except (OSError, RuntimeError):
        evidence = evidence_root.expanduser().absolute()
        errors.append("Evidence directory does not resolve to an accessible path.")

    if errors and any(label not in paths for label in path_names):
        return {"ready": False, "errors": errors, "privacy": {"paths_recorded": False, "secret_values_recorded": False}}

    source = paths.get("source")
    workspace = paths.get("workspace")
    backups = paths.get("backups")
    ocr_root = paths.get("ocr_root")
    manifest = paths.get("manifest")
    if source and not source.is_dir():
        errors.append("DOKA_PILOT_SOURCE must be a directory containing a COPY of office data.")
    if ocr_root and not ocr_root.is_dir():
        errors.append("DOKA_OCR_ROOT must be a directory.")
    if manifest and not manifest.is_file():
        errors.append("DOKA_OCR_MANIFEST must be a regular file.")
    if source and source.is_dir():
        if not any(p.is_file() and not p.is_symlink() for p in source.rglob("*")):
            errors.append("DOKA_PILOT_SOURCE contains no regular files.")
        if any(p.is_symlink() for p in source.rglob("*")):
            errors.append("DOKA_PILOT_SOURCE contains symbolic links; remove them from the copied dataset.")
    for label, path in (("workspace", workspace), ("backups", backups)):
        if path and path.exists():
            if not path.is_dir():
                errors.append(f"DOKA_PILOT_{'WORKSPACE' if label == 'workspace' else 'BACKUPS'} must be a directory.")
            elif any(path.iterdir()):
                errors.append(f"DOKA_PILOT_{'WORKSPACE' if label == 'workspace' else 'BACKUPS'} must be empty before acceptance.")

    named_paths = {**paths, "evidence": evidence}
    for label, path in named_paths.items():
        if label == "manifest":
            continue
        for other_label, other in named_paths.items():
            if label >= other_label or other_label == "manifest":
                continue
            if path == other or _inside(path, other) or _inside(other, path):
                errors.append(f"{label} and {other_label} paths must be separate and non-overlapping.")

    if manifest and ocr_root and manifest.is_file() and ocr_root.is_dir():
        if _inside(manifest, ocr_root):
            errors.append("DOKA_OCR_MANIFEST must be stored outside the OCR sample directory.")
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            samples = data.get("samples") if isinstance(data, dict) else None
            if not isinstance(samples, list) or not samples:
                errors.append("OCR manifest must contain a non-empty samples array.")
            else:
                for index, sample in enumerate(samples):
                    if not isinstance(sample, dict) or not isinstance(sample.get("reference"), str) or not sample["reference"].strip():
                        errors.append(f"OCR manifest sample {index + 1} has no reference text.")
                        continue
                    rel = Path(str(sample.get("path", "")))
                    if rel.is_absolute() or not str(rel) or any(part in {"", ".", ".."} for part in rel.parts):
                        errors.append(f"OCR manifest sample {index + 1} has an invalid relative path.")
                        continue
                    sample_path = (ocr_root / rel).resolve(strict=False)
                    if not _inside(sample_path, ocr_root) or sample_path.is_symlink() or not sample_path.is_file():
                        errors.append(f"OCR manifest sample {index + 1} does not resolve to a regular file inside OCR root.")
        except (OSError, json.JSONDecodeError):
            errors.append("OCR manifest cannot be read as valid JSON.")

    py_ok = sys.version_info[:2] == (3, 13)
    if not py_ok:
        errors.append("Use Python 3.13 for the documented local acceptance environment.")
    node_path = shutil.which("node")
    if not node_path:
        errors.append("Node.js is not available.")
    else:
        code, version = _command_output([node_path, "--version"])
        if code != 0 or not version.startswith("v24."):
            errors.append("Use Node.js 24.x for the documented frontend environment.")
    npm_ok = shutil.which("npm") is not None
    if not npm_ok:
        errors.append("npm is not available.")
    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        errors.append("Tesseract OCR is not available.")
    else:
        code, languages = _command_output([tesseract_path, "--list-langs"])
        if code != 0:
            errors.append("Tesseract language list could not be read.")
        else:
            installed = set(languages.split())
            if "eng" not in installed or "mya" not in installed:
                errors.append("Tesseract must have both eng and mya language packs installed.")

    return {
        "schema_version": 1,
        "ready": not errors,
        "errors": errors,
        "runtime": {
            "python_313": py_ok,
            "node_24": bool(node_path and _command_output([node_path, "--version"])[1].startswith("v24.")),
            "npm_available": npm_ok,
            "tesseract_eng_and_mya": bool(tesseract_path and (lambda out: out[0] == 0 and {"eng", "mya"}.issubset(set(out[1].split())))(_command_output([tesseract_path, "--list-langs"]))),
        },
        "privacy": {"paths_recorded": False, "secret_values_recorded": False, "ocr_text_recorded": False},
    }


def _safe_report_path(output: Path, env: dict[str, str], evidence_root: Path) -> bool:
    """Prevent the generated report from overwriting or entering any input/evidence tree."""
    try:
        destination = output.expanduser().resolve()
        evidence = evidence_root.expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    protected: list[Path] = [evidence]
    for variable in REQUIRED_ENV:
        value = env.get(variable, "").strip()
        if not value or variable == "BOOTSTRAP_ADMIN_PASSWORD":
            continue
        try:
            protected.append(Path(value).expanduser().resolve())
        except (OSError, RuntimeError):
            return False
    for root in protected:
        if destination == root or _inside(destination, root) or _inside(root, destination):
            return False
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True, help="Dedicated evidence directory, separate from all inputs.")
    parser.add_argument("--output", help="Optional JSON report path outside all input directories.")
    args = parser.parse_args()
    report = validate_environment(dict(os.environ), Path(args.evidence_root))
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).expanduser()
        if output.is_symlink() or not _safe_report_path(output, dict(os.environ), Path(args.evidence_root)):
            print("Refusing to write preflight report inside or over a protected input/evidence path.", file=sys.stderr)
            return 2
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
