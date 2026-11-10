-- Phase 1 remediation: make audit/version history server-controlled.
-- This migration is append-only and intentionally does not modify prior migrations.
-- Direct authenticated INSERT is removed; version changes remain in guarded,
-- atomic SECURITY DEFINER RPCs that validate auth.uid(), SHA-256 and object keys.

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
  IF p_owner_id IS NULL
     OR p_action IS NULL
     OR p_action NOT IN (
       'upload','download','update','trash','restore','permanent_delete',
       'preview','export','version_create','version_restore'
     )
     OR p_filename IS NOT NULL AND pg_catalog.length(p_filename) > 255
     OR p_metadata IS NULL
     OR pg_catalog.jsonb_typeof(p_metadata) <> 'object' THEN
    RAISE EXCEPTION 'Invalid audit event' USING errcode = '22023';
  END IF;

  IF p_document_id IS NOT NULL AND NOT EXISTS (
    SELECT 1
    FROM public.doka_documents
    WHERE id = p_document_id
      AND owner_id = p_owner_id
  ) THEN
    RAISE EXCEPTION 'Audit document ownership mismatch' USING errcode = '42501';
  END IF;

  INSERT INTO public.doka_audit_events(
    owner_id, document_id, action, filename, metadata
  ) VALUES (
    p_owner_id, p_document_id, p_action, p_filename, p_metadata
  );
END;
$function$;

REVOKE ALL ON FUNCTION public.doka_record_audit_event(uuid, text, uuid, text, jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.doka_record_audit_event(uuid, text, uuid, text, jsonb)
  TO service_role;

-- The version replacement/restore RPCs are single PostgreSQL transactions:
-- version INSERT + document UPDATE + audit INSERT commit or roll back together.
-- Keep only the guarded RPC execution surface for authenticated callers.
REVOKE ALL ON FUNCTION public.doka_replace_document_version(uuid, text, text, text, bigint, text)
  FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.doka_replace_document_version_storage(uuid, text, text, text, bigint, text, text, text)
  FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.doka_restore_document_version(uuid, uuid)
  FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version(uuid, text, text, text, bigint, text)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_replace_document_version_storage(uuid, text, text, text, bigint, text, text, text)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.doka_restore_document_version(uuid, uuid)
  TO authenticated;
