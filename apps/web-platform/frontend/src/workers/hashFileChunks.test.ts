import { describe, expect, it } from 'vitest';
import { sha256 } from '@noble/hashes/sha256';
import { createHash } from 'node:crypto';
import { hashFileChunks, hashFileMultipartParts } from './hashFileChunks';

function mockFile(size: number) {
  let maxRead = 0;
  return {
    file: {
      size,
      slice(start: number, end: number) {
        const length = end - start;
        maxRead = Math.max(maxRead, length);
        return { async arrayBuffer() {
          const bytes = new Uint8Array(length);
          for (let i = 0; i < length; i++) bytes[i] = (start + i) % 251;
          return bytes.buffer;
        }};
      },
    } as File,
    maxRead: () => maxRead,
  };
}
function expectedDigest(size: number) {
  const hash = sha256.create();
  const blockSize = 1024 * 1024;
  for (let offset = 0; offset < size; offset += blockSize) {
    const length = Math.min(blockSize, size - offset);
    const bytes = new Uint8Array(length);
    for (let i = 0; i < length; i++) bytes[i] = (offset + i) % 251;
    hash.update(bytes);
  }
  return Array.from(hash.digest(), b => b.toString(16).padStart(2, '0')).join('');
}
describe('incremental SHA-256 chunk reader', () => {
  it('hashes empty, small and exact chunk boundaries', async () => {
    for (const size of [0, 37, 65536, 131072, 5 * 65536]) {
      const { file } = mockFile(size);
      expect(await hashFileChunks(file, { chunkSize: 65536 })).toBe(expectedDigest(size));
    }
  });
  it('simulates 100 MiB without reading more than 8 MiB at once', async () => {
    const size = 100 * 1024 * 1024;
    const { file, maxRead } = mockFile(size);
    const progress: number[] = [];
    expect(await hashFileChunks(file, { chunkSize: 8 * 1024 * 1024, onProgress: p => progress.push(p.percent) })).toBe(expectedDigest(size));
    expect(maxRead()).toBeLessThanOrEqual(8 * 1024 * 1024);
    expect(progress.at(-1)).toBe(100);
  });
  it('cancels between chunks', async () => {
    const controller = new AbortController();
    const { file } = mockFile(4 * 65536);
    await expect(hashFileChunks(file, { chunkSize: 65536, signal: controller.signal, onProgress: p => { if (p.loadedBytes >= 65536) controller.abort(); } })).rejects.toMatchObject({ name: 'AbortError' });
  });
});


describe('multipart per-part integrity hashes', () => {
  it('computes whole-file SHA-256 and per-part SHA-256/MD5 with bounded chunk reads', async () => {
    const partSize = 5 * 1024 * 1024;
    const size = partSize + 123;
    const { file, maxRead } = mockFile(size);
    const result = await hashFileMultipartParts(file, partSize, { chunkSize: 1024 * 1024 });
    expect(result.sha256).toBe(expectedDigest(size));
    expect(result.parts).toHaveLength(2);
    expect(result.parts[0].part_number).toBe(1);
    expect(result.parts[0].sha256).toMatch(/^[0-9a-f]{64}$/);
    const firstPartBytes = new Uint8Array(partSize);
    for (let i = 0; i < partSize; i++) firstPartBytes[i] = i % 251;
    expect(result.parts[0].content_md5).toBe(createHash('md5').update(firstPartBytes).digest('hex'));
    expect(result.parts[0].sha256).toBe(createHash('sha256').update(firstPartBytes).digest('hex'));
    expect(result.parts[1].part_number).toBe(2);
    expect(maxRead()).toBeLessThanOrEqual(1024 * 1024);
  });
});
