# Doka Free Cloud-First Architecture Decision

## Goal

Doka is being built for personal use. The target deployment is **cloud-first and free-only**:

- the user's weak local computer is a client, not the main processing server;
- documents and application state should live in cloud services;
- OCR/document processing should run remotely where practical;
- the user can later install/download a desktop-style client when needed;
- Docker must not be required on the user's local machine;
- paid services must not be required for the baseline personal edition.

This document records the current architecture decision after checking the current provider limits in October 2026.

## What is already fixed

### Vercel
Vercel remains the web UI host for the React/Vite frontend.

It is a good fit for the lightweight UI, but the existing Doka backend cannot simply be moved into Vercel Functions because the current backend relies on a persistent workspace model, local SQLite/files, OCR binaries, backup/recovery, and filesystem safety checks.

### Supabase
Supabase remains the authentication and cloud metadata layer.

The current free plan includes 500 MB database, 1 GB file storage, and 5 GB egress, but free projects can be paused after one week of inactivity. Therefore Supabase is suitable for auth/metadata and can initially hold a small document set, but it should not be treated as unlimited document storage.

### Cloudflare R2
R2 is the preferred **optional document-object storage adapter** when the personal document set grows beyond the Supabase Storage allowance.

Current R2 Standard free allowance is 10 GB-month storage, 1 million Class A operations/month, 10 million Class B operations/month, and free egress. R2 is S3-compatible and supports Python boto3, so Doka can use a stable object-storage adapter without coupling the application to one provider.

Important: R2 is usage-billed after the free allowance. The baseline application must therefore include a storage-usage guard/visibility mechanism before real office data is migrated.

## Hosting decision for the Python/OCR backend

No currently checked provider gives us all of the following simultaneously at a comfortable level:

1. free forever;
2. no payment-method dependency;
3. no Docker requirement;
4. enough memory/CPU for Doka's OCR/document processing;
5. persistent local disk suitable for the current backend.

### Render Free

Not selected as the Doka data plane.

Render Free web services sleep after inactivity and their local filesystem is ephemeral. Local SQLite databases, uploaded files, and other filesystem changes can disappear on restart, redeploy, or spin-down. That is incompatible with the current Doka workspace/data model.

### Koyeb Free

Technically interesting for a small Python API: the free instance currently provides 512 MB RAM, 0.1 vCPU and 2 GB SSD, and can deploy from GitHub using buildpacks without requiring a Dockerfile.

However, the free instance cannot use persistent volumes, scales to zero, and Koyeb's account validation requires a payment method. Because Doka is explicitly targeting a free-only personal deployment, Koyeb is not the baseline decision.

### PythonAnywhere Free

It is genuinely free and convenient for Python, but the current free account is too constrained for Doka's intended workload: 512 MB private storage, 100 CPU-seconds/day, no always-on task, and restricted outbound access. It is not a suitable OCR/document-processing backend.

### Google Cloud Run

Cloud Run is technically the strongest fallback for the backend because it supports Python source deployment without Docker being installed locally, and it has an always-free request/CPU/RAM allowance. However, Cloud Run belongs to Google Cloud's billing-account model, and source deployment also uses Cloud Build/Artifact Registry. It therefore remains a **future fallback**, not the strict free-only baseline.

### Hugging Face Spaces

Not selected for the Doka backend. Current free compute/storage behavior and Space visibility/runtime constraints are oriented toward ML demos rather than a private personal document-management backend. Space local disk is ephemeral, and current personal-account rules require paid plans for ordinary Gradio/Docker compute Spaces (with limited exceptions).

## Current architecture target

The safest free-first design is therefore:

    [Doka Web/Desktop Client]
              |
              v
        [Vercel UI]
              |
        Supabase Auth
              |
              +----> [Supabase Postgres]
              |
              +----> [Supabase Storage]
              |
              +----> [Object Storage Adapter]
                         |
                         +----> Cloudflare R2 (when needed)
              |
              v
       [Remote Doka API/Worker]
              |
              +----> OCR / extraction
              +----> organization planner
              +----> backup/recovery orchestration

The critical design rule is that **documents are not stored only on the compute host's local filesystem**.

The API/worker should become stateless with respect to durable documents. Temporary processing files may exist during a request/job, but durable documents, metadata, manifests, and backup objects belong in cloud storage/database services.

## Desktop/client direction

The future downloadable software should be a **thin Doka client**:

- login with Supabase Auth;
- upload/download through authenticated APIs or short-lived signed URLs;
- browse/search cloud metadata;
- submit OCR/organization jobs;
- review and approve organization plans;
- download selected documents when local access is needed.

It should not require Docker and should not require the user's weak machine to host the Doka server.

A local cache may exist for usability, but cache loss must never mean document loss.

## Phase E implementation order

1. Keep the existing Phase A-D local safety implementation intact.
2. Finish the real-machine Phase D pilot using a copied office dataset.
3. Add a provider-neutral object-storage interface to the backend.
4. Add Supabase Storage as the first cloud storage implementation for small personal datasets.
5. Add an R2 implementation behind the same interface, with quota/usage safeguards.
6. Refactor document processing so durable state is cloud-backed and temporary files are disposable.
7. Choose the remote Python/OCR runtime only after measuring the real pilot workload.
8. Build the downloadable thin client after the cloud API is stable.
9. Never make the desktop client depend on a local Docker daemon.

## Important boundary

The current repository is **not** declaring Phase E complete merely because Vercel and Supabase Auth are connected.

Phase E becomes implementation-ready only after the Phase D pilot provides real workload measurements for:

- document counts and sizes;
- OCR time and memory needs;
- PDF/image workload;
- DOCX/XLSX extraction workload;
- backup size;
- expected monthly storage growth;
- expected monthly processing volume.

Those measurements will determine whether the strict free-only runtime can handle the workload or whether a later paid/credit-based runtime is unavoidable.

## Current conclusion

For Doka's personal edition, the architecture should be **cloud-first, storage-first, and provider-neutral**.

The current committed direction is:

- **Vercel** → UI
- **Supabase Auth + Postgres** → identity and metadata
- **Supabase Storage initially** → small personal document set
- **Cloudflare R2 adapter** → larger document/backup storage when needed
- **Remote Python/OCR runtime** → still deliberately undecided until Phase D measurements
- **Local computer** → thin client/cache only
- **Docker on the user's computer** → not required
- **Render Free** → not used as the durable Doka data plane

This avoids locking Doka into a fragile free filesystem while keeping the application ready for a true downloadable client later.


## Code-side cloud storage foundation (implemented)
The backend now contains a provider-neutral object-storage boundary at
`web-platform/backend/app/services/cloud_storage.py`.

Implemented adapters:
- Supabase Storage adapter using the authenticated user's Supabase access token.
- Cloudflare R2 adapter using S3-compatible `boto3`.
- Safe object-key normalization and traversal rejection.
- Per-object size guard and optional total logical quota guard.
- SHA-256 verification on uploads; R2 metadata verification on downloads.
- Temporary signed GET URL support with a maximum seven-day expiry.
- Authenticated Doka API routes for upload, binary download, and signed download URL.
- Cloud storage remains disabled by default until the manual provider/bucket setup is completed.

This is deliberately a storage layer only. Document metadata/database persistence, cloud OCR execution, and the thin downloadable client remain separate implementation steps so the durable data model is not coupled to one provider.
