# Doka Personal Local Runbook

## Purpose

Doka is a single-user local/office document management system. The original source drive is treated as read-only.

## Safe data flow

```
Original source
    -> verified import/copy
Working Copy
    -> inventory + SHA-256
    -> local text extraction / OCR
    -> duplicate + version analysis
    -> review plan
    -> user approval
Final organized library
    -> backup + audit history
```

The organization workflow copies approved files into Final. It does not rename, move, delete, or overwrite files in the original source.

## Workspace boundaries

Configured paths are:

- `SOURCE_ROOT`: original source folder, read-only.
- `WORKING_ROOT`: writable processing area.
- `FINAL_ROOT`: organized output under the working area.
- `QUARANTINE_ROOT`: reserved for uncertain/suspicious files.
- `BACKUP_ROOT`: workspace backups.

Writable paths must remain inside the working area. Source-write mode is rejected in personal mode.

## Normal workflow

1. Open the Safe Workspace page.
2. Start an import using the source folder or configured `SOURCE_ROOT`.
3. Wait until files are copied and hash-verified.
4. Scan the working copy.
5. Run Read / OCR.
6. Build the organization review plan.
7. Review manual-review items first.
8. Select only proposals you approve.
9. Use **Approve & Copy Selected**.
10. Create a workspace backup after meaningful changes.

## Duplicate and version handling

- Exact SHA-256 duplicates are marked for review.
- Filename families such as copy/final/v2/version are treated as possible versions.
- Uncertain items remain in review instead of being automatically reorganized.

## Recovery

Backups contain the writable workspace snapshot plus a SHA-256 manifest.

Restore is recovery-only: it extracts into a new `Workspace/Recovery/...` directory and does not replace the active workspace.

Undo removes only files copied by the current organization session when their current hash still matches the audit record. Changed files are preserved.

## Search and preview

Search operates on the working copy. Results can expose a preview or download the verified working-copy file. File paths are validated against the session working-copy root.

## OCR

The OCR validation endpoint checks:

- Tesseract executable
- English language data
- configured Myanmar language data

The DMS remains usable without OCR; OCR-dependent understanding simply has less extracted text.

## AI

AI is disabled by default. Local/rule-based processing must remain functional without provider credentials.

When enabled later, provider order is configurable and uses fallback behavior. AI recommendations are advisory and require user approval before organization.

## Office access

Keep the data plane at home/local. For office access, use a private VPN such as Tailscale rather than public port forwarding.

Do not expose the original drive or document APIs directly to the public Internet.

## External services

Vercel is a frontend deployment target. Render and Supabase are reserved for a later cloud/multi-user edition. Sentry is optional and must receive sanitized telemetry only.

The personal edition must continue working when these external services and AI providers are unavailable.

## Troubleshooting

### Import does not start

Check that the source directory exists and is readable. The source must not overlap the writable workspace.

### Some files are failed/unreadable

Do not delete them automatically. Inspect the status and keep them in review/quarantine until the cause is understood.

### OCR is unavailable

Run **Check OCR**. Install/configure Tesseract and the required language data on the local machine before relying on OCR classification.

### A proposal shows conflict

The system will not overwrite a different existing target. Review the conflict manually.

### Office browser cannot connect

Verify the private VPN connection and that the local backend/frontend are running. Do not open public router ports as a workaround.

## Pre-pilot checklist

- [ ] Original source path is correct.
- [ ] Original source is not inside the writable workspace.
- [ ] `ALLOW_SOURCE_WRITE=false`.
- [ ] A backup destination exists.
- [ ] Safe Workspace import completes with verified hashes.
- [ ] OCR check has been reviewed.
- [ ] Manual-review proposals are understood.
- [ ] First organization batch is small.
- [ ] Backup exists before a larger batch.

## Current boundary

This runbook describes the Doka Personal Local Edition. Enterprise multi-user, cloud storage, billing, tenant isolation, and advanced integrations are intentionally deferred until the personal workflow is stable with real office data.

## Local browser login

The Personal Local Edition uses a small local JWT auth boundary and does not require the deferred enterprise ORM/user-model stack.

Set these in the local `.env` before starting the backend:
- `LOCAL_ADMIN_USERNAME=admin` (or another local username)
- `BOOTSTRAP_ADMIN_PASSWORD=<strong password>` (12+ characters)

The React login screen uses `/api/auth/login`. Workspace APIs require the resulting bearer token. The password is never embedded in the frontend or repository.

