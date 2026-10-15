-- Restrict authenticated document edits to the fields exposed by the API.
revoke update on table public.doka_documents from authenticated;
grant update (status, metadata) on table public.doka_documents to authenticated;
