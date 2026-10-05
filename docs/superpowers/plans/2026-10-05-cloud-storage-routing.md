# Doka Cloud Storage Routing Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

Goal: Implement the approved Cloud Edition storage routing architecture with direct browser uploads, B2 multipart support, Cloudinary credit fallback, Google Drive export/backup boundaries, Supabase metadata, security tests, and living README documentation.

Architecture: Supabase remains the metadata/auth/RLS control plane. A provider-neutral storage router selects Supabase Storage, Cloudinary derivatives, or Backblaze B2 and returns short-lived browser upload/download instructions; the Worker never proxies large file bytes. Google Drive is an explicit export/backup target only.

Tech Stack: Cloudflare Python Worker/FastAPI, Supabase REST/Storage, Backblaze B2 S3-compatible API with SigV4, Cloudinary signed upload API, Google Drive REST/OAuth, React/TypeScript/Vite, Supabase SQL/RLS, pytest.

Spec: docs/superpowers/specs/2026-10-05-cloud-storage-architecture-design.md

## Global Constraints
- Original/source objects <= 50 MiB route to Supabase Storage; >50 MiB route to Backblaze B2.
- Preview/thumbnail/cover artifacts under 10 MB route to Cloudinary unless the credit guard triggers fallback.
- B2 multipart is mandatory for objects above 5 GB and must use initiate/upload-part/complete/abort.
- Browser uploads are direct to the selected provider; the Worker must not proxy file bytes.
- SHA-256 and authoritative object size are verified before metadata becomes ready.
- Supabase RLS and the configured single-user allowlist remain enabled.
- Provider secrets never enter frontend bundles or API responses.
- Google Drive is export/backup only.
- Vercel remains paused; no deployment is performed as part of this feature.
- No paid-only dependency is introduced solely for this feature.
- README is updated whenever architecture, configuration, workflow, or release gates materially change.

## Review Focus
- Boundary values at exactly 50 MiB and exactly 10 MB must route according to the documented rules.
- Upload completion with a wrong checksum must never mark a document ready.
- An expired, malformed, or owner-mismatched upload/download request must not leak signed credentials.
- B2 multipart failures must be abortable and retry-safe without buffering the full file in the Worker.
- Cloudinary usage lookup failures must degrade safely to Supabase fallback without exposing account credentials.

### Task 1: Provider-neutral contracts and routing
Files: web-platform/backend/app/services/cloud_storage.py; create web-platform/backend/app/services/storage_router.py; tests in web-platform/tests/test_cloud_storage_routing.py and existing test_cloud_storage.py.
Interfaces: StorageObjectRef(provider, object_key, owner_id); UploadMetadata(filename, content_type, size_bytes, sha256, owner_id, artifact_type); UploadSession(provider, object_ref, expires_at, upload, warnings); StorageProvider methods create_upload_session, complete_upload, get_signed_download, delete, head, initiateMultipartUpload, uploadPart, completeMultipartUpload, abortMultipartUpload; StorageRouter.route(metadata).
- [ ] Write failing tests for <=50 MiB source -> Supabase, >50 MiB source -> B2, <10 MB preview -> Cloudinary, and invalid sizes.
- [ ] Implement provider-neutral contracts, size constants, artifact classification, SHA-256 validation, and owner-scoped object keys.
- [ ] Run focused tests and commit: feat: add provider-neutral cloud storage routing.

### Task 2: Supabase direct signed-upload provider
Files: cloudflare_worker/main.py; create cloudflare_worker/storage_supabase.py; tests/test_cloudflare_storage_direct_upload.py and worker contract tests.
Interfaces: SupabaseStorageProvider.create_upload_session, complete_upload, get_signed_download.
- [ ] Test signed upload creation, no Worker file-body read, completion size/checksum/ownership/idempotency.
- [ ] Implement short-lived Supabase signed upload sessions and owner-scoped paths.
- [ ] Enforce the 50 MiB source boundary and verify authoritative object metadata before ready state.
- [ ] Run focused tests and commit: feat: add direct Supabase storage uploads.

### Task 3: Backblaze B2 direct uploads and multipart
Files: create cloudflare_worker/storage_b2.py; modify cloudflare_worker/main.py; tests/test_cloudflare_b2_storage.py and worker contract tests.
Interfaces: B2StorageProvider.create_upload_session, initiateMultipartUpload, uploadPart, completeMultipartUpload, abortMultipartUpload, get_signed_download.
- [ ] Test direct signed upload, multipart lifecycle, >5 GB behavior, and absence of full-object buffering.
- [ ] Implement B2 S3-compatible SigV4 presigned requests with server-side credentials.
- [ ] Implement multipart initiate/upload-part/complete/abort and preserve part checksums/ETags.
- [ ] Verify object size and SHA-256 before metadata becomes ready.
- [ ] Run focused tests and commit: feat: add direct Backblaze B2 storage and multipart uploads.

### Task 4: Cloudinary derivative provider and credit guard
Files: create cloudflare_worker/storage_cloudinary.py; modify cloudflare_worker/main.py; tests/test_cloudflare_cloudinary_guard.py.
Interfaces: CloudinaryStorageProvider.create_upload_session, get_signed_download; CloudinaryCreditGuard.check.
- [ ] Test healthy credits -> Cloudinary and low/unknown credits -> Supabase fallback with warning cloudinary_credit_fallback.
- [ ] Assert API secret, raw usage payload, and credentials never appear in responses.
- [ ] Implement server-side usage/credit check using DOKA_CLOUDINARY_LOW_CREDIT_THRESHOLD.
- [ ] Implement signed browser upload parameters for preview/thumbnail/cover artifacts under 10 MB.
- [ ] Run focused tests and commit: feat: add Cloudinary derivative routing and credit guard.

