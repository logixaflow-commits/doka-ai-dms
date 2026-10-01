-- Doka uploads always use x-upsert=false. Remove the unused object-replacement policy
-- so authenticated users cannot overwrite existing objects in the Doka bucket.
drop policy if exists "doka_documents_storage_update" on storage.objects;
