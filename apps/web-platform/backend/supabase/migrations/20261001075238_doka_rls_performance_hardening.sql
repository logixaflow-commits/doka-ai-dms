-- Avoid per-row auth function evaluation in RLS and pin trigger function search_path.
alter function public.doka_set_updated_at() set search_path = public, pg_temp;

drop policy if exists "doka_documents_owner_select" on public.doka_documents;
create policy "doka_documents_owner_select"
  on public.doka_documents for select
  to authenticated
  using ((select auth.uid()) = owner_id);

drop policy if exists "doka_documents_owner_insert" on public.doka_documents;
create policy "doka_documents_owner_insert"
  on public.doka_documents for insert
  to authenticated
  with check ((select auth.uid()) = owner_id);

drop policy if exists "doka_documents_owner_update" on public.doka_documents;
create policy "doka_documents_owner_update"
  on public.doka_documents for update
  to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

drop policy if exists "doka_documents_owner_delete" on public.doka_documents;
create policy "doka_documents_owner_delete"
  on public.doka_documents for delete
  to authenticated
  using ((select auth.uid()) = owner_id);

drop policy if exists "doka_versions_owner_select" on public.doka_document_versions;
create policy "doka_versions_owner_select"
  on public.doka_document_versions for select
  to authenticated
  using (
    exists (
      select 1 from public.doka_documents d
      where d.id = document_id and d.owner_id = (select auth.uid())
    )
  );

drop policy if exists "doka_versions_owner_insert" on public.doka_document_versions;
create policy "doka_versions_owner_insert"
  on public.doka_document_versions for insert
  to authenticated
  with check (
    exists (
      select 1 from public.doka_documents d
      where d.id = document_id and d.owner_id = (select auth.uid())
    )
  );
