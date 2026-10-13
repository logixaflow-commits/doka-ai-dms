# Google Drive export checksum verification — 2026-10-13

## Finding

The Drive v3 `files` resource does not provide a `sha256Checksum` field for ordinary binary files. Requesting that field and requiring it during export completion made valid exports fail closed. Trusting Doka's pre-upload `appProperties` as proof of the stored bytes would not be a valid substitute.

## Change

- Removed reliance on the unsupported `sha256Checksum` metadata field.
- Completion verification now checks the file's configured destination/ownership and exact size, then downloads the actual Drive media through the Worker and computes SHA-256 over those bytes.
- The Worker binary-fetch helper checks the advertised content length before buffering and checks the actual response size afterward.
- Server-side checksum verification now streams the Drive media response in chunks and computes SHA-256 incrementally, with a hard 1 GiB verification cap. The response is not buffered as one large ArrayBuffer. The cap protects Worker CPU/bandwidth while supporting exports above 50 MiB.
- Added regression tests proving the actual downloaded bytes are hashed, mismatched content is rejected even when `appProperties` match, and files above 50 MiB use the streaming-verification path.

## Verification

- Python compile: `cloudflare_worker/main.py`, `cloudflare_worker/storage_google_drive.py`, and `web-platform/tests/test_cloudflare_google_drive.py` — passed.
- Targeted Drive provider + streaming-hash tests — 10 passed.
- Cloudflare provider/contract regression set (`web-platform/tests/test_cloudflare_*.py`) — 171 passed.
- `git diff --check` — passed.
- Full repository Doka Quality Checks passed on commit `d32342469591dcd689711fc1ef74f4774343b885` (run: https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38419720821).
- Worker dry-run succeeded after the stream-hash change.
- Production deploy is still blocked by GitHub Actions' Cloudflare API authentication error 10000; no new Worker version was deployed.
- Live Google OAuth/Drive export has not been run; it still requires a valid test-user token and a deployed Worker.

## Follow-up

Run authenticated live export acceptance before declaring the provider complete; the streaming implementation has a 1 GiB hard limit.
