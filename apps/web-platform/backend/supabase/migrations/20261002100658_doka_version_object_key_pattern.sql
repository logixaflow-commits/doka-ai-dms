-- Require a SHA-bound, single safe object-key segment in both version RPCs.
create or replace function public.doka_replace_document_version(
  p_document_id uuid, p_object_key text, p_filename text, p_content_type text,
  p_size_bytes bigint, p_sha256 text
) returns public.doka_documents
language plpgsql
security definer
set search_path = pg_catalog, public, pg_temp
as $$
declare
  current_doc public.doka_documents;
  next_no integer;
  updated_doc public.doka_documents;
begin
  if auth.uid() is null then
    raise exception 'Authentication required' using errcode = '42501';
  end if;
  if p_document_id is null
     or p_sha256 is null or p_sha256 !~ '^[0-9a-f]{64}$'
     or p_size_bytes is null or p_size_bytes < 0
     or p_object_key is null
     or p_object_key !~ ('^users/' || auth.uid()::text || '/documents/' || p_sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     or p_filename is null or btrim(p_filename) in ('', '.', '..')
     or length(p_filename) > 255
     or position('/' in p_filename) > 0 or position(chr(92) in p_filename) > 0
     or p_content_type is null or btrim(p_content_type) = ''
     or length(p_content_type) > 255 or position('/' in p_content_type) = 0 then
    raise exception 'Invalid version object metadata' using errcode = '22023';
  end if;
  select * into current_doc
  from public.doka_documents
  where id = p_document_id and owner_id = auth.uid() and deleted_at is null
  for update;
  if not found then
    raise exception 'Document not found' using errcode = 'P0002';
  end if;
  if current_doc.sha256 is null or current_doc.sha256 !~ '^[0-9a-f]{64}$'
     or current_doc.object_key !~ ('^users/' || auth.uid()::text || '/documents/' || current_doc.sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$') then
    raise exception 'Current document storage key is invalid' using errcode = '22023';
  end if;
  select coalesce(max(version_no), 0) + 1 into next_no
  from public.doka_document_versions where document_id = p_document_id;
  insert into public.doka_document_versions(document_id, version_no, object_key, size_bytes, sha256, filename, content_type)
  values (p_document_id, next_no, current_doc.object_key, current_doc.size_bytes, current_doc.sha256, current_doc.filename, current_doc.content_type);
  update public.doka_documents
  set object_key = p_object_key, filename = p_filename, content_type = p_content_type,
      size_bytes = p_size_bytes, sha256 = p_sha256, updated_at = now()
  where id = p_document_id returning * into updated_doc;
  return updated_doc;
end;
$$;

create or replace function public.doka_restore_document_version(
  p_document_id uuid, p_version_id uuid
) returns public.doka_documents
language plpgsql
security definer
set search_path = pg_catalog, public, pg_temp
as $$
declare
  current_doc public.doka_documents;
  chosen public.doka_document_versions;
  next_no integer;
  updated_doc public.doka_documents;
begin
  if auth.uid() is null then
    raise exception 'Authentication required' using errcode = '42501';
  end if;
  if p_document_id is null or p_version_id is null then
    raise exception 'Document and version are required' using errcode = '22023';
  end if;
  select * into current_doc
  from public.doka_documents
  where id = p_document_id and owner_id = auth.uid() and deleted_at is null
  for update;
  if not found then
    raise exception 'Document not found' using errcode = 'P0002';
  end if;
  if current_doc.sha256 is null or current_doc.sha256 !~ '^[0-9a-f]{64}$'
     or current_doc.object_key !~ ('^users/' || auth.uid()::text || '/documents/' || current_doc.sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$') then
    raise exception 'Current document storage key is invalid' using errcode = '22023';
  end if;
  select * into chosen from public.doka_document_versions
  where id = p_version_id and document_id = p_document_id;
  if not found then
    raise exception 'Version not found' using errcode = 'P0002';
  end if;
  if chosen.object_key is null
     or chosen.sha256 is null or chosen.sha256 !~ '^[0-9a-f]{64}$'
     or chosen.object_key !~ ('^users/' || auth.uid()::text || '/documents/' || chosen.sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     or chosen.size_bytes is null or chosen.size_bytes < 0
     or (chosen.filename is not null and (
       btrim(chosen.filename) in ('', '.', '..') or length(chosen.filename) > 255
       or position('/' in chosen.filename) > 0 or position(chr(92) in chosen.filename) > 0
     ))
     or (chosen.content_type is not null and (
       btrim(chosen.content_type) = '' or length(chosen.content_type) > 255
       or position('/' in chosen.content_type) = 0
     )) then
    raise exception 'Stored version metadata is invalid' using errcode = '22023';
  end if;
  select coalesce(max(version_no), 0) + 1 into next_no
  from public.doka_document_versions where document_id = p_document_id;
  insert into public.doka_document_versions(document_id, version_no, object_key, size_bytes, sha256, filename, content_type)
  values (p_document_id, next_no, current_doc.object_key, current_doc.size_bytes, current_doc.sha256, current_doc.filename, current_doc.content_type);
  update public.doka_documents
  set object_key = chosen.object_key, filename = coalesce(chosen.filename, current_doc.filename),
      content_type = coalesce(chosen.content_type, current_doc.content_type),
      size_bytes = chosen.size_bytes, sha256 = chosen.sha256, updated_at = now()
  where id = p_document_id returning * into updated_doc;
  return updated_doc;
end;
$$;

revoke all on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) from public, anon;
revoke all on function public.doka_restore_document_version(uuid,uuid) from public, anon;
grant execute on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) to authenticated;
grant execute on function public.doka_restore_document_version(uuid,uuid) to authenticated;

comment on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) is
  'Authenticated owner-only atomic version replacement. SECURITY DEFINER is required to keep storage pointer columns unavailable to direct REST updates; validates auth.uid(), owner, SHA-bound single-segment object key, filename, MIME type and narrow EXECUTE ACL.';
comment on function public.doka_restore_document_version(uuid,uuid) is
  'Authenticated owner-only atomic version restore. SECURITY DEFINER is required to keep storage pointer columns unavailable to direct REST updates; validates auth.uid(), document/version ownership, SHA-bound single-segment object key, metadata and narrow EXECUTE ACL.';
