# Doka Architecture

Last reconciled: 2026-10-07

## 1. Architecture principle

Doka has two intentionally separate active runtimes: Personal Local (safety-first local filesystem/data-plane product) and Personal Cloud (authenticated cloud document library). Enterprise/mobile capabilities remain deferred until their own release gates pass.

## 2. Personal Local

Original source (READ ONLY) -> Verified import/copy -> Working Workspace -> OCR/extraction + inventory/duplicate/version analysis + backup/recovery -> Review Plan -> Human approval -> Copy to Final + audit.

Core invariants: SOURCE_ROOT and WORKING_ROOT are separate; ORIGINAL_READ_ONLY=true; ALLOW_SOURCE_WRITE=false; FINAL_ROOT and QUARANTINE_ROOT remain inside WORKING_ROOT; BACKUP_ROOT is separate from source/workspace; restore never replaces the active workspace; organization never writes to the original source.

## 3. Personal Local application boundary

Frontend: React + TypeScript + Vite and Safe Workspace review UI. Backend: FastAPI/Python with local authentication, workspace/import/inventory/search/OCR/organization/backup services. State: local filesystem for the document workspace and SQLite-compatible local state for local authentication/metadata where configured. External dependencies are optional.

## 4. Personal Cloud

Browser -> Supabase Auth -> React/Vite UI -> Cloudflare Worker -> Supabase Postgres + RLS and private object storage.

Security model: user identity comes from Supabase Auth; Worker ownership checks derive from the verified token; Postgres RLS is an independent ownership boundary; private Storage policies scope objects to the authenticated user; service-role secrets are never exposed to the browser; signed URLs are short-lived; version pointer changes use owner-checked database functions; bulk status/Trash operations use an atomic owner-scoped database function.

## 5. Storage direction

Current transition: Supabase Storage is the active private storage path; Cloudinary is the selected target for the later private object-storage cutover; provider-neutral storage interfaces are already present.

The cutover is gated by real provider configuration, quota/size testing, cleanup behavior, and recovery evidence.

## 6. Deployment boundary

Local runs on the user's machine and does not require public Internet exposure. Private VPN is preferred for remote office access. Cloud uses Vercel as the frontend target (currently owner-paused), Cloudflare as the active cloud API, and Supabase as Auth/Postgres/private Storage transition layer. Vercel is not the Python OCR/filesystem runtime.

## 7. Deferred architecture

Not active in the current release: enterprise organizations/tenant RBAC, distributed worker/Redis architecture, multi-region failover, formal compliance programs, production remote OCR runtime, downloadable thin client, mobile offline/resumable upload, and broad AI/RAG infrastructure.

These are later roadmap items and must not leak into the Personal Local startup path. The detailed Phase 9–12 expansion gates are maintained in `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md` and require independent activation, migration/rollback and acceptance evidence.

## 8. AI agent boundary

When AI is enabled, keep a strict Reader → Planner → Executor separation. Reader and Planner are read/propose-only; Executor accepts only validated human-approved plans. This boundary is described in `docs/AI_PROVIDER_MATRIX.md` and must remain compatible with the Local source-read-only invariant.

## 9. Architecture change rule

Any material architecture change must document problem/scope, affected edition, data flow, security boundary, migration/rollback, cost/resource implications, and verification evidence. For execution order, docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md is canonical.