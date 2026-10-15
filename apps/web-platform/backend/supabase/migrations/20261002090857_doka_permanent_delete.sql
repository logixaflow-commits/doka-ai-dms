-- Ensure the audit table exists when migrations are replayed in timestamp order.
-- The dedicated audit migration later adds indexes, grants and RLS policies.
create table if not exists public.doka_audit_events (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid references public.doka_documents(id) on delete set null,
  action text not null check (action in ('upload','download','preview','update','trash','restore','permanent_delete')),
  filename text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Allow owners to permanently remove only documents already in Trash.
-- Storage objects are deleted by the authenticated Worker before metadata deletion.
grant delete on table public.doka_documents to authenticated;
drop policy if exists doka_documents_owner_permanent_delete on public.doka_documents;
create policy doka_documents_owner_permanent_delete
  on public.doka_documents for delete to authenticated
  using ((select auth.uid()) = owner_id and deleted_at is not null);

-- Preserve an audit record after the document row is removed.
alter table public.doka_audit_events
  drop constraint if exists doka_audit_events_action_check;
alter table public.doka_audit_events
  add constraint doka_audit_events_action_check
  check (action in ('upload','download','preview','update','trash','restore','permanent_delete'));
