/// <reference lib="webworker" />
import { sha256 } from '@noble/hashes/sha256';
type RequestMessage = { type: 'hash'; file: File; chunkSize?: number } | { type: 'cancel' };
type ResponseMessage = { type: 'progress'; loadedBytes: number; totalBytes: number; percent: number } | { type: 'complete'; sha256: string; sizeBytes: number } | { type: 'error'; message: string };
const scope = self as DedicatedWorkerGlobalScope;
let cancelled = false;
scope.onmessage = async ({ data }: MessageEvent<RequestMessage>) => {
  if (data.type === 'cancel') { cancelled = true; return; }
  cancelled = false;
  try {
    const chunkSize = Math.max(65536, Math.min(data.chunkSize ?? 8 * 1024 * 1024, 32 * 1024 * 1024));
    const state = sha256.create(); let offset = 0;
    while (offset < data.file.size) {
      if (cancelled) throw new DOMException('Hashing cancelled', 'AbortError');
      const end = Math.min(offset + chunkSize, data.file.size);
      state.update(new Uint8Array(await data.file.slice(offset, end).arrayBuffer())); offset = end;
      const message: ResponseMessage = { type: 'progress', loadedBytes: offset, totalBytes: data.file.size, percent: Math.floor(offset / data.file.size * 100) };
      scope.postMessage(message); await new Promise(resolve => setTimeout(resolve, 0));
    }
    if (cancelled) throw new DOMException('Hashing cancelled', 'AbortError');
    const digest = Array.from(state.digest(), b => b.toString(16).padStart(2, '0')).join('');
    const message: ResponseMessage = { type: 'complete', sha256: digest, sizeBytes: data.file.size }; scope.postMessage(message);
  } catch (error) { const message: ResponseMessage = { type: 'error', message: error instanceof Error ? error.message : 'Hash worker failed.' }; scope.postMessage(message); }
};
export {};
