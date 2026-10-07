# Doka Storage Migration and Rollback

## Migration safety rule

The Cloud Edition storage metadata migration is **additive and byte-read-only**.
It does not copy, move, delete, or rewrite any existing document object.
Existing documents and versions are marked `storage_provider = supabase` by default.

The first migration phase therefore changes metadata only; the existing Supabase
object path remains the source of truth.

## Lazy migration

Existing documents are migrated only when a document is explicitly accessed or
selected for a provider transition. A transition is valid only after the target
provider reports the expected object size and SHA-256. The metadata provider field
must be updated only after that verification succeeds.

Until then, reads continue to use the existing Supabase object.

## Rollback

To roll back the new provider routing:

1. Set the routing mode to Supabase-only (`STORAGE_PROVIDER=supabase`).
2. Stop issuing new B2/Cloudinary source sessions.
3. Keep existing provider metadata for reconciliation; do not delete it.
4. Continue reading existing Supabase-backed documents normally.
5. For a document that was already migrated, use the recorded provider reference
   only for reconciliation; rollback must never delete the original Supabase object.
6. Re-enable `hybrid` only after the provider readiness checks pass again.

Rollback is therefore a **routing rollback**, not a destructive storage migration.
No byte copy is required to return to Supabase-only operation.

## Operational rule

Do not run SQL against the managed `storage` schema to mutate object metadata.
Use the Storage API for object operations and keep this migration limited to Doka's
own `public.doka_documents` and `public.doka_document_versions` metadata tables.
