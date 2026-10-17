function normalizeExternalUrl(rawUrl) {
  if (typeof rawUrl !== 'string' || rawUrl.length === 0 || rawUrl.length > 2048) {
    throw new TypeError('External link must be a valid URL string.');
  }

  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new TypeError('External link URL is invalid.');
  }

  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new TypeError('Only credential-free HTTP(S) external links are allowed.');
  }
  return parsed.href;
}

module.exports = { normalizeExternalUrl };
