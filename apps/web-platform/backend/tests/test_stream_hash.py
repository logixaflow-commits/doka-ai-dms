import asyncio
import hashlib
import time
from cloudflare_worker.stream_hash import hash_response_stream
class JSChunk:
    def __init__(self, data): self.length, self.data = len(data), data
    def to_py(self): return memoryview(self.data)
class Reader:
    def __init__(self, chunks): self.chunks, self.cancelled = iter(chunks), False
    async def read(self):
        try: return type('R', (), {'done': False, 'value': JSChunk(next(self.chunks))})()
        except StopIteration: return type('R', (), {'done': True, 'value': None})()
    async def cancel(self): self.cancelled = True
    def releaseLock(self): pass
def test_stream_hash_matches_incremental_sha256():
    chunks=[b'a'*1024,b'b'*8192,b'c'*37]; result=asyncio.run(hash_response_stream(Reader(chunks),20000))
    assert result == {'size_bytes':sum(map(len,chunks)),'sha256':hashlib.sha256(b''.join(chunks)).hexdigest()}
def test_stream_hash_cancels_when_over_limit():
    reader=Reader([b'x'*1024])
    try: asyncio.run(hash_response_stream(reader,100))
    except ValueError as exc: assert 'verification limit' in str(exc)
    else: raise AssertionError('expected size cap')
    assert reader.cancelled
def test_bulk_conversion_benchmark_for_one_mib_chunk():
    payload=bytes(range(256))*4096
    start=time.perf_counter(); legacy=bytes(int(payload[i]) for i in range(len(payload))); before=time.perf_counter()-start
    start=time.perf_counter(); bulk=bytes(memoryview(payload)); after=time.perf_counter()-start
    assert legacy==bulk
    print(f'1MiB conversion benchmark legacy={before:.6f}s bulk={after:.6f}s speedup={before/max(after,1e-9):.2f}x')


def test_stream_hash_returns_sha256_for_exact_part_boundaries_across_network_chunks():
    payload = b'a' * 17 + b'b' * 19 + b'c' * 7
    reader = Reader([payload[:9], payload[9:28], payload[28:]])
    result = asyncio.run(hash_response_stream(reader, len(payload), part_size_bytes=20))
    expected_parts = [
        hashlib.sha256(payload[:20]).hexdigest(),
        hashlib.sha256(payload[20:40]).hexdigest(),
        hashlib.sha256(payload[40:]).hexdigest(),
    ]
    assert result == {
        'size_bytes': len(payload),
        'sha256': hashlib.sha256(payload).hexdigest(),
        'part_sha256s': expected_parts,
    }
