from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.core.upload_safety import (
    UploadTooLargeError,
    safe_upload_filename,
    stream_upload_bounded,
)


class ChunkedUpload:
    def __init__(self, chunks: list[bytes]):
        self._chunks = iter(chunks)

    async def read(self, _size: int) -> bytes:
        return next(self._chunks, b"")


def test_safe_upload_filename_strips_paths_controls_and_platform_metacharacters():
    assert safe_upload_filename("../../folder\\report\r\n:final?.pdf") == "reportfinal.pdf"
    assert safe_upload_filename("... ") == "document"
    assert len(safe_upload_filename("x" * 300)) == 180


def test_safe_upload_filename_rejects_invalid_bound():
    with pytest.raises(ValueError):
        safe_upload_filename("document.pdf", max_length=0)


@pytest.mark.asyncio
async def test_stream_upload_bounded_rejects_overflow_without_writing_over_limit():
    upload = ChunkedUpload([b"ab", b"cd"])
    destination = io.BytesIO()

    with pytest.raises(UploadTooLargeError):
        await stream_upload_bounded(upload, destination, max_bytes=3, chunk_size=2)

    assert destination.getvalue() == b"ab"


@pytest.mark.asyncio
async def test_stream_upload_bounded_writes_exact_bytes_in_chunks():
    upload = ChunkedUpload([b"1234", b"5678"])
    destination = io.BytesIO()

    size = await stream_upload_bounded(upload, destination, max_bytes=8, chunk_size=4)

    assert size == 8
    assert destination.getvalue() == b"12345678"


def test_version_route_uses_bounded_stream_and_always_cleans_temp_file():
    route = Path(__file__).parents[1] / "app" / "api" / "routes" / "versions.py"
    source = route.read_text(encoding="utf-8")
    assert "stream_upload_bounded(" in source
    assert "status.HTTP_413_REQUEST_ENTITY_TOO_LARGE" in source
    assert "await file.close()" in source
    assert "os.unlink(tmp_file_path)" in source
    assert "original_filename=safe_name" in source
