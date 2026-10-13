# Doka Storage

> **Owner:** How is document storage routed, isolated, verified and recovered?
> **Update when:** Storage provider routing, object limits, integrity checks, migration/rollback rules or recovery behavior changes.
> **Last Updated:** 2026-10-13
> **Do NOT put here:** General deployment topology, database schema, or release status.

## Personal Local
Local filesystem is the document data plane. Original source is read-only. Working, Final, Quarantine and Backup roots are explicitly separated according to the local safety invariants.

## Personal Cloud routing
- Source <=50 MiB: Supabase private Storage.
- Source >50 MiB: Backblaze B2 when configured.
- Derivatives: Cloudinary preferred when configured and healthy, with documented fallback behavior.
- Google Drive: configuration-gated export/archive/recovery path.

## Live provider evidence
### Cloudinary
Provider-level recovery was live-tested on 2026-10-08 using a disposable 22-byte raw asset.
- SHA-256: 42b68a292fea02d6220c0ee02a4489697758f19d4fb1420d9063697087583a1c
- Upload: succeeded.
- Backup download: returned the exact test payload.
- Delete: succeeded.
- Post-delete lookup: returned a zero-byte placeholder, confirming the original delivery object was removed.
- Tool-side duration: not exposed by the connector.
This proves provider-level recovery behavior, not the complete Doka application adapter/release gate.

### Backblaze B2
Configuration evidence (2026-10-13):
- The Cloudflare Worker `doka-ai-dms` has the `B2_QUOTA_BYTES` secret binding set to 1 GiB (1,073,741,824 bytes) per user.
- Quota warning threshold: 80% projected usage. Upload blocking threshold: 95% projected usage.
- The Worker deployment recorded for this configuration is `d894b59e-4aca-4fa2-86b2-9750055749eb`, active version `75e436b2-2009-4779-b659-5421bea0843a`, with 100% traffic.

VERIFY/PENDING. This confirms quota configuration and deployment metadata only; it does not prove B2 credentials are valid or that live object operations work. Required evidence remains an application-path upload/download/SHA-256 integrity/delete/recovery test, quota rejection and recovery test, and an object above 50 MiB.

### Google Drive
VERIFY/PENDING. The current Worker adapter uses one configured `GOOGLE_DRIVE_REFRESH_TOKEN` and supports an export/resumable-upload path; this is not yet a multi-account connection manager. Multiple Google Accounts, Shared Drives, virtual classification without moving originals, and explicit permission/approval-gated moves remain required work. No live Google Drive OAuth connector or disposable OAuth account was available in this pass. Required evidence remains connect -> consent -> callback -> Connected for each account, enumerate My Drive and Shared Drives with pagination, verify owner/drive identity, export and retrieve with SHA-256 verification, and prove originals are not moved until an authorized approval is recorded.

## Integrity and recovery
Provider transitions are additive and byte-read-only until target size/SHA-256 are verified. Rollback is routing rollback; never delete the original Supabase object merely because a provider transition occurred.

## Readiness
Configured provider credentials do not prove live readiness. Gate 11 remains PENDING until B2, Cloudinary application-path, Google Drive, 50 MiB boundary and recovery evidence are all recorded.
