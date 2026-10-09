# Doka Testing

> **Owner:** How is Doka tested from code-level checks through release acceptance?
> **Update when:** Test suites, acceptance criteria, benchmark methodology, CI evidence or release-test requirements change.
> **Last Updated:** 2026-10-09
> **Do NOT put here:** Product roadmap ownership, secrets, or deployment topology.

## Required layers
1. Syntax/static checks.
2. Maintained unit/regression suites.
3. Frontend lint/build/smoke.
4. Integration tests for changed boundaries.
5. Real browser acceptance when release-critical.
6. Copied-office pilot and real OCR benchmark.
7. Provider/recovery/isolation tests for Cloud release.

## Current recorded evidence
Latest recorded maintained Personal Local suite: 386 passed with 11 warnings. Frontend lint/build/smoke and quality/CodeQL workflows were recorded green.

Targeted validation was run in a disposable Python 3.13 runtime on 2026-10-09. The maintained Personal Local backend suite passed **58 tests**; the curated Cloud storage/provider/release-gate/acceptance suite, including the D1 migration tests, passed **90 tests**. Frontend `npm ci`, production TypeScript/Vite build, smoke tests, ESLint and `npm audit --audit-level=high` all passed under Node 24.21.0; npm reported zero vulnerabilities. The browser test was discovered but not executed because authenticated pilot credentials, representative source data and Tesseract are unavailable. Playwright discovery lists one Personal Local browser acceptance test, but the actual browser acceptance was not run because local credentials/data and Tesseract are unavailable. Local `pip-audit` JSON reports for all six backend dependency profiles plus the root `pyproject.toml` contained zero unignored vulnerability findings (the backend scan uses the workflow’s existing `PYSEC-2025-183` ignore). These are local results, not a GitHub Actions result; the connected status view still does not expose the push-triggered Doka Quality Checks run for the latest commit. A broad legacy backend test-directory collection remains non-green: five stale test modules fail collection because the legacy ORM/model stack (`app.models`, `Base` export) is intentionally not loaded by the current Personal Local entrypoint, and one test requires the separately installed Python Playwright package. This is not counted as a pass; CI deliberately runs the maintained Personal Local test list rather than that deferred legacy suite.

## Gate 3 — OCR
The repository contains scripts/ocr_benchmark.py and OCR regression tests. The current benchmark runner requires a copied sample directory plus a JSON manifest with reference text. The accessible test environment does not contain the required sample directory/manifest, and Tesseract is not installed there.

A historical privacy-scrubbed report contains 5 mixed mya+eng samples with mean CER 0.1660492282 and mean WER 0.3081550029, but it does not record the Tesseract version and is therefore not accepted as current Gate 3 release evidence.

Required owner evidence: representative Myanmar and English samples, manifest/reference text, Tesseract version, CER/WER report and privacy-safe evidence.

## Gate 4 — Personal Local browser
The repository now contains a current Playwright suite at web-platform/frontend/e2e/personal-local.spec.ts plus a dedicated config and stable UI selectors. The suite covers the Personal Local release flow and source immutability check. The browser runtime/data acceptance run remains pending.

Required scenario: login -> import -> scan/OCR -> review -> approve -> Final copy -> backup -> isolated restore -> undo, with source SHA-256 unchanged before/after.

## Gate 5 — Copied-office pilot
The repository contains scripts/doka_pilot_check.py with dedicated workspace/backup isolation, source before/after hashes, OCR checks, backup verification, and isolated recovery comparison. Existing evidence is still synthetic only; no representative copied-office pilot was run in this close-out pass.

Required evidence: copied data only, source SHA-256 before/after, import verification, scan/OCR result, organization review/approval, backup SHA-256, isolated Recovery manifest comparison and cleanup.

## Gate 6 — Backup/restore
Synthetic TestClient/backup evidence exists in the historical record, including successful backup verification and isolated Recovery restore with unchanged synthetic source. No real-machine timed drill was run.

Required real evidence: full backup -> destroy/disposable workspace -> restore -> integrity comparison, with backup size, file count, backup duration, restore duration, RTO and RPO recorded.

## Cloud acceptance
The runner at `scripts/cloud_acceptance.py` follows the current Worker direct-upload contract: authenticated `/api/storage/upload-session`, HTTPS signed provider upload, `/api/storage/upload-complete`, then actual signed download and SHA-256 verification. It does not POST file bytes to the legacy `/api/documents` endpoint, which is intentionally HTTP 410. It requires two pre-created authenticated Supabase access tokens and never creates users or accepts service-role credentials. It exercises user-A upload/update/download integrity, trash→restore→trash→permanent-delete lifecycle, user-B list/download isolation, and an exact 50 MiB upload plus download-integrity boundary via `DOKA_CLOUD_50MIB_FILE` for Gate 9 closure (the runner may execute partial checks without it, but Gate 9 remains pending). The runner writes privacy-safe JSON evidence and returns non-zero until all required checks, including the 50 MiB fixture, pass. On runtime/assertion failures it writes a privacy-safe failure record (failure class only) and attempts best-effort trash/permanent-delete cleanup in a `finally` path. The exact-50-MiB acceptance object is cleaned up immediately after successful upload and download verification.

Use authenticated sessions and at least two distinct users for ownership isolation. Test 50 MiB boundary, signed URLs, version restore, Trash/permanent-delete behavior and provider cleanup/recovery.

Gate 9 remains PENDING because a live unauthenticated Worker probe returned HTTP 403 and no disposable authenticated test session was available.

Gate 10 remains PENDING because live Supabase health/migrations are verified but no two real authenticated test users were available. Synthetic RLS probes are not a substitute for two-user evidence.

Gate 11 remains PENDING because Cloudinary provider-level recovery passed, while B2 and Google Drive live evidence is unavailable.


### Train 1 live D1 acceptance

Once D1 credentials are available in the runtime environment, the reusable runner can be executed again; the current live acceptance has already been recorded separately:

`python scripts/d1_job_runtime_acceptance.py --output Phase0_Evidence/train1/d1-job-runtime.json`

Current connector-side live acceptance passed and is recorded at `Phase0_Evidence/train1/d1-job-runtime.json`. Required environment presence is checked by `scripts/acceptance_preflight.py`:
`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `DOKA_D1_DATABASE_ID`.

The runner is disposable and privacy-safe: it verifies duplicate idempotency convergence, terminal success, retry, and exhaustion/dead state, then attempts cleanup. It never records credentials, database IDs, test IDs, or payload contents.


## D1 migration integrity
`python scripts/verify_d1_migrations.py --manifest cloudflare_worker/migrations/manifest.json` verifies that the numbered migration sequence and reviewed Git-blob hashes match. `web-platform/tests/test_d1_migrations.py` applies the numbered SQL files to a disposable SQLite database and verifies the organization-owner, document-owner-membership, permission-recipient and permission-granter guards. This does not apply migrations to production.


The production D1 authorization migration was applied only after a SQL export completed, the export restored in disposable SQLite, the affected metadata tables were confirmed empty, and all four migration guard tests passed. The post-apply read-only query confirmed the unique-owner index and six integrity triggers; see `Phase0_Evidence/train1/d1-authorization-migration-2026-10-09.json`.
