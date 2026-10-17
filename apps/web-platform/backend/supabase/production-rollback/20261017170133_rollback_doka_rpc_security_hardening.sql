-- Production-only compensating rollback recorded as migration 20261017170133.
-- Intentionally outside supabase/migrations: applying this to staging would undo its guarded RPC test setup.
-- Restores the pre-hardening SECURITY INVOKER definitions and authenticated-only ACL.

-- Reject NULL actions explicitly; SQL three-valued logic must not route NULL to Trash.
create or replace function public.doka_bulk_update_documents(
  p_document_ids uuid[],
  p_action text,
  p_status text default null
) returns setof public.doka_documents
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  matched_count integer;
  audit_action text;
begin
  if p_document_ids is null or cardinality(p_document_ids) < 1 or cardinality(p_document_ids) > 100 then
    raise exception 'Select between 1 and 100 documents' using errcode = '22023';
  end if;
  if p_action is null or p_action not in ('status','trash') then
    raise exception 'Unsupported bulk action' using errcode = '22023';
  end if;
  if p_action = 'status' and (p_status is null or p_status not in ('active','review','quarantined','archived')) then
    raise exception 'Invalid document status' using errcode = '22023';
  end if;
  select count(*) into matched_count from public.doka_documents
  where id = any(p_document_ids) and owner_id = auth.uid() and deleted_at is null;
  if matched_count <> cardinality(p_document_ids) then
    raise exception 'One or more documents are unavailable' using errcode = 'P0002';
  end if;

  if p_action = 'status' then
    update public.doka_documents set status = p_status
    where id = any(p_document_ids) and owner_id = auth.uid() and deleted_at is null;
    audit_action := 'update';
  else
    update public.doka_documents set deleted_at = now()
    where id = any(p_document_ids) and owner_id = auth.uid() and deleted_at is null;
    audit_action := 'trash';
  end if;

  insert into public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  select owner_id, id, audit_action, filename, jsonb_build_object('bulk', true)
  from public.doka_documents where id = any(p_document_ids) and owner_id = auth.uid();

  return query select * from public.doka_documents
  where id = any(p_document_ids) and owner_id = auth.uid()
  order by created_at desc;
end;
$$;


-- Replace the legacy SECURITY DEFINER version RPCs with owner-scoped SECURITY INVOKER functions.
create or replace function public.doka_replace_document_version(
  p_document_id uuid,p_object_key text,p_filename text,p_content_type text,p_size_bytes bigint,p_sha256 text
)
returns setof public.doka_documents
language plpgsql security invoker set search_path = public
as $$
declare v_owner uuid; v_next integer;
begin
  if (select auth.uid()) is null then return; end if;
  select owner_id into v_owner from public.doka_documents where id=p_document_id for update;
  if v_owner is null or v_owner <> (select auth.uid()) then return; end if;
  if p_size_bytes < 0 or p_sha256 !~ '^[0-9a-fA-F]{64}$' then raise exception 'invalid version metadata'; end if;
  select coalesce(max(version_no),0)+1 into v_next from public.doka_document_versions where document_id=p_document_id;
  insert into public.doka_document_versions(document_id,version_no,object_key,size_bytes,sha256,filename,content_type,storage_provider,storage_status)
  values(p_document_id,v_next,p_object_key,p_size_bytes,lower(p_sha256),p_filename,p_content_type,'supabase','ready');
  update public.doka_documents
  set object_key=p_object_key,filename=p_filename,content_type=p_content_type,size_bytes=p_size_bytes,sha256=lower(p_sha256),storage_provider='supabase',storage_status='ready',updated_at=now()
  where id=p_document_id and owner_id=(select auth.uid());
  return query select d.* from public.doka_documents d where d.id=p_document_id and d.owner_id=(select auth.uid());
end;
$$;

create or replace function public.doka_restore_document_version(p_document_id uuid,p_version_id uuid)
returns setof public.doka_documents
language plpgsql security invoker set search_path = public
as $$
declare v_owner uuid; v_version public.doka_document_versions%rowtype;
begin
  if (select auth.uid()) is null then return; end if;
  select owner_id into v_owner from public.doka_documents where id=p_document_id for update;
  if v_owner is null or v_owner <> (select auth.uid()) then return; end if;
  select * into v_version from public.doka_document_versions where id=p_version_id and document_id=p_document_id;
  if not found then return; end if;
  update public.doka_documents
  set object_key=v_version.object_key,filename=v_version.filename,content_type=v_version.content_type,size_bytes=v_version.size_bytes,sha256=v_version.sha256,storage_provider=v_version.storage_provider,storage_status=v_version.storage_status,updated_at=now()
  where id=p_document_id and owner_id=(select auth.uid());
  return query select d.* from public.doka_documents d where d.id=p_document_id and d.owner_id=(select auth.uid());
end;
$$;

revoke all on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) from public,anon;
revoke all on function public.doka_restore_document_version(uuid,uuid) from public,anon;
grant execute on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) to authenticated;
grant execute on function public.doka_restore_document_version(uuid,uuid) to authenticated;


-- Owner-scoped storage-aware version replacement for direct cloud uploads.
create or replace function public.doka_replace_document_version_storage(
  p_document_id uuid,p_object_key text,p_filename text,p_content_type text,p_size_bytes bigint,p_sha256 text,
  p_storage_provider text,p_storage_region text default null
)
returns setof public.doka_documents
language plpgsql security invoker set search_path = public
as $$
declare v_owner uuid; v_next integer;
begin
  if (select auth.uid()) is null then return; end if;
  select owner_id into v_owner from public.doka_documents where id=p_document_id for update;
  if v_owner is null or v_owner <> (select auth.uid()) then return; end if;
  if p_size_bytes < 0 or p_sha256 !~ '^[0-9a-fA-F]{64}$' then raise exception 'invalid version metadata'; end if;
  if p_storage_provider not in ('supabase','b2','mock') then raise exception 'invalid storage provider'; end if;
  select coalesce(max(version_no),0)+1 into v_next from public.doka_document_versions where document_id=p_document_id;
  insert into public.doka_document_versions(document_id,version_no,object_key,size_bytes,sha256,filename,content_type,storage_provider,storage_status,storage_region)
  values(p_document_id,v_next,p_object_key,p_size_bytes,lower(p_sha256),p_filename,p_content_type,p_storage_provider,'ready',p_storage_region);
  update public.doka_documents
  set object_key=p_object_key,filename=p_filename,content_type=p_content_type,size_bytes=p_size_bytes,sha256=lower(p_sha256),storage_provider=p_storage_provider,storage_status='ready',storage_region=p_storage_region,updated_at=now()
  where id=p_document_id and owner_id=(select auth.uid());
  return query select d.* from public.doka_documents d where d.id=p_document_id and d.owner_id=(select auth.uid());
end;
$$;
revoke all on function public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) from public,anon;
grant execute on function public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) to authenticated;


-- Restore the pre-hardening production ACL: authenticated RPC only; no anon/public/service_role grants.
REVOKE ALL ON FUNCTION public.doka_bulk_update_documents(uuid[],text,text) FROM PUBLIC, anon, service_role;
REVOKE ALL ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) FROM PUBLIC, anon, service_role;
REVOKE ALL ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) FROM PUBLIC, anon, service_role;
REVOKE ALL ON FUNCTION public.doka_restore_document_version(uuid,uuid) FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION public.doka_bulk_update_documents(uuid[],text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_restore_document_version(uuid,uuid) TO authenticated;
