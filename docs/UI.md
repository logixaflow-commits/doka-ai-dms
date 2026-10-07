# Doka UI Map and Workflow Contract

Last reconciled: 2026-10-07

This document is the UI source-of-truth for the active Doka editions. A UI component, route, mockup, or SPA shell response is not a working feature until its runtime API, authorization boundary, states, tests, and deployment evidence exist.

## 1. Active editions

### Personal Local
- React + Vite frontend with FastAPI local backend.
- Safe import/copy, verification, scan, OCR/extraction, review, approval, organization, search, backup and recovery.
- Must not depend on Supabase, Cloudflare, Vercel, Redis, MinIO, or AI credentials.
- Local authentication is separate from Supabase cloud authentication.

### Personal Cloud
- React + Vite frontend with Supabase Auth and the active Cloudflare Worker API.
- Authenticated private cloud document library.
- Cloud navigation must not expose Personal Local filesystem operations.

### Enterprise / Mobile
- Preserved or deferred. Do not expose incomplete routes as active production features.

## 2. Active route map

| Route | Edition | Role | Status |
|---|---|---|---|
| /login | Cloud | Supabase sign-in/session entry | Active |
| /admin/dashboard | Cloud | Cloud health, counts and recent documents | Active |
| /admin/cloud-documents | Cloud | Upload, search/filter, rename, folder path, status, preview, download, Trash/Restore, permanent delete, versions and bulk actions | Implemented; real-user E2E pending |
| /admin/activity | Cloud | Owner-scoped activity history | Active; real-user E2E pending |
| /admin/workspace | Local | Safe Workspace local workflow | Local-only; real-browser acceptance pending |

The production router must keep local workspace routes out of the cloud navigation.

## 3. Personal Local workflow

Import -> SHA-256 verify -> Scan -> Read/OCR -> Review Plan -> Human Approval -> Copy to Final -> Backup -> Recovery/Undo.

- Source is read-only.
- Organization is copy-only.
- No overwrite of different content.
- Duplicate/version recommendations require review.
- OCR corrections are sidecar/review data and do not mutate the source document.
- Undo removes only unchanged copies created by the current organization session.

## 4. Cloud document workflow

Sign in -> list/search/filter -> upload -> preview/download -> metadata/status/folder update -> Trash/Restore -> version history/create/restore -> audit.

Security boundary: Supabase Auth identifies the user; the Worker resolves ownership from the verified token; Supabase RLS/Storage policies remain the final ownership boundary; browser code must never contain service-role credentials; signed URLs are short-lived; trashed documents are excluded from normal listing/download.

## 5. Required UI states

Every active document action must provide loading/in-progress, empty where applicable, success confirmation, actionable error, disabled unsafe/conflicting state, and retry where safely retryable.

For destructive or irreversible actions: explicit confirmation, clear scope, audit event where applicable, and no accidental retry that can duplicate an operation.

## 6. Responsive/accessibility contract

Check 320px, 375px, 390px, 768px, 1024px and 1440px widths. Acceptance includes no horizontal overflow, correct sidebar/drawer behavior, keyboard navigation and visible focus, accessible labels, and reduced-motion-safe behavior.

The current release blocker is authenticated browser acceptance of protected pages, not the existence of React components.

## 7. Frontend state boundaries

A new import/session must clear stale search results, OCR/understanding results, organization plans, selected approvals and session-specific status. Cloud user state must never leak between authenticated sessions. Local session tokens must not be accepted as cloud identities.

## 8. UI completion rule

A feature is complete only when the route is mounted in the intended edition; navigation exposes it only where intended; the API contract exists; server-side authentication/authorization exists; loading/empty/error/success/disabled states exist; responsive/accessibility checks pass; focused regression tests pass; real browser E2E passes when release-critical; and documentation is updated.

See docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md for release sequencing.