-- Remove broad default table ACLs from the cloud audit log.
-- RLS remains owner-scoped; authenticated clients may only read/append their own events.
revoke all privileges on table public.doka_audit_events from public, anon, authenticated;
grant select, insert on table public.doka_audit_events to authenticated;

comment on table public.doka_audit_events is
  'Append-only owner-scoped audit events. Authenticated clients can select and insert only; row ownership is enforced by RLS.';
