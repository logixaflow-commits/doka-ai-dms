#!/usr/bin/env python3
"""Self-contained SHA-256 benchmark: byte-by-byte baseline vs memoryview chunks."""
import hashlib
import time

def run(mib):
    data = bytes(range(256)) * (mib * 4096)
    start = time.perf_counter()
    old = hashlib.sha256()
    for value in data:
        old.update(bytes((value,)))
    old_s = time.perf_counter() - start
    start = time.perf_counter()
    new = hashlib.sha256()
    view = memoryview(data)
    for offset in range(0, len(view), 1024 * 1024):
        new.update(view[offset:offset + 1024 * 1024])
    new_s = time.perf_counter() - start
    if old.digest() != new.digest():
        raise SystemExit(f"Digest mismatch for {mib} MiB")
    return old_s, new_s

if __name__ == "__main__":
    print("| Input | Byte-by-byte | memoryview | Speedup |")
    print("|---:|---:|---:|---:|")
    for size in (1, 10, 100):
        before, after = run(size)
        print(f"| {size} MiB | {before:.6f}s | {after:.6f}s | {before / max(after, 1e-12):.2f}x |")
