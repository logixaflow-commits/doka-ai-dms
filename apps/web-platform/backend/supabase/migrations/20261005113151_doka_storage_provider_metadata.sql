-- Additive metadata-only storage routing fields. Existing objects remain in place.
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

update public.doka_documents set storage_provider = 'supabase' where storage_provider is null or btrim(storage_provider)='';
update public.doka_documents set storage_status = 'ready' where storage_status is null or btrim(storage_status)='';
update public.doka_document_versions set storage_provider='supabase' where storage_provider is null or btrim(storage_provider)='';
update public.doka_document_versions set storage_status='ready' where storage_status is null or btrim(storage_status)='';

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
  add constraint doka_documents_storage_provider_check check (storage_provider in ('supabase', 'b2', 'mock')),
  add constraint doka_documents_storage_status_check check (storage_status in ('pending', 'uploading', 'ready', 'quarantined', 'failed', 'deleting')),
  add constraint doka_documents_preview_provider_check check (preview_provider is null or preview_provider in ('cloudinary', 'supabase', 'mock')),
  add constraint doka_documents_export_provider_check check (export_provider is null or export_provider in ('google_drive')),
  add constraint doka_documents_backup_provider_check check (backup_provider is null or backup_provider in ('google_drive'));

alter table public.doka_document_versions
  add constraint doka_document_versions_storage_provider_check check (storage_provider in ('supabase','b2','mock')),
  add constraint doka_document_versions_storage_status_check check (storage_status in ('pending','uploading','ready','quarantined','failed','deleting'));

create index if not exists doka_documents_storage_provider_status_idx
  on public.doka_documents(storage_provider, storage_status);
create index if not exists doka_document_versions_storage_provider_status_idx
  on public.doka_document_versions(storage_provider, storage_status);
