-- Version history is append-only for authenticated clients.
-- Permanent document deletion removes versions through the document FK cascade.
revoke delete on table public.doka_document_versions from authenticated;
drop policy if exists doka_versions_owner_delete on public.doka_document_versions;
comment on table public.doka_document_versions is
  'Owner-scoped append-only version history. Authenticated clients may select/insert; only trusted database operations may remove rows.';
