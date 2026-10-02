-- Allow authenticated owners to update only the status and metadata columns.
-- Row-level security still limits updates to the signed-in user's own documents.
grant update (status, metadata) on table public.doka_documents to authenticated;
