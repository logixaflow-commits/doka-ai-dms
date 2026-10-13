from __future__ import annotations

import asyncio
import hashlib
from types import SimpleNamespace

import pytest

from stream_hash import hash_response_stream


class FakeUint8Array:
    def __init__(self, data: bytes):
        self.data = data
        self.length = len(data)

    def __getitem__(self, index: int) -> int:
        return self.data[index]


class FakeReader:
    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)
        self.cancelled = False
        self.released = False

    async def read(self):
        if not self.chunks:
            return SimpleNamespace(done=True, value=None)
        return SimpleNamespace(done=False, value=FakeUint8Array(self.chunks.pop(0)))

    async def cancel(self):
        self.cancelled = True

    def releaseLock(self):
        self.released = True


def run(coro):
    return asyncio.run(coro)


def test_stream_hash_matches_sha256_across_multiple_chunks():
    chunks = [b"document ", b"payload", b" plus a tail"]
    reader = FakeReader(chunks)

    result = run(hash_response_stream(reader, max_bytes=1024))

    assert result == {
        "size_bytes": sum(map(len, chunks)),
        "sha256": hashlib.sha256(b"".join(chunks)).hexdigest(),
    }
    assert reader.released is True
    assert reader.cancelled is False


def test_stream_hash_cancels_reader_when_actual_bytes_exceed_limit():
    reader = FakeReader([b"1234", b"5678"])

    with pytest.raises(ValueError, match="verification limit"):
        run(hash_response_stream(reader, max_bytes=6))

    assert reader.cancelled is True
    assert reader.released is True


def test_stream_hash_accepts_empty_body():
    reader = FakeReader([])

    result = run(hash_response_stream(reader, max_bytes=1))

    assert result == {"size_bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}
