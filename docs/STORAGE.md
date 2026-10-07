# Doka Storage

## Personal Local
Local filesystem is the document data plane. Original source is read-only. Working, Final, Quarantine and Backup roots are explicitly separated according to the local safety invariants.

## Personal Cloud routing
- Source <=50 MiB: Supabase private Storage.
- Source >50 MiB: Backblaze B2 when configured.
- Derivatives: Cloudinary preferred when configured and healthy, with documented fallback behavior.
- Google Drive: configuration-gated export/archive/recovery path.

## Integrity and recovery
Provider transitions are additive and byte-read-only until target size/SHA-256 are verified. Rollback is routing rollback; never delete the original Supabase object merely because a provider transition occurred.

## Readiness
Configured provider credentials do not prove live readiness. Each provider requires real upload/download/integrity/cleanup/recovery evidence before Gate 11 can close.
