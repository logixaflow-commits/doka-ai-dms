/// <reference lib="webworker" />
import { hashFileChunks, hashFileMultipartParts } from './hashFileChunks';
type RequestMessage = { type: 'hash'; file: File; chunkSize?: number } | { type: 'hash-multipart'; file: File; partSizeBytes: number; chunkSize?: number } | { type: 'cancel' };
type ResponseMessage = { type: 'progress'; loadedBytes: number; totalBytes: number; percent: number } | { type: 'complete'; sha256: string; sizeBytes: number; parts?: { part_number: number; sha256: string; content_md5: string }[] } | { type: 'error'; message: string };
const scope = self as unknown as DedicatedWorkerGlobalScope;
let controller: AbortController | null = null;
scope.onmessage = async ({ data }: MessageEvent<RequestMessage>) => {
  if (data.type === 'cancel') { controller?.abort(); return; }
  controller?.abort();
  controller = new AbortController();
  const active = controller;
  try {
    const onProgress = (progress: { loadedBytes: number; totalBytes: number; percent: number }) =>
      scope.postMessage({ type: 'progress', ...progress } satisfies ResponseMessage);
    if (data.type === 'hash-multipart') {
      const result = await hashFileMultipartParts(data.file, data.partSizeBytes, {
        chunkSize: data.chunkSize, signal: active.signal, onProgress,
      });
      if (controller !== active || active.signal.aborted) return;
      scope.postMessage({ type: 'complete', sha256: result.sha256, sizeBytes: data.file.size, parts: result.parts } satisfies ResponseMessage);
    } else {
      const digest = await hashFileChunks(data.file, {
        chunkSize: data.chunkSize, signal: active.signal, onProgress,
      });
      if (controller !== active || active.signal.aborted) return;
      scope.postMessage({ type: 'complete', sha256: digest, sizeBytes: data.file.size } satisfies ResponseMessage);
    }
  } catch (error) {
    if (controller !== active) return;
    scope.postMessage({ type: 'error', message: error instanceof Error ? error.message : 'Hash worker failed.' } satisfies ResponseMessage);
  }
};
export {};
