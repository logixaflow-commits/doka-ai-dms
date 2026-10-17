const test = require('node:test');
const assert = require('node:assert/strict');
const { normalizeExternalUrl } = require('../externalUrl');

test('allows only ordinary HTTP(S) URLs and returns a normalized href', () => {
  assert.equal(normalizeExternalUrl('https://example.com/path'), 'https://example.com/path');
  assert.equal(normalizeExternalUrl('http://example.com:8080/a'), 'http://example.com:8080/a');
});

test('rejects executable and local protocols', () => {
  for (const url of ['javascript:alert(1)', 'file:///etc/passwd', 'data:text/html,hello', 'ftp://example.com']) {
    assert.throws(() => normalizeExternalUrl(url), /HTTP\(S\)/);
  }
});

test('rejects embedded credentials', () => {
  assert.throws(() => normalizeExternalUrl('https://user:pass@example.com'), /credential-free/);
});

test('rejects invalid and oversized values', () => {
  assert.throws(() => normalizeExternalUrl('not a url'), /invalid/i);
  assert.throws(() => normalizeExternalUrl('https://example.com/' + 'x'.repeat(2048)), /valid URL string/);
  assert.throws(() => normalizeExternalUrl(null), /valid URL string/);
});
