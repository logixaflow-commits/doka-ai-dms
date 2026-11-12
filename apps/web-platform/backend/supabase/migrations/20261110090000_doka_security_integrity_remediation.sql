-- Production-first remediation: keep audit/version writes server-controlled
-- while using the caller's verified Supabase JWT (no service-role key in Worker).
-- Every SECURITY DEFINER RPC performs an explicit auth.uid() owner check.

REVOKE INSERT ON TABLE public.doka_audit_events FROM authenticated;
REVOKE INSERT ON TABLE public.doka_document_versions FROM authenticated;
DROP POLICY IF EXISTS doka_audit_owner_insert ON public.doka_audit_events;
DROP POLICY IF EXISTS doka_versions_owner_insert ON public.doka_document_versions;

CREATE OR REPLACE FUNCTION public.doka_record_audit_event(
  p_owner_id uuid,
  p_action text,
  p_document_id uuid DEFAULT NULL,
  p_filename text DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
BEGIN
  IF auth.uid() IS NULL OR p_owner_id IS DISTINCT FROM auth.uid()
     OR p_action IS NULL
     OR p_action NOT IN ('upload','download','update','trash','restore','permanent_delete',
                         'preview','export','version_create','version_restore')
     OR (p_filename IS NOT NULL AND length(p_filename) > 255)
     OR p_metadata IS NULL OR jsonb_typeof(p_metadata) <> 'object' THEN
    RAISE EXCEPTION 'Invalid audit event' USING errcode = '22023';
  END IF;

  IF p_document_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.doka_documents
    WHERE id = p_document_id AND owner_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'Audit document ownership mismatch' USING errcode = '42501';
  END IF;

  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (auth.uid(), p_document_id, p_action, p_filename, p_metadata);
END;
$function$;

REVOKE ALL ON FUNCTION public.doka_record_audit_event(uuid, text, uuid, text, jsonb)
  FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION public.doka_record_audit_event(uuid, text, uuid, text, jsonb)
  TO authenticated;

-- Bulk update remains atomic and can append its audit events after direct table
-- INSERT is revoked. SECURITY DEFINER is safe here because every target row is
-- checked against auth.uid() before any update or audit write.
CREATE OR REPLACE FUNCTION public.doka_bulk_update_documents(
  p_document_ids uuid[],
  p_action text,
  p_status text DEFAULT NULL
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  matched_count integer;
  audit_action text;
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'Authentication required' USING errcode = '42501';
  END IF;
  IF p_document_ids IS NULL OR cardinality(p_document_ids) < 1 OR cardinality(p_document_ids) > 100
     OR cardinality(p_document_ids) <> (SELECT count(DISTINCT x) FROM unnest(p_document_ids) AS x) THEN
    RAISE EXCEPTION 'Select between 1 and 100 unique documents' USING errcode = '22023';
  END IF;
  IF p_action IS NULL OR p_action NOT IN ('status','trash') THEN
    RAISE EXCEPTION 'Unsupported bulk action' USING errcode = '22023';
  END IF;
  IF p_action = 'status' AND (p_status IS NULL OR p_status NOT IN ('active','review','quarantined','archived')) THEN
    RAISE EXCEPTION 'Invalid document status' USING errcode = '22023';
  END IF;

  SELECT count(*) INTO matched_count
  FROM public.doka_documents
  WHERE id = ANY(p_document_ids) AND owner_id = auth.uid() AND deleted_at IS NULL
  FOR UPDATE;
  IF matched_count <> cardinality(p_document_ids) THEN
    RAISE EXCEPTION 'One or more documents are unavailable' USING errcode = 'P0002';
  END IF;

  IF p_action = 'status' THEN
    UPDATE public.doka_documents SET status = p_status
    WHERE id = ANY(p_document_ids) AND owner_id = auth.uid() AND deleted_at IS NULL;
    audit_action := 'update';
  ELSE
    UPDATE public.doka_documents SET deleted_at = now()
    WHERE id = ANY(p_document_ids) AND owner_id = auth.uid() AND deleted_at IS NULL;
    audit_action := 'trash';
  END IF;

  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  SELECT d.owner_id, d.id, audit_action, d.filename, jsonb_build_object('bulk', true)
  FROM public.doka_documents AS d
  WHERE d.id = ANY(p_document_ids) AND d.owner_id = auth.uid();

  RETURN QUERY
  SELECT d.* FROM public.doka_documents AS d
  WHERE d.id = ANY(p_document_ids) AND d.owner_id = auth.uid()
  ORDER BY d.created_at DESC;
END;
$function$;

REVOKE ALL ON FUNCTION public.doka_bulk_update_documents(uuid[], text, text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.doka_bulk_update_documents(uuid[], text, text) TO authenticated;

-- Version replacement/restore are privileged only inside narrowly scoped RPCs.
-- Object keys must be SHA-bound and inside the authenticated user's own prefix.
CREATE OR REPLACE FUNCTION public.doka_replace_document_version(
  p_document_id uuid, p_object_key text, p_filename text, p_content_type text,
  p_size_bytes bigint, p_sha256 text
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  current_doc public.doka_documents;
  next_no integer;
BEGIN
  IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_id IS NULL OR p_sha256 IS NULL OR p_sha256 !~ '^[0-9a-f]{64}$'
     OR p_size_bytes IS NULL OR p_size_bytes < 0
     OR p_object_key IS NULL
     OR p_object_key !~ ('^users/' || auth.uid()::text || '/documents/' || p_sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     OR p_filename IS NULL OR btrim(p_filename) IN ('', '.', '..') OR length(p_filename) > 255
     OR position('/' in p_filename) > 0 OR position(chr(92) in p_filename) > 0
     OR p_content_type IS NULL OR btrim(p_content_type) = '' OR length(p_content_type) > 255
     OR position('/' in p_content_type) = 0 THEN
    RAISE EXCEPTION 'Invalid version object metadata' USING errcode = '22023';
  END IF;

  SELECT * INTO current_doc FROM public.doka_documents
  WHERE id = p_document_id AND owner_id = auth.uid() AND deleted_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING errcode = 'P0002'; END IF;

  SELECT coalesce(max(version_no), 0) + 1 INTO next_no
  FROM public.doka_document_versions WHERE document_id = p_document_id;
  INSERT INTO public.doka_document_versions(
    document_id, version_no, object_key, size_bytes, sha256, filename, content_type,
    storage_provider, storage_status, storage_region
  ) VALUES (
    p_document_id, next_no, p_object_key, p_size_bytes, lower(p_sha256), p_filename,
    p_content_type, 'supabase', 'ready', NULL
  );

  UPDATE public.doka_documents
  SET object_key = p_object_key, filename = p_filename, content_type = p_content_type,
      size_bytes = p_size_bytes, sha256 = lower(p_sha256), storage_provider = 'supabase',
      storage_status = 'ready', storage_region = NULL, updated_at = now()
  WHERE id = p_document_id AND owner_id = auth.uid();

  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (auth.uid(), p_document_id, 'version_create', p_filename, jsonb_build_object('storage_provider','supabase'));

  RETURN QUERY SELECT d.* FROM public.doka_documents d WHERE d.id = p_document_id AND d.owner_id = auth.uid();
END;
$function$;

CREATE OR REPLACE FUNCTION public.doka_replace_document_version_storage(
  p_document_id uuid, p_object_key text, p_filename text, p_content_type text,
  p_size_bytes bigint, p_sha256 text, p_storage_provider text, p_storage_region text DEFAULT NULL
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  current_doc public.doka_documents;
  next_no integer;
BEGIN
  IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_id IS NULL OR p_sha256 IS NULL OR p_sha256 !~ '^[0-9a-f]{64}$'
     OR p_size_bytes IS NULL OR p_size_bytes < 0
     OR p_object_key IS NULL
     OR p_object_key !~ ('^users/' || auth.uid()::text || '/documents/' || p_sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     OR p_filename IS NULL OR btrim(p_filename) IN ('', '.', '..') OR length(p_filename) > 255
     OR position('/' in p_filename) > 0 OR position(chr(92) in p_filename) > 0
     OR p_content_type IS NULL OR btrim(p_content_type) = '' OR length(p_content_type) > 255
     OR position('/' in p_content_type) = 0
     OR p_storage_provider NOT IN ('supabase','b2')
     OR (p_storage_region IS NOT NULL AND length(p_storage_region) > 128) THEN
    RAISE EXCEPTION 'Invalid version object metadata' USING errcode = '22023';
  END IF;

  SELECT * INTO current_doc FROM public.doka_documents
  WHERE id = p_document_id AND owner_id = auth.uid() AND deleted_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING errcode = 'P0002'; END IF;

  SELECT coalesce(max(version_no), 0) + 1 INTO next_no
  FROM public.doka_document_versions WHERE document_id = p_document_id;
  INSERT INTO public.doka_document_versions(
    document_id, version_no, object_key, size_bytes, sha256, filename, content_type,
    storage_provider, storage_status, storage_region
  ) VALUES (
    p_document_id, next_no, p_object_key, p_size_bytes, lower(p_sha256), p_filename,
    p_content_type, p_storage_provider, 'ready', p_storage_region
  );

  UPDATE public.doka_documents
  SET object_key = p_object_key, filename = p_filename, content_type = p_content_type,
      size_bytes = p_size_bytes, sha256 = lower(p_sha256), storage_provider = p_storage_provider,
      storage_status = 'ready', storage_region = p_storage_region, updated_at = now()
  WHERE id = p_document_id AND owner_id = auth.uid();

  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (auth.uid(), p_document_id, 'version_create', p_filename, jsonb_build_object('storage_provider',p_storage_provider));

  RETURN QUERY SELECT d.* FROM public.doka_documents d WHERE d.id = p_document_id AND d.owner_id = auth.uid();
END;
$function$;

CREATE OR REPLACE FUNCTION public.doka_restore_document_version(
  p_document_id uuid, p_version_id uuid
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  current_doc public.doka_documents;
  chosen public.doka_document_versions;
  next_no integer;
BEGIN
  IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_id IS NULL OR p_version_id IS NULL THEN
    RAISE EXCEPTION 'Document and version are required' USING errcode = '22023';
  END IF;

  SELECT * INTO current_doc FROM public.doka_documents
  WHERE id = p_document_id AND owner_id = auth.uid() AND deleted_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING errcode = 'P0002'; END IF;

  SELECT * INTO chosen FROM public.doka_document_versions
  WHERE id = p_version_id AND document_id = p_document_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Version not found' USING errcode = 'P0002'; END IF;
  IF chosen.sha256 IS NULL OR chosen.sha256 !~ '^[0-9a-f]{64}$'
     OR chosen.object_key !~ ('^users/' || auth.uid()::text || '/documents/' || chosen.sha256 || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     OR chosen.size_bytes < 0 OR chosen.storage_provider NOT IN ('supabase','b2')
     OR (chosen.filename IS NOT NULL AND (btrim(chosen.filename) IN ('','.', '..') OR length(chosen.filename) > 255
         OR position('/' in chosen.filename) > 0 OR position(chr(92) in chosen.filename) > 0))
     OR (chosen.content_type IS NOT NULL AND (btrim(chosen.content_type) = '' OR length(chosen.content_type) > 255
         OR position('/' in chosen.content_type) = 0)) THEN
    RAISE EXCEPTION 'Stored version metadata is invalid' USING errcode = '22023';
  END IF;

  SELECT coalesce(max(version_no), 0) + 1 INTO next_no
  FROM public.doka_document_versions WHERE document_id = p_document_id;
  INSERT INTO public.doka_document_versions(
    document_id, version_no, object_key, size_bytes, sha256, filename, content_type,
    storage_provider, storage_status, storage_region
  ) VALUES (
    p_document_id, next_no, current_doc.object_key, current_doc.size_bytes, current_doc.sha256,
    current_doc.filename, current_doc.content_type, current_doc.storage_provider,
    current_doc.storage_status, current_doc.storage_region
  );

  UPDATE public.doka_documents
  SET object_key = chosen.object_key, filename = coalesce(chosen.filename, current_doc.filename),
      content_type = coalesce(chosen.content_type, current_doc.content_type),
      size_bytes = chosen.size_bytes, sha256 = chosen.sha256,
      storage_provider = chosen.storage_provider, storage_status = chosen.storage_status,
      storage_region = chosen.storage_region, updated_at = now()
  WHERE id = p_document_id AND owner_id = auth.uid();

  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (auth.uid(), p_document_id, 'version_restore', coalesce(chosen.filename,current_doc.filename),
          jsonb_build_object('restored_version_id',p_version_id));

  RETURN QUERY SELECT d.* FROM public.doka_documents d WHERE d.id = p_document_id AND d.owner_id = auth.uid();
END;
$function$;

REVOKE ALL ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.doka_restore_document_version(uuid,uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_restore_document_version(uuid,uuid) TO authenticated;
