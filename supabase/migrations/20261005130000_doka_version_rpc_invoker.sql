-- Replace the legacy SECURITY DEFINER version RPCs with owner-scoped SECURITY INVOKER functions.
-- Authenticated callers are protected by table RLS and explicit auth.uid() predicates.
create or replace function public.doka_replace_document_version(
  p_document_id uuid,
  p_object_key text,
  p_filename text,
  p_content_type text,
  p_size_bytes bigint,
  p_sha256 text
)
returns setof public.doka_documents
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_owner uuid;
  v_next integer;
begin
  if (select auth.uid()) is null then
    return;
  end if;

  select owner_id into v_owner
  from public.doka_documents
  where id = p_document_id
  for update;

  if v_owner is null or v_owner <> (select auth.uid()) then
    return;
  end if;

  if p_size_bytes < 0 or p_sha256 !~ '^[0-9a-fA-F]{64}$' then
    raise exception 'invalid version metadata';
  end if;

  select coalesce(max(version_no), 0) + 1
    into v_next
  from public.doka_document_versions
  where document_id = p_document_id;

  insert into public.doka_document_versions (
    document_id, version_no, object_key, size_bytes, sha256,
    filename, content_type, storage_provider, storage_status
  )
  values (
    p_document_id, v_next, p_object_key, p_size_bytes, lower(p_sha256),
    p_filename, p_content_type, 'supabase', 'ready'
  );

  update public.doka_documents
  set object_key = p_object_key,
      filename = p_filename,
      content_type = p_content_type,
      size_bytes = p_size_bytes,
      sha256 = lower(p_sha256),
      storage_provider = 'supabase',
      storage_status = 'ready',
      updated_at = now()
  where id = p_document_id
    and owner_id = (select auth.uid());

  return query
    select d.*
    from public.doka_documents d
    where d.id = p_document_id
      and d.owner_id = (select auth.uid());
end;
$$;

create or replace function public.doka_restore_document_version(
  p_document_id uuid,
  p_version_id uuid
)
returns setof public.doka_documents
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_owner uuid;
  v_version public.doka_document_versions%rowtype;
begin
  if (select auth.uid()) is null then
    return;
  end if;

  select owner_id into v_owner
  from public.doka_documents
  where id = p_document_id
  for update;

  if v_owner is null or v_owner <> (select auth.uid()) then
    return;
  end if;

  select *
    into v_version
  from public.doka_document_versions
  where id = p_version_id
    and document_id = p_document_id;

  if not found then
    return;
  end if;

  update public.doka_documents
  set object_key = v_version.object_key,
      filename = v_version.filename,
      content_type = v_version.content_type,
      size_bytes = v_version.size_bytes,
      sha256 = v_version.sha256,
      storage_provider = v_version.storage_provider,
      storage_status = v_version.storage_status,
      updated_at = now()
  where id = p_document_id
    and owner_id = (select auth.uid());

  return query
    select d.*
    from public.doka_documents d
    where d.id = p_document_id
      and d.owner_id = (select auth.uid());
end;
$$;

revoke all on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) from public, anon;
revoke all on function public.doka_restore_document_version(uuid,uuid) from public, anon;
grant execute on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) to authenticated;
grant execute on function public.doka_restore_document_version(uuid,uuid) to authenticated;
