import { sha256 } from '@noble/hashes/sha256';
export interface ChunkHashProgress { loadedBytes: number; totalBytes: number; percent: number }
export interface ChunkHashOptions { chunkSize?: number; signal?: AbortSignal; onProgress?: (progress: ChunkHashProgress) => void }
export async function hashFileChunks(file: Pick<File, 'size' | 'slice'>, options: ChunkHashOptions = {}): Promise<string> {
  const chunkSize = Math.max(64 * 1024, Math.min(options.chunkSize ?? 8 * 1024 * 1024, 32 * 1024 * 1024));
  const state = sha256.create();
  let offset = 0;
  while (offset < file.size) {
    if (options.signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
    const end = Math.min(offset + chunkSize, file.size);
    const buffer = await file.slice(offset, end).arrayBuffer();
    if (buffer.byteLength !== end - offset) throw new Error('File chunk length mismatch.');
    state.update(new Uint8Array(buffer));
    offset = end;
    options.onProgress?.({ loadedBytes: offset, totalBytes: file.size, percent: file.size ? Math.floor(offset / file.size * 100) : 100 });
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  if (options.signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
  return Array.from(state.digest(), byte => byte.toString(16).padStart(2, '0')).join('');
}
