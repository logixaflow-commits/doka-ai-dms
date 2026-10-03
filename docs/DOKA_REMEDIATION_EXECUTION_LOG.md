# Doka Remediation Execution Log

Date: 2026-10-03

## SEC-001 — Secret scanning

- Added Gitleaks directory scanning to the existing consolidated `.github/workflows/doka-quality.yml`.
- Uses a version-pinned container image and read-only checkout mount.
- No additional workflow or runner job was created.
- Scan has not executed because recent GitHub Actions jobs completed with `runner_id=0`, no steps and no retrievable logs. No clean scan baseline is claimed.

## Regression test coverage

- Expanded the backend test command to run both `web-platform/backend` and `web-platform/tests`.
- This includes cross-cutting security, pilot, OCR, and backup helper tests rather than only the backend-local directory.
- Tests remain unverified until a runner can actually execute them.

## BE-009 / BE-010 inspection

- Active Personal Local Safe Workspace service uses per-session threading locks and temporary-file replacement for JSON state writes. Multi-process behavior and crash-recovery semantics still require tests.
- Legacy JSON document-versioning service is not registered in the Personal Local FastAPI entry point.
- Re-inspected lock/status references in active Safe Workspace service; no duplicate-return lock-status branch was found. No speculative code change made.

## CI evidence boundary

- GitHub push-triggered runs for commits `cd0334f` and `78f42da` failed within seconds with all jobs reporting `runner_id=0`, empty step lists and no retrievable logs. This does not establish a code/test failure; hosted runners did not execute the jobs.
- The latest run after expanding test coverage has not produced usable test evidence.
- Dependabot alert inventory remains inaccessible through connected repository permissions; the previously mentioned approximate count is not an itemized verified inventory.

## Prior SEC-014 implementation

- Added structural PostgreSQL URL parsing and shell-free `pg_dump` invocation in `web-platform/backend/app/core/backup_utils.py`.
- Updated legacy Celery database backup task and added parser tests in `web-platform/tests/test_backup_utils.py`.
- This hardens the legacy database backup path; Personal Local workspace archives still use `WorkspaceBackupService`.
- Tests have not been executed.
## Workspace backup destination isolation

- Review found that the workspace backup service resolved and created `BACKUP_ROOT` without rejecting overlap with the source or active workspace, and without rejecting a symlink at the configured backup root.
- Updated `_backup_root()` to reject symlink roots and any ancestor/descendant overlap with `SOURCE_ROOT` or `WORKING_ROOT` before creating the directory.
- Added regression coverage for nested paths, ancestor paths, safe external paths, and symlink roots in `web-platform/tests/test_workspace_backup_safety.py`.
- Tests have not been executed; CI remains skipped while hosted runners are unavailable. No runtime or office-pilot verification is claimed.
## Personal Local / Cloud API boundary

- Review found that the Personal Local FastAPI entry point imported and mounted the optional Supabase-backed `/api/storage` and `/api/documents` routers even though a separate `app.cloud_main` entry point exists for the Cloud API.
- Removed those cloud router registrations and imports from `app.main`; the cloud routes remain available through the dedicated cloud entry point only.
- Added `web-platform/tests/test_personal_local_entrypoint.py` to assert local auth/workspace routes remain and cloud routes are absent.
- This is an entry-point isolation change only; no cloud deployment was enabled. Tests have not been executed while CI is paused.
## Local authentication state file permissions

- The persistent SQLite revocation/refresh-state file is now set to owner read/write only (`0600`) on POSIX systems after opening, before schema access. This reduces the risk of another local OS account editing token revocation state.
- Added a POSIX-only regression test for the resulting file mode. Windows behavior is left to its native ACL model.
- The test has not been executed; runtime verification remains pending.
