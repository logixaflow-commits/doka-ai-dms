# Doka Runtime Evidence

This document records disposable-runtime observations that are useful for release decisions. It is intentionally privacy-safe: no credentials, OCR text, source paths or user identities are recorded.

## 2026-10-08 — disposable runtime checkpoint

### Train 0 preflight
- Runtime: ephemeral Python container.
- Python: 3.13 available.
- Node: 22 available.
- npm: 10 available.
- Playwright: 1.64 available.
- Tesseract: **absent**.
- Myanmar/English Tesseract languages: therefore unavailable.
- Required backend Python modules for the full acceptance harness were not installed in the clean box.
- acceptance_preflight.py in local mode returned not-ready (exit 2).
- Attempted system installation of Tesseract was blocked by the unprivileged runtime; no repository state was changed.

### Train 1/3 workflow contract
- workflow_automation.py was hardened with an explicit bounded idempotency key, per-instance POSIX locking, atomic replacement plus fsync, and replay-safe duplicate handling.
- Targeted workflow runtime suite: **6 passed**.
- Covered: normal completion, wrong assignment/step, next-step failure propagation, invalid idempotency key, key reuse conflict, and concurrent duplicate delivery.
- Full backend suite was not claimed; this is targeted contract evidence only.

## Release interpretation

Train 0 remains **PENDING** for OCR/browser/pilot/recovery/cloud/provider evidence. The runtime result is a real blocker, not a missing harness feature.

Train 1/3 contract hardening may continue in parallel, but distributed late-ack/worker takeover must remain disabled until external side effects use a durable idempotency contract at the job/DB layer.
