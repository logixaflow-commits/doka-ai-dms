# Phase A — Repository Structure and Code Quality Audit

**Scope:** default branch `main`, Doka Personal Local Edition  
**Audit date:** 2026-10-02

## Current structure

The repository has a clear active application boundary under `web-platform/`, with the React/Vite frontend, FastAPI backend, and Personal Local regression tests grouped together. Repository-wide scripts, documentation, GitHub workflows, optional Supabase migrations, and deferred legacy/mobile/infrastructure areas are kept outside that active runtime.

The root also retains historical launchers and deployment configuration. These are intentionally preserved for now; moving or deleting them without tracing every consumer could break local startup or deployment.

See [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md) for the maintained directory map and hygiene rules.

## Verified quality checks

The latest observed GitHub Actions runs for commit `4df0e3e2a8671f3b83b3f1631de65a88799e7a75` completed successfully on 2026-10-02:

- `Local Core Checks`: success.
- `Doka Quality Checks`: success.
- `Local Core Checks`: success.
- Backend regression test job: success.
- Frontend dependency installation, dependency audit reporting, ESLint baseline reporting, production build, and smoke tests: success.

These are CI results, not a substitute for testing on the target office machine with representative files.

## Findings and follow-up

- The frontend workflow's `npm audit` report identified 8 npm advisories: 6 high, 1 moderate, and 1 low. The report marked a fix as available for each listed package. These need dependency-by-dependency remediation and regression checks; do not blindly apply major upgrades.
- ESLint is now run in report-only mode so lint findings are visible without blocking the known-good build. The first recorded baseline is 172 errors and 5 warnings across 51 files. The largest rule groups are unused variables/imports (110), React Refresh export rules (25), explicit `any` types (18), state updates inside effects (9), exhaustive-deps (5), and immutability (4). Fix these in focused batches, then switch lint to a blocking check once the baseline reaches zero.
- The user-reported GitHub Dependabot page shows approximately 24 alerts. The connected repository interface available during this audit does not expose the Dependabot alerts endpoint, so the full alert list, affected manifests, and severity breakdown could not be independently retrieved here. Do not mark those alerts resolved based only on the npm audit subset.
- The repository includes legacy enterprise modules and older launchers alongside the active Personal Local edition. The separation is documented; deletion or broad refactoring is out of scope until references are mapped.
- No source/workspace safety boundaries were changed during this structure audit.

## Phase A status

**Structure review and documentation: completed.**  
**Code quality baseline: partially verified.** CI is green and ESLint reporting is integrated, but the lint backlog, npm advisories, and full Dependabot alert inventory remain open. Phase A should not be marked fully closed until those items are addressed and reconciled.
