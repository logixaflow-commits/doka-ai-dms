import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('hash worker source contract', () => {
  const worker = readFileSync(resolve(process.cwd(), 'src/workers/hash.worker.ts'), 'utf8');
  const helper = readFileSync(resolve(process.cwd(), 'src/workers/hashFileChunks.ts'), 'utf8');

  it('uses incremental SHA-256 and bounded 8MiB chunks in the hashing helper', () => {
    expect(helper).toContain('sha256.create()');
    expect(helper).toContain('8 * 1024 * 1024');
    expect(helper).toContain('file.slice(offset, end).arrayBuffer()');
    expect(worker).toContain("import { hashFileChunks, hashFileMultipartParts } from './hashFileChunks'");
    expect(worker).toContain("type: 'hash-multipart'");
  });

  it('supports progress, cancellation and explicit errors in the worker protocol', () => {
    expect(worker).toContain("type: 'progress'");
    expect(worker).toContain("type: 'cancel'");
    expect(worker).toContain("type: 'error'");
    expect(worker).toContain("type: 'complete'");
  });
});
