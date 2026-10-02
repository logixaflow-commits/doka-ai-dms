-- Add cloud library organization and recoverable trash lifecycle.
alter table public.doka_documents
  add column if not exists deleted_at timestamptz,
  add column if not exists folder_path text not null default '/';

alter table public.doka_documents
  add constraint doka_documents_folder_path_check
  check (folder_path = '/' or (left(folder_path, 1) = '/' and right(folder_path, 1) <> '/' and position('..' in folder_path) = 0));

create index if not exists doka_documents_owner_deleted_created_idx
  on public.doka_documents(owner_id, deleted_at, created_at desc);

-- The API validates values and RLS continues to enforce row ownership.
grant update (filename, folder_path, deleted_at) on table public.doka_documents to authenticated;
