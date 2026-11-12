"""Bounded-memory streaming hash helpers shared by the Cloudflare Worker."""
from __future__ import annotations

import hashlib


async def hash_response_stream(reader, max_bytes: int, part_size_bytes: int | None = None) -> dict[str, str | int | list[str]]:
    """Hash a JS ReadableStream reader without buffering the complete response.

    When part_size_bytes is supplied, also return SHA-256 digests for exact
    sequential part boundaries. memoryview slices avoid copying input chunks.
    """
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    if part_size_bytes is not None and part_size_bytes <= 0:
        raise ValueError("part_size_bytes must be positive")

    digest = hashlib.sha256()
    part_digest = hashlib.sha256() if part_size_bytes else None
    part_hashes: list[str] = []
    part_bytes = 0
    size_bytes = 0
    try:
        while True:
            chunk_result = await reader.read()
            if bool(chunk_result.done):
                break
            chunk = chunk_result.value
            chunk_length = int(chunk.length)
            size_bytes += chunk_length
            if size_bytes > max_bytes:
                await reader.cancel()
                raise ValueError("Binary response exceeds the configured verification limit")
            py_chunk = chunk.to_py()
            view = memoryview(py_chunk)
            if view.format != "B":
                view = view.cast("B")
            if view.nbytes != chunk_length:
                raise ValueError("Stream chunk conversion length mismatch")

            if part_size_bytes is None:
                digest.update(view)
                continue

            offset = 0
            while offset < view.nbytes:
                assert part_digest is not None
                take = min(view.nbytes - offset, part_size_bytes - part_bytes)
                segment = view[offset:offset + take]
                digest.update(segment)
                part_digest.update(segment)
                offset += take
                part_bytes += take
                if part_bytes == part_size_bytes:
                    part_hashes.append(part_digest.hexdigest())
                    part_digest = hashlib.sha256()
                    part_bytes = 0

        if part_size_bytes is not None and part_bytes:
            assert part_digest is not None
            part_hashes.append(part_digest.hexdigest())
        result: dict[str, str | int | list[str]] = {
            "size_bytes": size_bytes,
            "sha256": digest.hexdigest(),
        }
        if part_size_bytes is not None:
            result["part_sha256s"] = part_hashes
        return result
    finally:
        try:
            reader.releaseLock()
        except Exception:
            pass
