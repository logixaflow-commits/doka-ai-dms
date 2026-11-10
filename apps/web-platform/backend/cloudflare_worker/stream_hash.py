"""Bounded-memory streaming hash helpers shared by the Cloudflare Worker."""
from __future__ import annotations

import hashlib


async def hash_response_stream(reader, max_bytes: int) -> dict[str, str | int]:
    """Hash a JS ReadableStream reader using bulk buffer conversion.

    Pyodide's to_py() converts the JS typed-array view in one interop operation;
    memoryview avoids an additional per-byte Python integer/list allocation.
    """
    digest = hashlib.sha256()
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
            digest.update(view)
        return {"size_bytes": size_bytes, "sha256": digest.hexdigest()}
    finally:
        try:
            reader.releaseLock()
        except Exception:
            pass