### Task 5: Supabase metadata migration
Files: create supabase/migrations/20261005120000_doka_storage_provider_metadata.sql; test web-platform/tests/test_doka_storage_metadata_migration.py.
- [ ] Add provider/object/status/region/preview/export/backup fields while preserving owner/RLS columns.
- [ ] Add constraints for supported providers and non-negative sizes.
- [ ] Run migration contract tests and commit: feat: add cloud storage metadata schema.

### Task 6: Cloud API upload-session/completion/download endpoints
Files: cloudflare_worker/main.py; frontend DocumentUpload.tsx and cloudDocuments.ts; tests for API and frontend upload contracts.
Interfaces: POST /api/storage/upload-sessions; POST /api/storage/uploads/{session_id}/complete; POST /api/storage/multipart; POST /api/storage/multipart/{upload_id}/parts/{part_number}; POST /api/storage/multipart/{upload_id}/complete; POST /api/storage/multipart/{upload_id}/abort; POST /api/storage/download-url.
- [ ] Test authentication, ownership, expiry, provider-neutral signed instructions, completion, download URLs, and multipart.
- [ ] Implement endpoints using require_user and the provider-neutral router.
- [ ] Replace frontend Worker file proxy upload with session -> provider direct upload -> completion.
- [ ] Run focused backend/frontend tests and commit: feat: expose direct cloud storage upload workflow.

### Task 7: Google Drive export/backup adapter
Files: create web-platform/backend/app/services/google_drive_storage.py; tests/test_google_drive_storage.py; create docs/DOKA_GOOGLE_DRIVE_EXPORT.md.
Interfaces: GoogleDriveExporter.export_document, create_backup_manifest, restore_manifest.
- [ ] Test idempotent export/backup, checksum recording, remote references, and secret redaction.
- [ ] Implement server-side OAuth handling and Drive REST operations without exposing refresh tokens.
- [ ] Record remote file ID, checksum, size, timestamp, and status.
- [ ] Keep Drive outside normal source upload routing.
- [ ] Run focused tests and commit: feat: add Google Drive export and backup adapter.

### Task 8: Version, restore, and integrity integration
Files: new migration if required; cloudflare_worker/main.py; tests/test_document_versioning_safety.py and test_cloud_storage_integrity.py.
- [ ] Test provider/object/checksum preservation through version creation and restore.
- [ ] Test checksum mismatch, owner mismatch, provider failure, and idempotent completion.
- [ ] Ensure failed uploads remain non-ready/quarantined.
- [ ] Run the version/integrity suite and commit: feat: make version restore storage-provider aware.

### Task 9: Configuration, quotas, and deployment gates
Files: Worker configuration, backend .env.example, .github/workflows/cloudflare-worker-deploy.yml, docs/DOKA_ENVIRONMENT_MATRIX.md, docs/DOKA_CLOUDFLARE_WORKERS_SETUP.md.
Configuration: B2 endpoint/bucket/key ID/application key; Cloudinary cloud name/API key/API secret; DOKA_CLOUDINARY_LOW_CREDIT_THRESHOLD; Google Drive OAuth configuration; existing Supabase and DOKA_SINGLE_USER_EMAIL.
- [ ] Test missing/partial configuration and non-secret readiness flags.
- [ ] Add quota guards for Supabase 50 MiB and Cloudinary 10 MB.
- [ ] Block production verification when provider readiness is incomplete.
- [ ] Keep Vercel paused and documented.
- [ ] Commit: chore: add cloud storage configuration and release gates.

### Task 10: README and application structure documentation
Files: README.md; create docs/DOKA_APPLICATION_STRUCTURE.md; update DOKA_PHASE_A_TO_E_STATUS.md and DOKA_UNIFIED_REMEDIATION_ROADMAP.md.
- [ ] Add current Cloud Edition routing table, direct-upload rule, security boundary, setup links, and operator-supplied credential notes to README.
- [ ] Document frontend, Cloudflare Worker, Supabase, local backend, mobile, infrastructure, and archived/legacy boundaries.
- [ ] Add a living 'what changed / where to read next' section.
- [ ] Record Vercel paused and deployment gates.
- [ ] Run documentation checks and commit: docs: document Doka cloud storage architecture and structure.

### Task 11: Full regression and security verification
- [ ] Run focused cloud storage tests.
- [ ] Run Supabase migration/security tests.
- [ ] Run backend regression, static analysis, dependency audit, and frontend build/smoke checks.
- [ ] Run Cloudflare Worker contract tests.
- [ ] Verify repository root is clean and contains no secrets or temporary generated files.
- [ ] Re-query final GitHub Actions status and inspect failures/logs before declaring completion.
- [ ] Do not deploy Vercel.
- [ ] Do not deploy Cloudflare Worker unless operator credentials/readiness gates are satisfied.

## Final Acceptance
Complete only when routing, direct browser uploads, B2 multipart >5 GB, Cloudinary credit fallback, Supabase metadata/RLS, Google Drive export/backup, frontend workflow, README/application structure docs, and final CI verification all pass. Production deployment remains gated by operator-supplied credentials and Vercel remains paused.