-- Cloud document version history. Old object keys remain private and owner-scoped.
create table if not exists public.doka_document_versions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid not null references public.doka_documents(id) on delete cascade,
  object_key text not null,
  filename text not null,
  content_type text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);
create index if not exists doka_document_versions_owner_document_created_idx
  on public.doka_document_versions(owner_id, document_id, created_at desc);
alter table public.doka_document_versions enable row level security;
grant select, insert, delete on public.doka_document_versions to authenticated;
drop policy if exists doka_document_versions_owner_select on public.doka_document_versions;
create policy doka_document_versions_owner_select
  on public.doka_document_versions for select to authenticated
  using ((select auth.uid()) = owner_id);
drop policy if exists doka_document_versions_owner_insert on public.doka_document_versions;
create policy doka_document_versions_owner_insert
  on public.doka_document_versions for insert to authenticated
  with check ((select auth.uid()) = owner_id);
drop policy if exists doka_document_versions_owner_delete on public.doka_document_versions;
create policy doka_document_versions_owner_delete
  on public.doka_document_versions for delete to authenticated
  using ((select auth.uid()) = owner_id);
