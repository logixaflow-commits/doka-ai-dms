/// <reference lib="webworker" />
import { hashFileChunks } from './hashFileChunks';
type RequestMessage = { type: 'hash'; file: File; chunkSize?: number } | { type: 'cancel' };
type ResponseMessage = { type: 'progress'; loadedBytes: number; totalBytes: number; percent: number } | { type: 'complete'; sha256: string; sizeBytes: number } | { type: 'error'; message: string };
const scope = self as DedicatedWorkerGlobalScope;
let controller: AbortController | null = null;
scope.onmessage = async ({ data }: MessageEvent<RequestMessage>) => {
  if (data.type === 'cancel') { controller?.abort(); return; }
  controller?.abort();
  controller = new AbortController();
  const active = controller;
  try {
    const digest = await hashFileChunks(data.file, {
      chunkSize: data.chunkSize, signal: active.signal,
      onProgress: progress => scope.postMessage({ type: 'progress', ...progress } satisfies ResponseMessage),
    });
    if (controller !== active || active.signal.aborted) return;
    scope.postMessage({ type: 'complete', sha256: digest, sizeBytes: data.file.size } satisfies ResponseMessage);
  } catch (error) {
    if (controller !== active) return;
    scope.postMessage({ type: 'error', message: error instanceof Error ? error.message : 'Hash worker failed.' } satisfies ResponseMessage);
  }
};
export {};
