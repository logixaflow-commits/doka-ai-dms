-- Permit owner-scoped audit records for safe inline previews.
alter table public.doka_audit_events
  drop constraint if exists doka_audit_events_action_check;
alter table public.doka_audit_events
  add constraint doka_audit_events_action_check
  check (action in ('upload','download','preview','update','trash','restore','permanent_delete'));
