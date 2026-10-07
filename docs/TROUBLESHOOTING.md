# Doka Troubleshooting

> **Owner:** How do we diagnose common Doka development, runtime, security, and release problems?
> **Update when:** A recurring failure mode, diagnostic command, provider incident pattern, or recovery procedure changes.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Canonical architecture, release status, secrets, or permanent backlog items.

## First checks

Read `CURRENT_STATE.md`, `ROADMAP.md`, and `TOOL.md` first. Confirm whether the issue is Local, Cloud, provider-specific, or release-evidence related.

Use the status vocabulary consistently: DONE, VERIFIED, PENDING, BLOCKED, DEFERRED, NEXT, VERIFY.

## Personal Local startup problems

1. Confirm Python 3.12 and the backend environment.
2. Confirm the frontend uses the Vite development command.
3. Confirm `BOOTSTRAP_ADMIN_PASSWORD` is explicitly configured; do not rely on a shipped default.
4. Confirm SOURCE_ROOT and WORKING_ROOT are distinct.
5. Confirm `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false`.
6. For OCR failures, verify Tesseract/Poppler configuration and input safety limits before changing application code.

Do not use real source data as a writable test fixture.

## Authentication/session problems

Local and Cloud sessions use separate edition-specific namespaces. A refresh/network failure must not be treated as proof that a valid session is invalid unless the auth boundary actually rejects it.

For Cloud, verify the Supabase token and Worker authentication path. Never trust a client-supplied owner ID.

## Cloud API problems

Current Worker endpoint:
`https://doka-ai-dms.logixaflow.workers.dev`

For ownership failures:
- verify the authenticated identity;
- verify the requested object belongs to that identity;
- check API authorization before RLS/Storage behavior;
- verify signed URLs are short-lived.

For 404/route failures, confirm the current Worker deployment before changing frontend routes.

## Database/migration problems

Keep these facts separate:
- Repository migration head: `20261007120000_doka_trigger_function_least_privilege`.
- Last audited live Supabase head: `20261005113241_doka_audit_export_backup_actions`.

Never mark the repository head as live until it is freshly verified. Prefer a forward corrective migration over a destructive downgrade.

## Storage/provider problems

Provider credentials do not prove provider health. For B2, Cloudinary or Google Drive failures, test upload/download/integrity/cleanup/recovery independently and record evidence before changing the routing policy.

The 50 MiB boundary is a release-critical behavior. Do not silently route an oversized object through an unsupported path.

## Backup/recovery problems

Verify backup checksum first. Restore into an isolated recovery tree. Confirm the active workspace is unchanged and compare restored content against the expected hash before considering recovery successful.

Undo must not overwrite a target whose content no longer matches the executor's recorded hash.

## AI/RAG problems

AI is disabled by default. Distinguish implemented, configured, enabled and live-tested providers. Unsupported providers must fail closed. AI output must pass schema validation and must not bypass human approval or deterministic execution.

## Release-evidence problems

A green CI run proves only the checks that ran. It does not prove browser acceptance, copied-office readiness, OCR quality, provider recovery, two-user isolation, or production health.

When a release gate is blocked, record the exact missing evidence in `CURRENT_STATE.md` and keep the gate BLOCKED/PENDING rather than upgrading it by inference.
