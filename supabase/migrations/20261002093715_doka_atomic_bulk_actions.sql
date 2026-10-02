-- Atomic owner-scoped bulk status and Trash operations. Runs as invoker under existing grants/RLS.
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
  if p_action not in ('status','trash') then
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
    update public.doka_documents set status = p_status, updated_at = now()
    where id = any(p_document_ids) and owner_id = auth.uid() and deleted_at is null;
    audit_action := 'update';
  else
    update public.doka_documents set deleted_at = now(), updated_at = now()
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

revoke all on function public.doka_bulk_update_documents(uuid[],text,text) from public, anon;
grant execute on function public.doka_bulk_update_documents(uuid[],text,text) to authenticated;
