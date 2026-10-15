-- Align database folder path validation with the API's segment-based normalization.
alter table public.doka_documents
  drop constraint if exists doka_documents_folder_path_check;

alter table public.doka_documents
  add constraint doka_documents_folder_path_check
  check (
    folder_path = '/'
    or (
      folder_path ~ '^/[^/]+(/[^/]+)*$'
      and folder_path !~ '(^|/)\.\.(/|$)'
      and folder_path !~ '(^|/)\.(/|$)'
      and strpos(folder_path, chr(92)) = 0
    )
  );
