# Doka Storage

> **Owner:** How is document storage routed, isolated, verified and recovered?
> **Update when:** Storage provider routing, object limits, integrity checks, migration/rollback rules or recovery behavior changes.
> **Last Updated:** 2026-10-08
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
VERIFY/PENDING. No live B2 credential or storage connector was available in this pass. Required evidence remains a real upload/download/integrity/delete/recovery test, including an object above 50 MiB.

### Google Drive
VERIFY/PENDING. No live Google Drive OAuth connector or disposable OAuth account was available in this pass. Required evidence remains connect -> consent -> callback -> Connected, followed by export and retrieval verification.

## Integrity and recovery
Provider transitions are additive and byte-read-only until target size/SHA-256 are verified. Rollback is routing rollback; never delete the original Supabase object merely because a provider transition occurred.

## Readiness
Configured provider credentials do not prove live readiness. Gate 11 remains PENDING until B2, Cloudinary application-path, Google Drive, 50 MiB boundary and recovery evidence are all recorded.
