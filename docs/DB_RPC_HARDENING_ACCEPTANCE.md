# Supabase RPC Forward-Hardening Acceptance Gate

The SQL in `apps/web-platform/backend/supabase/candidates/20261021_doka_rpc_forward_hardening.sql` is a **review candidate only**, not an executable migration. It is intentionally outside `supabase/migrations/` so normal migration discovery does not apply it.

## Why this candidate exists

- Production rollback left the sensitive version RPCs as `SECURITY INVOKER`, while least-privilege column grants intentionally deny direct authenticated writes to storage-pointer fields. This can make version replacement/restore fail at runtime.
- The prior hardening candidate used a broad `[^/]+` object-key tail and granted `EXECUTE` to `service_role` even though the functions require `auth.uid()` and are intended for user-JWT calls.
- Bulk status/trash only changes the already-granted `status`/`deleted_at` columns, so this candidate keeps that function `SECURITY INVOKER`; the three version-pointer functions remain `SECURITY DEFINER` with explicit owner checks and a fixed search path.

## Required before promoting the candidate to a migration

1. Reconcile staging and production migration ledgers without rewriting history or replaying an already-applied migration.
2. In dedicated staging only, create disposable User A/User B accounts and execute authenticated upload/read/version-replace/version-restore/bulk-status/trash flows.
3. Verify User B cannot read, replace, restore, trash, or infer User A's documents or versions.
4. Verify each stored object key matches `users/{auth.uid()}/documents/{lowercase-sha256}/{safe-single-segment}`, the storage object hash matches the metadata, and invalid filename/provider/MIME/size inputs are rejected.
5. Verify the RPCs execute under the intended user JWT, service-role/anonymous execution is denied, and audit rows are written atomically.
6. Record the staging run IDs and evidence on issue #82; only then promote the reviewed candidate into a timestamped migration and request explicit production approval.

**No staging or production database was changed while preparing this candidate.** Do not enable automated database pushes or apply this file directly.
