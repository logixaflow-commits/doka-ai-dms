"""Small, dependency-light helpers for safe bounded upload handling."""
from __future__ import annotations

from typing import BinaryIO, Protocol


class AsyncReadableUpload(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


class UploadTooLargeError(ValueError):
    """Raised when a streamed upload exceeds its configured byte limit."""


def safe_upload_filename(filename: str | None, *, max_length: int = 180) -> str:
    """Return a bounded basename with path separators/control chars removed."""
    if max_length < 1:
        raise ValueError("max_length must be positive")
    name = (filename or "document").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(
        char for char in name
        if ord(char) >= 32 and ord(char) != 127 and char not in '<>:"|?*'
    )
    return (name.strip(" .") or "document")[:max_length]


async def stream_upload_bounded(
    upload: AsyncReadableUpload,
    destination: BinaryIO,
    *,
    max_bytes: int,
    chunk_size: int = 1024 * 1024,
) -> int:
    """Copy an async upload in bounded chunks; reject overflow without buffering all bytes."""
    if max_bytes < 1 or chunk_size < 1:
        raise ValueError("max_bytes and chunk_size must be positive")
    total_size = 0
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            return total_size
        total_size += len(chunk)
        if total_size > max_bytes:
            raise UploadTooLargeError("Upload exceeds configured byte limit")
        destination.write(chunk)
