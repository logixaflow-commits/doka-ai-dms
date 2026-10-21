-- REVIEW CANDIDATE ONLY: do not move into supabase/migrations or apply until issue #82
-- staging A/B + authenticated lifecycle acceptance and migration-ledger reconciliation pass.
-- Bulk status/trash stays SECURITY INVOKER; only RPCs that must update protected
-- storage-pointer columns use SECURITY DEFINER with explicit auth.uid() owner checks.
-- All functions use a fixed search_path, strict SHA-bound single-segment object keys,
-- and authenticated-only EXECUTE ACLs. No production or staging database has been changed.

CREATE OR REPLACE FUNCTION public.doka_bulk_update_documents(
  p_document_ids uuid[], p_action text, p_status text DEFAULT NULL
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  v_user uuid := auth.uid();
  matched_count integer;
  audit_action text;
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_ids IS NULL OR cardinality(p_document_ids) < 1 OR cardinality(p_document_ids) > 100 THEN
    RAISE EXCEPTION 'Select between 1 and 100 documents' USING errcode = '22023';
  END IF;
  IF p_action IS NULL OR p_action NOT IN ('status', 'trash') THEN
    RAISE EXCEPTION 'Unsupported bulk action' USING errcode = '22023';
  END IF;
  IF p_action = 'status' AND (p_status IS NULL OR p_status NOT IN ('active', 'review', 'quarantined', 'archived')) THEN
    RAISE EXCEPTION 'Invalid document status' USING errcode = '22023';
  END IF;
  SELECT count(*) INTO matched_count FROM public.doka_documents
  WHERE id = ANY(p_document_ids) AND owner_id = v_user AND deleted_at IS NULL;
  IF matched_count <> cardinality(p_document_ids) THEN
    RAISE EXCEPTION 'One or more documents are unavailable' USING errcode = 'P0002';
  END IF;
  IF p_action = 'status' THEN
    UPDATE public.doka_documents SET status = p_status
    WHERE id = ANY(p_document_ids) AND owner_id = v_user AND deleted_at IS NULL;
    audit_action := 'update';
  ELSE
    UPDATE public.doka_documents SET deleted_at = now()
    WHERE id = ANY(p_document_ids) AND owner_id = v_user AND deleted_at IS NULL;
    audit_action := 'trash';
  END IF;
  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  SELECT owner_id, id, audit_action, filename, pg_catalog.jsonb_build_object('bulk', true)
  FROM public.doka_documents WHERE id = ANY(p_document_ids) AND owner_id = v_user;
  RETURN QUERY SELECT * FROM public.doka_documents
  WHERE id = ANY(p_document_ids) AND owner_id = v_user ORDER BY created_at DESC;
END;
$function$;

CREATE OR REPLACE FUNCTION public.doka_replace_document_version_storage(
  p_document_id uuid, p_object_key text, p_filename text, p_content_type text,
  p_size_bytes bigint, p_sha256 text, p_storage_provider text, p_storage_region text DEFAULT NULL
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  v_user uuid := auth.uid();
  current_doc public.doka_documents;
  next_no integer;
  updated_doc public.doka_documents;
  v_sha text := pg_catalog.lower(p_sha256);
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_id IS NULL OR p_object_key IS NULL
     OR p_filename IS NULL OR pg_catalog.btrim(p_filename) IN ('', '.', '..')
     OR pg_catalog.length(p_filename) > 255
     OR pg_catalog.strpos(p_filename, '/') > 0 OR pg_catalog.strpos(p_filename, pg_catalog.chr(92)) > 0
     OR p_content_type IS NULL OR pg_catalog.btrim(p_content_type) = ''
     OR pg_catalog.length(p_content_type) > 255 OR pg_catalog.strpos(p_content_type, '/') = 0
     OR p_size_bytes IS NULL OR p_size_bytes < 0
     OR p_sha256 IS NULL OR p_sha256 !~ '^[0-9a-fA-F]{64}$'
     OR p_object_key !~ ('^users/' || v_user::text || '/documents/' || v_sha || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     OR p_storage_provider IS NULL OR p_storage_provider NOT IN ('supabase', 'b2', 'mock')
     OR (p_storage_region IS NOT NULL AND pg_catalog.length(p_storage_region) > 128) THEN
    RAISE EXCEPTION 'Invalid version object metadata' USING errcode = '22023';
  END IF;
  SELECT * INTO current_doc FROM public.doka_documents
  WHERE id = p_document_id AND owner_id = v_user AND deleted_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING errcode = 'P0002'; END IF;
  IF current_doc.sha256 IS NULL OR current_doc.sha256 !~ '^[0-9a-fA-F]{64}$'
     OR current_doc.object_key IS NULL
     OR current_doc.object_key !~ ('^users/' || v_user::text || '/documents/' || pg_catalog.lower(current_doc.sha256) || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$') THEN
    RAISE EXCEPTION 'Current document storage key is invalid' USING errcode = '22023';
  END IF;
  SELECT coalesce(max(version_no), 0) + 1 INTO next_no
  FROM public.doka_document_versions WHERE document_id = p_document_id;
  INSERT INTO public.doka_document_versions(
    document_id, version_no, object_key, size_bytes, sha256, filename, content_type,
    storage_provider, storage_status, storage_region
  ) VALUES (
    p_document_id, next_no, current_doc.object_key, current_doc.size_bytes,
    pg_catalog.lower(current_doc.sha256), current_doc.filename, current_doc.content_type,
    current_doc.storage_provider, current_doc.storage_status, current_doc.storage_region
  );
  UPDATE public.doka_documents
  SET object_key = p_object_key, filename = p_filename, content_type = p_content_type,
      size_bytes = p_size_bytes, sha256 = v_sha, storage_provider = p_storage_provider,
      storage_status = 'ready', storage_region = p_storage_region, updated_at = now()
  WHERE id = p_document_id AND owner_id = v_user RETURNING * INTO updated_doc;
  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (v_user, p_document_id, 'version_create', p_filename,
    pg_catalog.jsonb_build_object('version_no', next_no, 'storage_provider', p_storage_provider, 'size_bytes', p_size_bytes));
  RETURN NEXT updated_doc;
END;
$function$;

CREATE OR REPLACE FUNCTION public.doka_replace_document_version(
  p_document_id uuid, p_object_key text, p_filename text, p_content_type text,
  p_size_bytes bigint, p_sha256 text
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  v_user uuid := auth.uid();
  current_doc public.doka_documents;
  next_no integer;
  updated_doc public.doka_documents;
  v_sha text := pg_catalog.lower(p_sha256);
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_id IS NULL OR p_object_key IS NULL
     OR p_filename IS NULL OR pg_catalog.btrim(p_filename) IN ('', '.', '..')
     OR pg_catalog.length(p_filename) > 255
     OR pg_catalog.strpos(p_filename, '/') > 0 OR pg_catalog.strpos(p_filename, pg_catalog.chr(92)) > 0
     OR p_content_type IS NULL OR pg_catalog.btrim(p_content_type) = ''
     OR pg_catalog.length(p_content_type) > 255 OR pg_catalog.strpos(p_content_type, '/') = 0
     OR p_size_bytes IS NULL OR p_size_bytes < 0
     OR p_sha256 IS NULL OR p_sha256 !~ '^[0-9a-fA-F]{64}$'
     OR p_object_key !~ ('^users/' || v_user::text || '/documents/' || v_sha || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$') THEN
    RAISE EXCEPTION 'Invalid version object metadata' USING errcode = '22023';
  END IF;
  SELECT * INTO current_doc FROM public.doka_documents
  WHERE id = p_document_id AND owner_id = v_user AND deleted_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING errcode = 'P0002'; END IF;
  IF current_doc.sha256 IS NULL OR current_doc.sha256 !~ '^[0-9a-fA-F]{64}$'
     OR current_doc.object_key IS NULL
     OR current_doc.object_key !~ ('^users/' || v_user::text || '/documents/' || pg_catalog.lower(current_doc.sha256) || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$') THEN
    RAISE EXCEPTION 'Current document storage key is invalid' USING errcode = '22023';
  END IF;
  SELECT coalesce(max(version_no), 0) + 1 INTO next_no
  FROM public.doka_document_versions WHERE document_id = p_document_id;
  INSERT INTO public.doka_document_versions(
    document_id, version_no, object_key, size_bytes, sha256, filename, content_type,
    storage_provider, storage_status, storage_region
  ) VALUES (
    p_document_id, next_no, current_doc.object_key, current_doc.size_bytes,
    pg_catalog.lower(current_doc.sha256), current_doc.filename, current_doc.content_type,
    current_doc.storage_provider, current_doc.storage_status, current_doc.storage_region
  );
  UPDATE public.doka_documents
  SET object_key = p_object_key, filename = p_filename, content_type = p_content_type,
      size_bytes = p_size_bytes, sha256 = v_sha, storage_provider = 'supabase',
      storage_status = 'ready', storage_region = NULL, updated_at = now()
  WHERE id = p_document_id AND owner_id = v_user RETURNING * INTO updated_doc;
  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (v_user, p_document_id, 'version_create', p_filename,
    pg_catalog.jsonb_build_object('version_no', next_no, 'storage_provider', 'supabase', 'size_bytes', p_size_bytes));
  RETURN NEXT updated_doc;
END;
$function$;

CREATE OR REPLACE FUNCTION public.doka_restore_document_version(
  p_document_id uuid, p_version_id uuid
) RETURNS SETOF public.doka_documents
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $function$
DECLARE
  v_user uuid := auth.uid();
  current_doc public.doka_documents;
  chosen public.doka_document_versions;
  next_no integer;
  updated_doc public.doka_documents;
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING errcode = '42501'; END IF;
  IF p_document_id IS NULL OR p_version_id IS NULL THEN
    RAISE EXCEPTION 'Document and version are required' USING errcode = '22023';
  END IF;
  SELECT * INTO current_doc FROM public.doka_documents
  WHERE id = p_document_id AND owner_id = v_user AND deleted_at IS NULL FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING errcode = 'P0002'; END IF;
  IF current_doc.sha256 IS NULL OR current_doc.sha256 !~ '^[0-9a-fA-F]{64}$'
     OR current_doc.object_key IS NULL
     OR current_doc.object_key !~ ('^users/' || v_user::text || '/documents/' || pg_catalog.lower(current_doc.sha256) || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$') THEN
    RAISE EXCEPTION 'Current document storage key is invalid' USING errcode = '22023';
  END IF;
  SELECT * INTO chosen FROM public.doka_document_versions
  WHERE id = p_version_id AND document_id = p_document_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Version not found' USING errcode = 'P0002'; END IF;
  IF chosen.object_key IS NULL OR chosen.sha256 IS NULL OR chosen.sha256 !~ '^[0-9a-fA-F]{64}$'
     OR chosen.object_key !~ ('^users/' || v_user::text || '/documents/' || pg_catalog.lower(chosen.sha256) || '/[A-Za-z0-9-][A-Za-z0-9._-]{0,254}$')
     OR chosen.size_bytes IS NULL OR chosen.size_bytes < 0
     OR (chosen.filename IS NOT NULL AND (
       pg_catalog.btrim(chosen.filename) IN ('', '.', '..') OR pg_catalog.length(chosen.filename) > 255
       OR pg_catalog.strpos(chosen.filename, '/') > 0 OR pg_catalog.strpos(chosen.filename, pg_catalog.chr(92)) > 0
     ))
     OR (chosen.content_type IS NOT NULL AND (
       pg_catalog.btrim(chosen.content_type) = '' OR pg_catalog.length(chosen.content_type) > 255
       OR pg_catalog.strpos(chosen.content_type, '/') = 0
     )) THEN
    RAISE EXCEPTION 'Stored version metadata is invalid' USING errcode = '22023';
  END IF;
  SELECT coalesce(max(version_no), 0) + 1 INTO next_no
  FROM public.doka_document_versions WHERE document_id = p_document_id;
  INSERT INTO public.doka_document_versions(
    document_id, version_no, object_key, size_bytes, sha256, filename, content_type,
    storage_provider, storage_status, storage_region
  ) VALUES (
    p_document_id, next_no, current_doc.object_key, current_doc.size_bytes,
    pg_catalog.lower(current_doc.sha256), current_doc.filename, current_doc.content_type,
    current_doc.storage_provider, current_doc.storage_status, current_doc.storage_region
  );
  UPDATE public.doka_documents
  SET object_key = chosen.object_key, filename = coalesce(chosen.filename, current_doc.filename),
      content_type = coalesce(chosen.content_type, current_doc.content_type),
      size_bytes = chosen.size_bytes, sha256 = pg_catalog.lower(chosen.sha256),
      storage_provider = chosen.storage_provider, storage_status = chosen.storage_status,
      storage_region = chosen.storage_region, updated_at = now()
  WHERE id = p_document_id AND owner_id = v_user RETURNING * INTO updated_doc;
  INSERT INTO public.doka_audit_events(owner_id, document_id, action, filename, metadata)
  VALUES (v_user, p_document_id, 'version_restore', updated_doc.filename,
    pg_catalog.jsonb_build_object('restored_version_id', p_version_id, 'version_no', next_no));
  RETURN NEXT updated_doc;
END;
$function$;

REVOKE ALL ON FUNCTION public.doka_bulk_update_documents(uuid[],text,text) FROM PUBLIC, anon, service_role;
REVOKE ALL ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) FROM PUBLIC, anon, service_role;
REVOKE ALL ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) FROM PUBLIC, anon, service_role;
REVOKE ALL ON FUNCTION public.doka_restore_document_version(uuid,uuid) FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION public.doka_bulk_update_documents(uuid[],text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_restore_document_version(uuid,uuid) TO authenticated;

COMMENT ON FUNCTION public.doka_bulk_update_documents(uuid[],text,text) IS
  'Owner-scoped bulk status/trash transaction. SECURITY INVOKER preserves RLS and column grants; explicit auth.uid() ownership checks and narrow EXECUTE ACLs apply.';
COMMENT ON FUNCTION public.doka_replace_document_version(uuid,text,text,text,bigint,text) IS
  'Owner-only atomic version replacement. Validates identity, ownership, SHA-256-bound object key, filename and MIME type before updating protected storage pointer columns.';
COMMENT ON FUNCTION public.doka_replace_document_version_storage(uuid,text,text,text,bigint,text,text,text) IS
  'Owner-only storage-aware version replacement. Validates identity, ownership, SHA-256-bound object key, filename, MIME type and provider before updating protected storage pointer columns.';
COMMENT ON FUNCTION public.doka_restore_document_version(uuid,uuid) IS
  'Owner-only atomic version restore. Validates identity, document/version ownership, SHA-256-bound object keys and metadata before updating protected storage pointer columns.';
