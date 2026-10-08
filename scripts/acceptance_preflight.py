#!/usr/bin/env python3
"""Privacy-safe runtime preflight for Doka acceptance execution.

The preflight reports capability presence only; it never records credentials,
full environment values, source paths, or OCR text.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PYTHON_MODULES = (
    "fastapi", "httpx", "loguru", "yaml", "jwt", "argon2", "bcrypt",
    "pytesseract", "PIL", "numpy", "cv2", "pdf2image", "pdfplumber",
    "openpyxl", "boto3", "pytest", "pytest_asyncio",
)
CLOUD_ENV = (
    "DOKA_CLOUD_BASE_URL",
    "DOKA_CLOUD_USER_A_TOKEN",
    "DOKA_CLOUD_USER_B_TOKEN",
)
CLOUDFLARE_ENV = (
    "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "DOKA_D1_DATABASE_ID",
)

PROVIDER_ENV = (
    "SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_STORAGE_BUCKET",
    "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
    "R2_BUCKET", "R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
)

def command_version(command: str, *args: str) -> dict[str, object]:
    path = shutil.which(command)
    result: dict[str, object] = {"available": path is not None}
    if path is None:
        return result
    result["path_recorded"] = False
    try:
        proc = subprocess.run([path, *args], capture_output=True, text=True, timeout=15, check=False)
        line = (proc.stdout or proc.stderr).splitlines()
        result["version_available"] = proc.returncode == 0
        result["version_recorded"] = bool(line)
    except (OSError, subprocess.SubprocessError):
        result["version_available"] = False
    return result

def tesseract_languages() -> dict[str, object]:
    path = shutil.which("tesseract")
    if path is None:
        return {"available": False, "mya": False, "eng": False}
    try:
        proc = subprocess.run([path, "--list-langs"], capture_output=True, text=True, timeout=15, check=False)
        languages = set(proc.stdout.split())
        return {"available": proc.returncode == 0, "mya": "mya" in languages, "eng": "eng" in languages}
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "mya": False, "eng": False}

def module_report() -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in PYTHON_MODULES}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("local", "cloud", "all"), default="all")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    python_ok = sys.version_info >= (3, 11)
    commands = {
        "python": {"available": True, "version_ok": python_ok},
        "node": command_version("node", "--version"),
        "npm": command_version("npm", "--version"),
        "tesseract": command_version("tesseract", "--version"),
    }
    modules = module_report()
    evidence: dict[str, object] = {
        "schema_version": 1,
        "privacy": {
            "credential_values_recorded": False,
            "environment_values_recorded": False,
            "paths_recorded": False,
            "ocr_text_recorded": False,
        },
        "mode": args.mode,
        "python": {"major": sys.version_info.major, "minor": sys.version_info.minor, "version_ok": python_ok},
        "commands": commands,
        "python_modules": modules,
        "tesseract_languages": tesseract_languages(),
        "cloud_env_present": {name: bool(os.getenv(name, "").strip()) for name in CLOUD_ENV},
        "provider_env_present": {name: bool(os.getenv(name, "").strip()) for name in PROVIDER_ENV},
        "cloudflare_env_present": {name: bool(os.getenv(name, "").strip()) for name in CLOUDFLARE_ENV},
    }

    local_ready = (
        python_ok
        and commands["node"].get("available") is True
        and commands["npm"].get("available") is True
        and all(modules.values())
        and evidence["tesseract_languages"].get("available") is True
        and evidence["tesseract_languages"].get("mya") is True
        and evidence["tesseract_languages"].get("eng") is True
    )
    cloud_ready = all(evidence["cloud_env_present"].values())
    if args.mode == "local":
        ready = local_ready
    elif args.mode == "cloud":
        ready = cloud_ready
    else:
        ready = local_ready and cloud_ready
    evidence["local_ready"] = local_ready
    evidence["cloud_ready"] = cloud_ready
    evidence["ready"] = ready

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if ready else 2

if __name__ == "__main__":
    raise SystemExit(main())
