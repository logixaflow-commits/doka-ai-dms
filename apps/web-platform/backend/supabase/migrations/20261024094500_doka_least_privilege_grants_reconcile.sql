-- Restore least-privilege Data API ACLs for Doka document tables.
-- RLS policies remain the row-level boundary; these grants are an independent
-- privilege boundary. The guarded SECURITY DEFINER RPCs are retained for the
-- validated storage-pointer/version operations and enforce auth.uid() ownership.
REVOKE ALL PRIVILEGES ON TABLE public.doka_documents FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON TABLE public.doka_document_versions FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON TABLE public.doka_audit_events FROM PUBLIC, anon, authenticated;

-- Authenticated clients may create/read documents, update only user-facing
-- status/metadata, and permanently delete only rows allowed by the RLS policy.
GRANT SELECT, INSERT, DELETE ON TABLE public.doka_documents TO authenticated;
GRANT UPDATE (status, metadata) ON TABLE public.doka_documents TO authenticated;

-- Version history and audit events are append-only for authenticated clients.
GRANT SELECT, INSERT ON TABLE public.doka_document_versions TO authenticated;
GRANT SELECT, INSERT ON TABLE public.doka_audit_events TO authenticated;

-- Do not grant anon direct table access. service_role retains its existing
-- privileged ACL and bypass-RLS behavior.
