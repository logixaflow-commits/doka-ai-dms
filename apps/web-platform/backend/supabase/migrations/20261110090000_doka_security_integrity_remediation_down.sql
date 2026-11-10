-- Manual rollback companion for 20261110090000_doka_security_integrity_remediation.sql.
-- Run only after approval; this restores the previous direct client INSERT model.

REVOKE EXECUTE ON FUNCTION public.doka_record_audit_event(uuid, text, uuid, text, jsonb)
  FROM service_role;
DROP FUNCTION IF EXISTS public.doka_record_audit_event(uuid, text, uuid, text, jsonb);

GRANT INSERT ON TABLE public.doka_audit_events TO authenticated;
GRANT INSERT ON TABLE public.doka_document_versions TO authenticated;

CREATE POLICY doka_audit_owner_insert
  ON public.doka_audit_events FOR INSERT TO authenticated
  WITH CHECK ((select auth.uid()) = owner_id);

-- Restore only the historical version INSERT policy if the target environment
-- previously used one; owner validation is document-scoped.
CREATE POLICY doka_versions_owner_insert
  ON public.doka_document_versions FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.doka_documents d
      WHERE d.id = document_id AND d.owner_id = (select auth.uid())
    )
  );
