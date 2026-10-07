# Doka Cloud API Contract

Version: 1.5  
Runtime: Cloudflare Python Worker + Supabase Auth/Postgres/Storage  
Base URL: `https://doka.logixaflow.workers.dev`

This document is the source-of-truth contract for the Personal Cloud API. Every endpoint requires a valid Supabase access token unless marked public. Supabase RLS and private Storage policies remain the final ownership boundary; the Worker also filters by the verified user ID. Never use the service-role key in this API.

## Common behavior

- JSON responses use UTF-8.
- Authenticated endpoints accept `Authorization: Bearer <Supabase access token>`.
- Invalid/expired token: HTTP 401.
- Missing runtime configuration: HTTP 503.
- Document identifiers are UUIDs.
- The maximum object size is 50 MiB.
- SHA-256 is calculated by the Worker from uploaded bytes.
- Storage objects are private and scoped below `users/{auth.uid()}/documents/`.
- List operations return only active (non-trashed) documents unless `trash=true`.
- Soft-deleted documents cannot be downloaded or modified until restored.
- Error response shape: `{"detail":"Human-readable message"}`.

## Endpoints

### `GET /health` — public

Returns Worker health and edition metadata.

### `GET /api/config` — public

Returns runtime readiness booleans only. It must never return keys or tokens.

### `GET /api/documents` — authenticated

Query parameters:

| Name | Type | Default | Validation |
|---|---|---|---|
| `limit` | integer | 100 | 1–500 |
| `offset` | integer | 0 | >= 0 |
| `search` | string | omitted | max 200 chars; filename contains match |
| `status` | enum | omitted | active, review, quarantined, archived |
| `trash` | boolean | false | false = active library; true = trash |
| `folder_path` | string | omitted | normalized absolute path, max 512 chars |

Response: `{"documents": CloudDocument[]}`.

### `POST /api/documents` — authenticated

Multipart form field: `file`.

The Worker rejects files larger than 50 MiB, computes SHA-256, uploads to private Storage without overwrite, then creates owner-scoped metadata. If metadata creation fails, it attempts to clean up the newly uploaded object.

Response: `{"document": CloudDocument}`.

### `GET /api/folders` — authenticated

Returns the distinct logical folder paths used by the signed-in owner's active documents. The result is owner-scoped and capped at 500 rows for bounded response size.

Response: `{"folders": string[]}`.

### `POST /api/documents/bulk` — authenticated

JSON body: `{"document_ids": string[], "action": "status" | "trash", "status"?: "active" | "review" | "quarantined" | "archived"}`.

Accepts 1–100 unique document IDs. All IDs must belong to the authenticated owner and be active; otherwise the transaction fails without partial updates. Status changes and Trash operations run in one database transaction and write corresponding audit events.

Response: `{"documents": CloudDocument[], "updated_count": number}`.

### `GET /api/documents/{id}/download` — authenticated

Returns a short-lived signed URL (300 seconds) and SHA-256. The Worker verifies ownership and rejects trashed documents before creating the signed URL.

Response: `{"url": string, "sha256": string, "expires_seconds": 300}`.

### `GET /api/documents/{id}/preview` — authenticated

Returns a short-lived signed URL (300 seconds) for passive inline formats only: PDF, JPEG, PNG, GIF, WebP, plain text and CSV. HTML, SVG, Office files and unknown formats are rejected with HTTP 415. Ownership and non-trashed state are verified before signing. Preview requests create a `preview` audit event.

Response: `{"url": string, "sha256": string, "expires_seconds": 300}`.

### `GET /api/documents/{id}/versions` — authenticated

Returns up to 100 previous versions, newest version number first. The Worker verifies ownership and active state; version rows are additionally protected by RLS through their parent document.

Response: `{"versions": CloudDocumentVersion[]}`.

### `POST /api/documents/{id}/versions` — authenticated

Multipart form field: `file`. Uploads a replacement object (maximum 50 MiB), then calls an owner-checked database function that atomically snapshots the current object metadata and switches the document pointer. Identical content is rejected with HTTP 409. Failed database updates trigger best-effort cleanup of the newly uploaded object.

