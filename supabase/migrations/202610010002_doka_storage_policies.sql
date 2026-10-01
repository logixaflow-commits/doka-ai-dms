-- Doka private storage bucket policies.
-- Create the "doka-documents" bucket manually as a PRIVATE bucket before enabling cloud storage.
-- The object path convention is users/<auth.uid()>/documents/<sha256>/<filename>.

drop policy if exists "doka_documents_storage_select" on storage.objects;
create policy "doka_documents_storage_select"
on storage.objects for select
to authenticated
using (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "doka_documents_storage_insert" on storage.objects;
create policy "doka_documents_storage_insert"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "doka_documents_storage_update" on storage.objects;
create policy "doka_documents_storage_update"
on storage.objects for update
to authenticated
using (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
)
with check (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "doka_documents_storage_delete" on storage.objects;
create policy "doka_documents_storage_delete"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);
