import os
from pathlib import Path


def safe_read(path: str | Path) -> str:
    requested_path = Path(path)
    allowed_root = Path(os.getenv("FILE_ROOT", "./data")).resolve()
    resolved_path = requested_path.resolve(strict=True)

    if not resolved_path.is_relative_to(allowed_root):
        raise PermissionError("Requested file is outside the allowed file root.")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(resolved_path, flags), "r", encoding="utf-8") as source:
        content = source.read()
    if requested_path.resolve(strict=True) != resolved_path:
        raise PermissionError("Requested file changed while being read.")
    return content
