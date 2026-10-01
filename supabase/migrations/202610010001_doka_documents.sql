create table if not exists public.doka_documents (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  object_key text not null,
  filename text not null,
  content_type text not null default 'application/octet-stream',
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 text not null check (sha256 ~ '^[0-9a-fA-F]{64}$'),
  status text not null default 'active' check (status in ('active','review','quarantined','archived')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(owner_id, object_key)
);

create index if not exists doka_documents_owner_created_idx
  on public.doka_documents(owner_id, created_at desc);

create table if not exists public.doka_document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.doka_documents(id) on delete cascade,
  version_no integer not null check (version_no > 0),
  object_key text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 text not null check (sha256 ~ '^[0-9a-fA-F]{64}$'),
  created_at timestamptz not null default now(),
  unique(document_id, version_no)
);

create index if not exists doka_document_versions_document_idx
  on public.doka_document_versions(document_id, version_no desc);

alter table public.doka_documents enable row level security;
alter table public.doka_document_versions enable row level security;

drop policy if exists "doka_documents_owner_select" on public.doka_documents;
create policy "doka_documents_owner_select"
  on public.doka_documents for select
  using (owner_id = auth.uid());

drop policy if exists "doka_documents_owner_insert" on public.doka_documents;
create policy "doka_documents_owner_insert"
  on public.doka_documents for insert
  with check (owner_id = auth.uid());

drop policy if exists "doka_documents_owner_update" on public.doka_documents;
create policy "doka_documents_owner_update"
  on public.doka_documents for update
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

drop policy if exists "doka_documents_owner_delete" on public.doka_documents;
create policy "doka_documents_owner_delete"
  on public.doka_documents for delete
  using (owner_id = auth.uid());

drop policy if exists "doka_versions_owner_select" on public.doka_document_versions;
create policy "doka_versions_owner_select"
  on public.doka_document_versions for select
  using (
    exists (
      select 1 from public.doka_documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  );

drop policy if exists "doka_versions_owner_insert" on public.doka_document_versions;
create policy "doka_versions_owner_insert"
  on public.doka_document_versions for insert
  with check (
    exists (
      select 1 from public.doka_documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  );

create or replace function public.doka_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists doka_documents_set_updated_at on public.doka_documents;
create trigger doka_documents_set_updated_at
before update on public.doka_documents
for each row execute function public.doka_set_updated_at();
