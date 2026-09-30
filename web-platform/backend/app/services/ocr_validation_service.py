from __future__ import annotations

import shutil
import subprocess
from typing import Any

from app.core.config import settings


class OCRValidationService:
    def validate(self) -> dict[str, Any]:
        executable = settings.TESSERACT_CMD or "tesseract"
        path = shutil.which(executable) if not executable.startswith("/") else executable
        result: dict[str, Any] = {
            "available": False,
            "executable": path or executable,
            "myanmar_language": settings.MYANMAR_LANG,
            "english_language": "eng",
            "languages": [],
            "checks": [],
        }
        if not path:
            result["checks"].append({"name": "tesseract", "ok": False, "detail": "Tesseract executable not found"})
            return result
        result["checks"].append({"name": "tesseract", "ok": True, "detail": path})
        try:
            proc = subprocess.run([path, "--list-langs"], capture_output=True, text=True, timeout=10, check=False)
            langs = [line.strip() for line in proc.stdout.splitlines()[1:] if line.strip()]
            result["languages"] = langs
            mya_ok = settings.MYANMAR_LANG in langs
            eng_ok = "eng" in langs
            result["checks"].append({"name": "english", "ok": eng_ok, "detail": "eng language data"})
            result["checks"].append({"name": "myanmar", "ok": mya_ok, "detail": f"{settings.MYANMAR_LANG} language data"})
            result["available"] = eng_ok and mya_ok
        except Exception as exc:
            result["checks"].append({"name": "language_data", "ok": False, "detail": str(exc)})
        return result


ocr_validation_service = OCRValidationService()
