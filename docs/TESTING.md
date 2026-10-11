# Doka Testing

> **Owner:** How is Doka tested from code-level checks through release acceptance?
> **Update when:** Test suites, acceptance criteria, benchmark methodology, CI evidence or release-test requirements change.
> **Last Updated:** 2026-10-11
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
Latest recorded maintained Personal Local suite: 386 passed with 11 warnings (historical run; not rerun on the current HEAD). Frontend lint/build/smoke and quality/CodeQL workflows were recorded green (historical evidence; not equivalent to current-HEAD CI).

Current worktree verification on 2026-10-11 (Windows/Python 3.14): the maintained Personal Local regression list passed **181 tests, 20 skipped, 1 deselected**. The backend CI regression list passed **70 tests, 7 skipped, 1 deselected**; the deselected symlink-root test requires a Windows directory-symlink privilege unavailable to this account. The OCR benchmark, OCR safety/resource-limit, and vector OCR selection passed **27 tests, 3 skipped**. Compilation and `git diff --check` passed. While enabling the backend suite to finish, two half-open circuit-breaker tests were corrected to provide the durable consent fixture they require; the AI output-validation regression also exposed and fixed a missing `math` import. These are local results, not GitHub Actions results; current-HEAD CI remains unverified.

Targeted validation was run in a disposable Python 3.13 runtime on 2026-10-09. The maintained Personal Local backend suite passed **58 tests**; the curated Cloud storage/provider/release-gate/acceptance suite, including the D1 migration tests, passed **90 tests**. Frontend `npm ci`, production TypeScript/Vite build, smoke tests, ESLint and `npm audit --audit-level=high` all passed under Node 24.21.0; npm reported zero vulnerabilities. Playwright discovery lists one Personal Local browser acceptance test, but the actual browser acceptance was not run because authenticated pilot credentials, representative source data and Tesseract are unavailable. Local `pip-audit` JSON reports for all six backend dependency profiles plus the root `pyproject.toml` contained zero unignored vulnerability findings (the backend scan uses the workflow’s existing `PYSEC-2025-183` ignore). These are local results, not a GitHub Actions result; GitHub Actions run 38072383164 passed nine reported jobs on commit c470c260d38de59766b90b3f1d8c0ecd55d625c3; that run predates later code/documentation commits, so current-HEAD CI remains unverified until a directly associated run succeeds. A broad legacy backend test-directory collection remains non-green: five stale test modules fail collection because the legacy ORM/model stack (`app.models`, `Base` export) is intentionally not loaded by the current Personal Local entrypoint, and one test requires the separately installed Python Playwright package. This is not counted as a pass; CI deliberately runs the maintained Personal Local test list rather than that deferred legacy suite.

## Gate 3 — OCR
The repository contains `scripts/ocr_benchmark.py` and OCR regression tests. A fresh local benchmark was run from copied, visually verified samples and their private reference manifest under `D:\Doka\OcrBenchmarkRun`, using Tesseract `v5.5.3.20260724` with `eng` and `mya` language data. The report is privacy-scrubbed and records 3/3 scored samples with 0 execution errors. Myanmar-only scores CER 0.0880/WER 0.1944 and mixed Myanmar/English scores CER 0.0435/WER 0.1600; both pass the strict per-sample limits. English scores CER 0.0253/WER 0.1071. Aggregate and strict sample gates pass (`gate_ready=true`), with thresholds unchanged.

See [docs/Report/ocr-benchmark.json](Report/ocr-benchmark.json) for machine-readable metrics and [docs/Report/ocr-benchmark-acceptance.md](Report/ocr-benchmark-acceptance.md) for sample provenance, source-render comparison, settings, limitations, and reproduction instructions. This small run does not replace broader representative-sample or release acceptance.

## Gate 4 — Personal Local browser
The repository now contains a current Playwright suite at web-platform/frontend/e2e/personal-local.spec.ts plus a dedicated config and stable UI selectors. The suite covers the Personal Local release flow and source immutability check. A synthetic single-text-file browser smoke passed in headless Chromium on 2026-10-09 (1 test, 1.925 seconds). Privacy-safe evidence is recorded at `Phase0_Evidence/acceptance/personal-local-browser-smoke-2026-10-09.json`. Representative copied-office data and actual Myanmar/English OCR remain required, so Gate 4 remains pending.

Required scenario: login -> import -> scan/OCR -> review -> approve -> Final copy -> backup -> isolated restore -> undo, with source SHA-256 unchanged before/after.

## Repo-side Personal Local preflight
The pilot harness now rejects overlapping source/workspace/backup/evidence paths, symlink roots, source trees containing symlinks, non-empty dedicated workspace/backup roots, and evidence targets that are not regular-file paths. It validates the source before creating mutable pilot roots. The maintained backend workflow explicitly includes `web-platform/tests/test_doka_pilot.py`, so these guardrails are checked in CI when the workflow runs.

Local validation on 2026-10-09: the maintained Personal Local safety subset plus pilot/idempotency tests passed **71 tests**; frontend TypeScript/build/smoke/lint checks passed. The actual Playwright browser acceptance and representative OCR/copied-office pilot remain separate, pending release gates.

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


## Repository self-audit

Run `python scripts/audit/doka_self_audit.py` to check canonical documentation, release-gate references, the current next-action marker, and referenced evidence-path presence. The script's tests run in the `repository-self-audit` GitHub Actions job. Evidence references are advisory by default; missing runtime credentials or real-world acceptance evidence must remain visible as release blockers and are not treated as passing. See [SELF_AUDIT.md](SELF_AUDIT.md).


## 2026-10-11 exact-HEAD and AI/OCR follow-up

- Windows idempotency locking now has an msvcrt fallback with a regression test; a disposable 100-way concurrent-claim smoke test passed. This is not a substitute for the maintained pytest suite on the current commit.
- The OCR benchmark now requires scored samples for required languages and applies per-language mean CER <= 0.30 and mean WER <= 0.60 defaults. The latest six-sample report correctly fails the gate (Myanmar/English CER 79.94%, WER 171.43%). Do not weaken the gate to obtain a pass; visually verify the reference, correct it if needed, and rerun representative scans.
- The unified AI service requires a granted consent record matching subject, purpose and exact resource scope. Persistent grant storage, trusted authenticated caller propagation, revocation/audit, and live free-only provider acceptance remain unverified; external processing must fail closed until integrated.
- Exact-HEAD CI checkpoint: commit `1d404b18d4b927f7fde69fef0fc14116ad6f2849`, GitHub Actions run [#870](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38116845434), completed successfully with all nine reported jobs passing. This closes the CI-evidence gap for that commit only; subsequent code changes require their own successful run. Runtime/local/cloud release gates remain separate.
