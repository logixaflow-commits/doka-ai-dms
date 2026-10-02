# Phase A — Repository Structure and Code Quality Audit

**Scope:** default branch `main`, Doka Personal Local Edition  
**Audit date:** 2026-10-02

## Current structure

The repository has a clear active application boundary under `web-platform/`, with the React/Vite frontend, FastAPI backend, and Personal Local regression tests grouped together. Repository-wide scripts, documentation, GitHub workflows, optional Supabase migrations, and deferred legacy/mobile/infrastructure areas are kept outside that active runtime.

The root also retains historical launchers and deployment configuration. These are intentionally preserved for now; moving or deleting them without tracing every consumer could break local startup or deployment.

See [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md) for the maintained directory map and hygiene rules.

## Verified quality checks

The latest observed GitHub Actions run for commit `7fcbcd759d1bf08224795366677f099c1f570428` completed successfully on 2026-10-02:

- `Local Core Checks`: success.
- `Doka Quality Checks`: success.
- Backend regression test job: success.
- Frontend dependency installation, production build, and smoke tests: success.

These are CI results, not a substitute for testing on the target office machine with representative files.

## Findings and follow-up

- The frontend workflow's `npm audit` report on that CI run identified 8 npm advisories: 6 high, 1 moderate, and 1 low. The report marked a fix as available for each listed package. These need dependency-by-dependency remediation and regression checks; do not blindly apply major upgrades.
- The frontend quality workflow currently runs build and smoke tests but does not run the configured ESLint command. Lint coverage should be added after its current findings are assessed and resolved.
- The user-reported GitHub Dependabot page shows approximately 24 alerts. The connected repository interface available during this audit does not expose the Dependabot alerts endpoint, so the full alert list, affected manifests, and severity breakdown could not be independently retrieved here. Do not mark those alerts resolved based only on the npm audit subset.
- The repository includes legacy enterprise modules and older launchers alongside the active Personal Local edition. The separation is documented; deletion or broad refactoring is out of scope until references are mapped.
- No source/workspace safety boundaries were changed during this structure audit.

## Phase A status

**Structure review and documentation: completed.**  
**Code quality baseline: partially verified.** CI is green, but ESLint coverage and the dependency-alert remediation remain follow-up items. Phase A should not be marked fully closed until those items are addressed and the full Dependabot alert inventory is reconciled.
