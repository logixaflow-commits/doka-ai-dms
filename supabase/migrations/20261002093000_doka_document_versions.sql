-- Extend the existing version table; ownership is inherited through its parent document RLS.
alter table public.doka_document_versions
  add column if not exists filename text,
  add column if not exists content_type text;
create index if not exists doka_document_versions_document_created_idx
  on public.doka_document_versions(document_id, created_at desc);
grant select, insert, delete on public.doka_document_versions to authenticated;
drop policy if exists doka_versions_owner_delete on public.doka_document_versions;
create policy doka_versions_owner_delete
  on public.doka_document_versions for delete to authenticated
  using (exists (
    select 1 from public.doka_documents d
    where d.id = doka_document_versions.document_id
      and d.owner_id = (select auth.uid())
  ));
