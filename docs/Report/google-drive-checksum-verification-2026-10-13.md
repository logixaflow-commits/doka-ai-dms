# Google Drive export checksum verification — 2026-10-13

## Finding

The Drive v3 `files` resource does not provide a `sha256Checksum` field for ordinary binary files. Requesting that field and requiring it during export completion made valid exports fail closed. Trusting Doka's pre-upload `appProperties` as proof of the stored bytes would not be a valid substitute.

## Change

- Removed reliance on the unsupported `sha256Checksum` metadata field.
- Completion verification now checks the file's configured destination/ownership and exact size, then downloads the actual Drive media through the Worker and computes SHA-256 over those bytes.
- The Worker binary-fetch helper checks the advertised content length before buffering and checks the actual response size afterward.
- Server-side checksum verification is capped at 50 MiB to avoid unbounded Worker memory use. Larger Drive exports fail closed with a clear internal error until a streaming hash path is implemented. This is a known limitation, not a passing test.
- Added regression tests proving the actual downloaded bytes are hashed, mismatched content is rejected even when `appProperties` match, and oversized exports are rejected before media buffering.

## Verification

- Python compile: `cloudflare_worker/main.py`, `cloudflare_worker/storage_google_drive.py`, and `web-platform/tests/test_cloudflare_google_drive.py` — passed.
- Targeted Drive provider tests — 7 passed.
- Cloudflare provider/contract regression set (`web-platform/tests/test_cloudflare_*.py`) — 168 passed.
- `git diff --check` — passed.
- Live Google OAuth/Drive export has not been run in this environment; it remains blocked on valid provider credentials and a test user/document.

## Follow-up

Implement bounded-memory streaming SHA-256 verification to support Drive exports larger than 50 MiB, then run authenticated live export acceptance before declaring the provider complete.
