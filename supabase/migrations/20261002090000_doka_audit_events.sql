-- Phase 1 cloud audit trail.
create table if not exists public.doka_audit_events (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid references public.doka_documents(id) on delete set null,
  action text not null check (action in ('upload','download','update','trash','restore')),
  filename text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.doka_audit_events enable row level security;

create index if not exists doka_audit_events_owner_created_idx
  on public.doka_audit_events(owner_id, created_at desc);

create index if not exists doka_audit_events_document_created_idx
  on public.doka_audit_events(document_id, created_at desc);

grant select, insert on public.doka_audit_events to authenticated;

drop policy if exists doka_audit_owner_select on public.doka_audit_events;
create policy doka_audit_owner_select
  on public.doka_audit_events for select to authenticated
  using ((select auth.uid()) = owner_id);

drop policy if exists doka_audit_owner_insert on public.doka_audit_events;
create policy doka_audit_owner_insert
  on public.doka_audit_events for insert to authenticated
  with check ((select auth.uid()) = owner_id);
