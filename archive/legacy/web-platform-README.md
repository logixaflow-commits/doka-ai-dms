# Web Platform

The current Personal Local Edition lives under this boundary.

- `frontend/` — React + Vite browser application.
- `backend/` — FastAPI/Python local data-plane application.
- `tests/` — Personal Local regression tests.
- `docs/` — web-platform-specific documentation pointers.

The backend keeps legacy enterprise modules in the same source tree for later reuse, but the default runtime is the Personal Local entry point.

### Backup retention and confirmation

Workspace backup pruning keeps at least the newest five integrity-verified backups by default, even when they are older than `BACKUP_RETENTION_DAYS` (default: 30). Configure the minimum with `BACKUP_MINIMUM_RETAINED` (must be at least 1). Preview a prune with `POST /api/workspace/backups/prune?dry_run=true`; actual pruning requires `confirm=true` and recalculates the plan while holding the backup-operation lock. Restore requests likewise require `confirm=true`; restore continues to verify archive integrity and writes only to a separate Recovery folder.

## Personal Local build contract

For a production-built Personal Local frontend, set `VITE_DOKA_EDITION=personal-local` at frontend build time. This explicit edition flag selects Personal Local authentication even if optional Supabase configuration is present; the Personal Local login flow does not use Supabase. Keep the flag unset for cloud/Vercel builds. The backend must run with `ENVIRONMENT=local` or `development` for local password authentication and filesystem workspace routes. Keep `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false` in all Personal Local deployments. Local token revocation and one-time refresh state are stored in `LOCAL_AUTH_STATE_PATH` (default: `Office_DMS/database/local_auth_state.sqlite3`), outside the working workspace; keep this file on persistent local storage and do not place it inside `SOURCE_ROOT` or `WORKING_ROOT`.
