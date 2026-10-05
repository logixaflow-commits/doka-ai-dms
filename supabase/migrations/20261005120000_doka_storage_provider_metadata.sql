-- Backward-compatible Cloud Edition storage metadata.
-- IMPORTANT: this migration is metadata-only. It never copies, deletes, moves,
-- or rewrites bytes in storage. Existing objects remain Supabase-backed.

alter table public.doka_documents
  add column if not exists storage_provider text not null default 'supabase',
  add column if not exists storage_status text not null default 'ready',
  add column if not exists storage_region text,
  add column if not exists preview_provider text,
  add column if not exists preview_object_key text,
  add column if not exists export_provider text,
  add column if not exists export_reference text,
  add column if not exists export_status text,
  add column if not exists backup_provider text,
  add column if not exists backup_reference text,
  add column if not exists backup_status text;

alter table public.doka_document_versions
  add column if not exists storage_provider text not null default 'supabase',
  add column if not exists storage_status text not null default 'ready',
  add column if not exists storage_region text;

-- Existing rows are explicitly pinned to Supabase. This is the rollback-safe
-- default and does not touch storage objects.
update public.doka_documents
set storage_provider = 'supabase'
where storage_provider is null or btrim(storage_provider) = '';

update public.doka_document_versions
set storage_provider = 'supabase'
where storage_provider is null or btrim(storage_provider) = '';

alter table public.doka_documents
  drop constraint if exists doka_documents_storage_provider_check,
  drop constraint if exists doka_documents_storage_status_check,
  drop constraint if exists doka_documents_preview_provider_check,
  drop constraint if exists doka_documents_export_provider_check,
  drop constraint if exists doka_documents_backup_provider_check;

alter table public.doka_document_versions
  drop constraint if exists doka_document_versions_storage_provider_check,
  drop constraint if exists doka_document_versions_storage_status_check;

alter table public.doka_documents
  add constraint doka_documents_storage_provider_check
    check (storage_provider in ('supabase', 'b2', 'mock')),
  add constraint doka_documents_storage_status_check
    check (storage_status in ('pending', 'uploading', 'ready', 'quarantined', 'failed', 'deleting')),
  add constraint doka_documents_preview_provider_check
    check (preview_provider is null or preview_provider in ('cloudinary', 'supabase', 'mock')),
  add constraint doka_documents_export_provider_check
    check (export_provider is null or export_provider in ('google_drive')),
  add constraint doka_documents_backup_provider_check
    check (backup_provider is null or backup_provider in ('google_drive'));

alter table public.doka_document_versions
  add constraint doka_document_versions_storage_provider_check
    check (storage_provider in ('supabase', 'b2', 'mock')),
  add constraint doka_document_versions_storage_status_check
    check (storage_status in ('pending', 'uploading', 'ready', 'quarantined', 'failed', 'deleting'));

create index if not exists doka_documents_storage_provider_idx
  on public.doka_documents(storage_provider, storage_status);

create index if not exists doka_document_versions_storage_provider_idx
  on public.doka_document_versions(storage_provider, storage_status);

comment on column public.doka_documents.storage_provider is
  'Primary source-object provider. Existing documents default to supabase; transitions are lazy and verified before metadata changes.';
comment on column public.doka_documents.storage_status is
  'Storage lifecycle state. Only verified objects may become ready.';
comment on column public.doka_documents.preview_provider is
  'Derivative provider for preview/thumbnail/cover artifacts; independent from source storage_provider.';
comment on column public.doka_documents.export_provider is
  'Explicit export destination; Google Drive is never normal source storage.';
comment on column public.doka_documents.backup_provider is
  'Explicit backup destination; Google Drive is never normal source storage.';
