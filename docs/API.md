# Doka API

> **Owner:** What is the authenticated cloud API contract and its security boundary?
> **Update when:** Worker routes, request/response contracts, auth behavior, storage APIs or frontend integration contracts change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Provider credentials, release status, deployment procedures, or database schema details.

## Cloud API
Active cloud API base: `https://doka-ai-dms.logixaflow.workers.dev`.

The Worker exposes authenticated document lifecycle operations, health/config endpoints, version operations, bulk status/Trash operations and owner-scoped audit access.

## Authentication
Authenticated cloud requests use Supabase access tokens. Ownership is derived from the verified identity; clients must not submit a trusted owner ID.

## Document lifecycle
Implemented contract areas include list/search/filter, folders, direct-upload session/completion, download, safe preview, metadata/status/filename/folder updates, Trash/restore, permanent delete, version history/create/restore, atomic bulk status/Trash and audit events.

## Security contract
- Trashed documents are excluded from normal listing/download.
- Signed URLs are short-lived.
- Preview is restricted to passive formats.
- Filename/folder paths are normalized and traversal-safe.
- Version switching is owner-checked and atomic.
- New endpoints require an API contract, auth/RLS tests, frontend states, regression tests and documentation.
