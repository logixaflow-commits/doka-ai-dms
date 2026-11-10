import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
describe('hash worker source contract', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/workers/hash.worker.ts'), 'utf8');
  it('uses incremental SHA-256 and bounded 8MiB chunks', () => {
    expect(source).toContain('sha256.create()');
    expect(source).toContain('8 * 1024 * 1024');
    expect(source).toContain('file.slice(offset, end).arrayBuffer()');
  });
  it('supports progress, cancellation and explicit errors', () => {
    expect(source).toContain("type: 'progress'");
    expect(source).toContain("type: 'cancel'");
    expect(source).toContain("type: 'error'");
  });
});
