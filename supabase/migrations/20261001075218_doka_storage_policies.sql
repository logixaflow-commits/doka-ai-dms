-- Doka private storage bucket and owner-scoped policies.
-- Object path convention: users/<auth.uid()>/documents/<sha256>/<filename>.

insert into storage.buckets (id, name, public, file_size_limit)
values ('doka-documents', 'doka-documents', false, 52428800)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit;

drop policy if exists "doka_documents_storage_select" on storage.objects;
create policy "doka_documents_storage_select"
on storage.objects for select
to authenticated
using (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = 'users'
  and (storage.foldername(name))[2] = (select auth.uid()::text)
);

drop policy if exists "doka_documents_storage_insert" on storage.objects;
create policy "doka_documents_storage_insert"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = 'users'
  and (storage.foldername(name))[2] = (select auth.uid()::text)
);

drop policy if exists "doka_documents_storage_update" on storage.objects;
create policy "doka_documents_storage_update"
on storage.objects for update
to authenticated
using (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = 'users'
  and (storage.foldername(name))[2] = (select auth.uid()::text)
)
with check (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = 'users'
  and (storage.foldername(name))[2] = (select auth.uid()::text)
);

drop policy if exists "doka_documents_storage_delete" on storage.objects;
create policy "doka_documents_storage_delete"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'doka-documents'
  and (storage.foldername(name))[1] = 'users'
  and (storage.foldername(name))[2] = (select auth.uid()::text)
);
