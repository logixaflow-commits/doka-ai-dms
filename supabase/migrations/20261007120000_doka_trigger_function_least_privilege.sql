-- Trigger functions do not need direct API execution privileges.
-- Keep the updated_at trigger callable by PostgreSQL while removing public/anon/authenticated EXECUTE.
revoke all on function public.doka_set_updated_at() from public, anon, authenticated;
