-- Keep privileged version RPCs out of the public/authenticated Data API surface.
-- The functions remain SECURITY DEFINER because they perform guarded atomic version
-- pointer changes; callers are limited to the server-side service role.
revoke all on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) from public, anon, authenticated;
revoke all on function public.doka_restore_document_version(uuid,uuid) from public, anon, authenticated;

grant execute on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) to service_role;
grant execute on function public.doka_restore_document_version(uuid,uuid) to service_role;

comment on function public.doka_replace_document_version(uuid,text,text,text,bigint,text) is
  'Server-side only atomic version replacement. SECURITY DEFINER is retained for the guarded version-pointer transaction; direct authenticated execution is revoked.';

comment on function public.doka_restore_document_version(uuid,uuid) is
  'Server-side only atomic version restore. SECURITY DEFINER is retained for the guarded version-pointer transaction; direct authenticated execution is revoked.';
