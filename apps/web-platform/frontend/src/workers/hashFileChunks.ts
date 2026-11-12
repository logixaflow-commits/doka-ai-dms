import { sha256 } from '@noble/hashes/sha256';
import { md5 } from '@noble/hashes/legacy';
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


export interface MultipartPartHash {
  part_number: number;
  sha256: string;
  content_md5: string;
}

export interface MultipartFileHash {
  sha256: string;
  parts: MultipartPartHash[];
}

export async function hashFileMultipartParts(
  file: Pick<File, 'size' | 'slice'>,
  partSizeBytes: number,
  options: ChunkHashOptions = {},
): Promise<MultipartFileHash> {
  if (!Number.isSafeInteger(partSizeBytes) || partSizeBytes < 5 * 1024 * 1024) {
    throw new Error('B2 multipart part size must be at least 5 MiB.');
  }
  const chunkSize = Math.max(64 * 1024, Math.min(options.chunkSize ?? 8 * 1024 * 1024, 32 * 1024 * 1024));
  const whole = sha256.create();
  const parts: MultipartPartHash[] = [];
  let partSha = sha256.create();
  let partMd5 = md5.create();
  let partBytes = 0;
  let offset = 0;

  while (offset < file.size) {
    if (options.signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
    const end = Math.min(offset + chunkSize, file.size);
    const buffer = await file.slice(offset, end).arrayBuffer();
    if (buffer.byteLength !== end - offset) throw new Error('File chunk length mismatch.');
    const bytes = new Uint8Array(buffer);
    whole.update(bytes);

    let localOffset = 0;
    while (localOffset < bytes.byteLength) {
      const take = Math.min(bytes.byteLength - localOffset, partSizeBytes - partBytes);
      const segment = bytes.subarray(localOffset, localOffset + take);
      partSha.update(segment);
      partMd5.update(segment);
      localOffset += take;
      partBytes += take;

      const isLastByte = offset + localOffset === file.size && localOffset === bytes.byteLength;
      if (partBytes === partSizeBytes || isLastByte) {
        const sha = partSha.digest();
        const md5Digest = partMd5.digest();
        parts.push({
          part_number: parts.length + 1,
          sha256: Array.from(sha, byte => byte.toString(16).padStart(2, '0')).join(''),
          content_md5: Array.from(md5Digest, byte => byte.toString(16).padStart(2, '0')).join(''),
        });
        partSha = sha256.create();
        partMd5 = md5.create();
        partBytes = 0;
      }
    }

    offset = end;
    options.onProgress?.({ loadedBytes: offset, totalBytes: file.size, percent: file.size ? Math.floor(offset / file.size * 100) : 100 });
    await new Promise(resolve => setTimeout(resolve, 0));
  }

  if (options.signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
  return {
    sha256: Array.from(whole.digest(), byte => byte.toString(16).padStart(2, '0')).join(''),
    parts,
  };
}