Response: `{"document": CloudDocument}`.

### `POST /api/documents/{id}/versions/{version_id}/restore` — authenticated

Restores a previous version while first snapshotting the current active object as a new history entry. The owner-checked database function performs both operations atomically.

Response: `{"document": CloudDocument}`.

### `PATCH /api/documents/{id}` — authenticated

Supported fields:

- `status`: active, review, quarantined, archived
- `metadata`: JSON object
- `filename`: plain filename, 1–255 chars; path separators and NUL rejected
- `folder_path`: normalized path such as `/` or `/Finance/Invoices`; traversal segments rejected

At least one field is required. The Worker scopes the update to the authenticated owner and non-trashed document. Database column privileges restrict writes to the approved fields.

Response: `{"document": CloudDocument}`.

### `DELETE /api/documents/{id}` — authenticated

Moves a document into Trash by setting `deleted_at`. The object is retained in private Storage so the user can restore it. This is not permanent deletion.

Response: `{"document": CloudDocument}`.

### `POST /api/documents/{id}/restore` — authenticated

Restores a trashed document by clearing `deleted_at`. Only the owning user can restore it.

Response: `{"document": CloudDocument}`.

### `DELETE /api/documents/{id}/permanent` — authenticated

Permanently deletes a document only when it is already in Trash. The Worker verifies ownership, enumerates version object keys, deletes the current object and stored version objects, then deletes metadata. If Storage cleanup fails, metadata is retained and the request fails. The owner-only database DELETE policy independently requires `deleted_at IS NOT NULL`.

Response: `{"deleted": true, "document_id": string, "objects_deleted": number}`.

### `GET /api/audit` — authenticated

Returns the signed-in owner's document activity, newest first.

Query:
- `limit`: integer, 1–500, default 100.

Each event contains `id`, `document_id`, `action`, `filename`, `metadata`, and `created_at`.

The audit table is owner-scoped with RLS. The Worker records upload, download, preview, update, trash, restore, permanent_delete, version_create, and version_restore events as best-effort side effects; an audit-write failure never breaks the primary document operation. Permanent-delete events retain the original document ID in event metadata because the document row is removed.

## Canonical document schema

See `shared/contracts/cloud-document.schema.json`.

## Implemented vs planned contract surface

Implemented in the current Worker: health, config, list/search/filter/pagination, folder listing, upload, download, safe preview, status/metadata/rename/folder-path update, trash, restore, version history/create/restore and atomic bulk status/Trash.

Implemented in the Cloud Documents UI: bulk status changes and bulk move-to-Trash through a single owner-scoped atomic database transaction. Planned: richer folder-tree CRUD, batch upload queue/retry, OCR jobs, organization/team access and AI jobs. Permanent deletion is implemented for trashed documents with Storage object cleanup and a restrictive owner-only DELETE policy. Audit event recording/listing is now implemented.

## Security invariants

- Every authenticated request resolves the user from Supabase Auth; never trust an owner ID from the browser.
- RLS and Storage path policies must continue to enforce owner boundaries.
- Do not expose service-role credentials to the browser or Worker runtime unless a future reviewed server-side use case requires them; the current design uses the user's access token.
- A trashed document is excluded from normal listing and download.
- Folder paths are labels/organization metadata, not filesystem paths.
- Filename/folder updates cannot change owner ID, storage object key, SHA-256 or object bytes.
- The only operations that switch a document's active object pointer are the two owner-checked version RPCs. They validate `auth.uid()`, active document ownership, SHA-256-bound per-user object keys with one safe filename segment, and filename/MIME metadata; execute is revoked from `public` and `anon` and granted only to `authenticated`.
- Bulk status/Trash uses a `SECURITY INVOKER` RPC, validates every unique owner-owned active document before updating, and writes audit events in the same transaction.
- New endpoint = contract + RLS/authorization test + frontend state + regression test + docs.
