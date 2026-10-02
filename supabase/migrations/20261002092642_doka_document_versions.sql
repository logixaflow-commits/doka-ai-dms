-- Cloud document version history. The existing version_no/object_key contract is retained.
create table if not exists public.doka_document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.doka_documents(id) on delete cascade,
  version_no integer not null check (version_no > 0),
  object_key text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 text not null check (sha256 ~ '^[0-9a-fA-F]{64}$'),
  created_at timestamptz not null default now(),
  constraint doka_document_versions_document_id_version_no_key unique (document_id, version_no)
);
alter table public.doka_document_versions
  add column if not exists filename text,
  add column if not exists content_type text;
create index if not exists doka_document_versions_document_created_idx
  on public.doka_document_versions(document_id, created_at desc);
alter table public.doka_document_versions enable row level security;
grant select, insert, delete on public.doka_document_versions to authenticated;

drop policy if exists doka_versions_owner_select on public.doka_document_versions;
create policy doka_versions_owner_select on public.doka_document_versions
  for select to authenticated
  using (exists (
    select 1 from public.doka_documents d
    where d.id = doka_document_versions.document_id
      and d.owner_id = (select auth.uid())
  ));
drop policy if exists doka_versions_owner_insert on public.doka_document_versions;
create policy doka_versions_owner_insert on public.doka_document_versions
  for insert to authenticated
  with check (exists (
    select 1 from public.doka_documents d
    where d.id = doka_document_versions.document_id
      and d.owner_id = (select auth.uid())
  ));
drop policy if exists doka_versions_owner_delete on public.doka_document_versions;
create policy doka_versions_owner_delete on public.doka_document_versions
  for delete to authenticated
  using (exists (
    select 1 from public.doka_documents d
    where d.id = doka_document_versions.document_id
      and d.owner_id = (select auth.uid())
  ));
