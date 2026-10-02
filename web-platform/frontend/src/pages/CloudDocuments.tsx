import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, ArrowDownToLine, CheckCircle2, CloudUpload, File, Files,
  HardDrive, Pencil, RefreshCw, Search, ShieldCheck, Trash2, Undo2, UploadCloud,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  getCloudDocumentDownloadUrl, listCloudDocuments, renameCloudDocument,
  moveCloudDocument, restoreCloudDocument, trashCloudDocument, updateCloudDocument,
  uploadCloudDocument, type CloudDocument,
} from '@/lib/cloudDocuments';

const MAX_FILE_BYTES = 50 * 1024 * 1024;
const PAGE_SIZE = 100;

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 ** 3)).toFixed(2)} GB`;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(date);
}

export default function CloudDocuments() {
  const [documents, setDocuments] = useState<CloudDocument[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [trashView, setTrashView] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await listCloudDocuments({
        limit: PAGE_SIZE, offset: 0, search, trash: trashView,
        ...(statusFilter === 'all' || trashView ? {} : { status: statusFilter as CloudDocument['status'] }),
      });
      const rows = result.documents || [];
      setDocuments(rows);
      setOffset(rows.length);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cloud documents.');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, trashView]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 250);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const totalBytes = useMemo(() => documents.reduce((sum, item) => sum + item.size_bytes, 0), [documents]);
  const reviewCount = useMemo(() => documents.filter(item => item.status === 'review').length, [documents]);

  async function loadMore() {
    setBusy(true);
    setError('');
    try {
      const result = await listCloudDocuments({
        limit: PAGE_SIZE, offset, search, trash: trashView,
        ...(statusFilter === 'all' || trashView ? {} : { status: statusFilter as CloudDocument['status'] }),
      });
      const rows = result.documents || [];
      setDocuments(current => [...current, ...rows]);
      setOffset(current => current + rows.length);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load more documents.');
    } finally {
      setBusy(false);
    }
  }

  function chooseFile(next: File | null) {
    setError('');
    setMessage('');
    if (next && next.size > MAX_FILE_BYTES) {
      setFile(null);
      setError('This file is larger than the 50 MiB upload limit.');
      return;
    }
    setFile(next);
  }

  async function upload() {
    if (!file) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await uploadCloudDocument(file);
      setFile(null);
      const input = document.getElementById('doka-cloud-file') as HTMLInputElement | null;
      if (input) input.value = '';
      setMessage(`Uploaded “${result.document.filename}”. SHA-256 integrity fingerprint saved.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setBusy(false);
    }
  }

  async function download(item: CloudDocument) {
    setBusy(true);
    setError('');
    try {
      const result = await getCloudDocumentDownloadUrl(item.id);
      window.location.assign(result.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create a download link.');
      setBusy(false);
    }
  }

  async function changeStatus(item: CloudDocument, status: CloudDocument['status']) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await updateCloudDocument(item.id, { status });
      setDocuments(current => current.map(row => row.id === item.id ? result.document : row));
      setMessage(`Status updated for “${item.filename}”.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update document status.');
    } finally {
      setBusy(false);
    }
  }

  async function rename(item: CloudDocument) {
    const next = window.prompt('Enter a new document name', item.filename);
    if (next === null || next.trim() === item.filename) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await renameCloudDocument(item.id, next);
      setDocuments(current => current.map(row => row.id === item.id ? result.document : row));
      setMessage('Document name updated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to rename document.');
    } finally {
      setBusy(false);
    }
  }

  async function moveToFolder(item: CloudDocument) {
    const next = window.prompt('Enter a folder path (for example /Finance/Invoices)', item.folder_path || '/');
    if (next === null) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await moveCloudDocument(item.id, next);
      setDocuments(current => current.map(row => row.id === item.id ? result.document : row));
      setMessage(`Moved “${item.filename}” to ${result.document.folder_path}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to move document.');
    } finally {
      setBusy(false);
    }
  }

  async function moveToTrash(item: CloudDocument) {
    if (!window.confirm(`Move “${item.filename}” to Trash? You can restore it later.`)) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await trashCloudDocument(item.id);
      setDocuments(current => current.filter(row => row.id !== item.id));
      setMessage('Document moved to Trash. The stored file has not been permanently deleted.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to move document to Trash.');
    } finally {
      setBusy(false);
    }
  }

  async function restore(item: CloudDocument) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await restoreCloudDocument(item.id);
      setDocuments(current => current.filter(row => row.id !== item.id));
      setMessage('Document restored to your library.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to restore document.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary"><CloudUpload className="h-4 w-4" /> Private cloud library</div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Your documents</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Upload, search and manage files securely. Each document is stored privately and linked to your signed-in account.</p>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading || busy} className="h-10 shrink-0 rounded-xl">
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh library
        </Button>
      </section>

      {!trashView && <section className="grid gap-4 sm:grid-cols-3">
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-blue-50 p-3 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><Files className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Loaded documents</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : documents.length}{hasMore ? '+' : ''}</p></div></CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-violet-50 p-3 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300"><HardDrive className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Storage in loaded results</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : formatSize(totalBytes)}</p></div></CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-amber-50 p-3 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"><ShieldCheck className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Marked for review</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : reviewCount}</p></div></CardContent></Card>
      </section>}

      {!trashView && <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-start gap-3"><span className="rounded-2xl bg-primary/10 p-3 text-primary"><UploadCloud className="h-5 w-5" /></span><div><h2 className="font-semibold">Add files to your library</h2><p className="mt-1 text-sm text-muted-foreground">Maximum 50 MiB per file · Private storage · SHA-256 fingerprint</p></div></div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label htmlFor="doka-cloud-file" className="inline-flex h-10 cursor-pointer items-center justify-center rounded-xl border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-muted">
                <File className="mr-2 h-4 w-4" /> Choose file
              </label>
              <input id="doka-cloud-file" type="file" className="sr-only" onChange={event => chooseFile(event.target.files?.[0] || null)} disabled={busy} />
              <Button onClick={() => void upload()} disabled={!file || busy} className="h-10 rounded-xl px-5"><CloudUpload className="mr-2 h-4 w-4" />{busy ? 'Working…' : 'Upload securely'}</Button>
            </div>
          </div>
          {file && <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/20 bg-primary/[0.04] px-4 py-3"><div className="flex min-w-0 items-center gap-3"><File className="h-4 w-4 shrink-0 text-primary" /><div className="min-w-0"><p className="truncate text-sm font-medium">{file.name}</p><p className="text-xs text-muted-foreground">{formatSize(file.size)} · {file.type || 'Unknown file type'}</p></div></div><button className="text-xs font-medium text-muted-foreground hover:text-foreground" onClick={() => chooseFile(null)}>Remove</button></div>}
        </CardContent>
      </Card>}

      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      {message && <div role="status" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />{message}</div>}

      <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <div className="flex flex-col gap-4 border-b border-border/70 p-5 sm:px-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div><h2 className="font-semibold">{trashView ? 'Trash' : 'Document library'} <span className="ml-1 text-sm font-normal text-muted-foreground">({documents.length}{hasMore ? '+' : ''})</span></h2><p className="mt-1 text-xs text-muted-foreground">{trashView ? 'Trashed files remain stored privately until permanently deleted.' : 'Only documents belonging to your account are shown.'}</p></div>
            <div className="inline-flex w-fit rounded-xl border border-border bg-muted/50 p-1">
              <button type="button" onClick={() => setTrashView(false)} aria-pressed={!trashView} className={`rounded-lg px-3 py-2 text-xs font-medium transition ${!trashView ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>Library</button>
              <button type="button" onClick={() => setTrashView(true)} aria-pressed={trashView} className={`rounded-lg px-3 py-2 text-xs font-medium transition ${trashView ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>Trash</button>
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative min-w-0 flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input aria-label="Search documents by file name" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search file names…" className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" /></div>
            {!trashView && <select aria-label="Filter by status" value={statusFilter} onChange={event => setStatusFilter(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary sm:w-40"><option value="all">All statuses</option><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>}
          </div>
        </div>
        <CardContent className="p-0">
          {loading ? <div className="space-y-3 p-6"><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /></div> :
            documents.length === 0 ? <div className="px-6 py-14 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground"><File className="h-7 w-7" /></span><h3 className="mt-4 font-semibold">{trashView ? 'Trash is empty' : 'No documents found'}</h3><p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{trashView ? 'Documents you move to Trash will appear here.' : 'Choose a file above or change your search and filters.'}</p></div> :
              <div className="divide-y divide-border/70">{documents.map(item => <div key={item.id} className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div className="flex min-w-0 items-start gap-3"><span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><File className="h-5 w-5" /></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="break-all text-sm font-medium">{item.filename}</p><Badge variant="outline" className="capitalize">{item.status}</Badge></div><p className="mt-1 text-xs text-muted-foreground">{formatSize(item.size_bytes)} · {item.content_type} · {formatDate(item.created_at)}</p><p className="mt-1 text-xs text-muted-foreground">Folder: <span className="font-mono">{item.folder_path || '/'}</span></p><p className="mt-1 break-all font-mono text-[10px] text-muted-foreground/80">SHA-256 · {item.sha256}</p></div></div>
                <div className="flex flex-wrap items-center gap-2 pl-[52px] sm:justify-end sm:pl-0">
                  {!trashView && <><select aria-label={`Status for ${item.filename}`} className="h-9 min-w-28 rounded-lg border border-input bg-background px-2 text-xs" value={item.status} disabled={busy} onChange={event => void changeStatus(item, event.target.value as CloudDocument['status'])}><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select><Button size="sm" variant="ghost" onClick={() => void rename(item)} disabled={busy} className="h-9 rounded-lg" aria-label={`Rename ${item.filename}`}><Pencil className="h-4 w-4" /><span className="ml-1 hidden md:inline">Rename</span></Button><Button size="sm" variant="ghost" onClick={() => void moveToFolder(item)} disabled={busy} className="h-9 rounded-lg">Move</Button><Button size="sm" variant="outline" onClick={() => void download(item)} disabled={busy} className="h-9 rounded-lg"><ArrowDownToLine className="mr-2 h-4 w-4" />Download</Button><Button size="icon" variant="ghost" onClick={() => void moveToTrash(item)} disabled={busy} className="h-9 w-9 rounded-lg text-rose-600 hover:bg-rose-50 hover:text-rose-700" aria-label={`Move ${item.filename} to Trash`}><Trash2 className="h-4 w-4" /></Button></>}
                  {trashView && <Button size="sm" variant="outline" onClick={() => void restore(item)} disabled={busy} className="h-9 rounded-lg"><Undo2 className="mr-2 h-4 w-4" />Restore</Button>}
                </div>
              </div>)}</div>
          }
          {hasMore && !loading && <div className="flex justify-center border-t border-border/70 p-4"><Button variant="outline" onClick={() => void loadMore()} disabled={busy} className="rounded-xl">{busy ? 'Loading…' : 'Load more documents'}</Button></div>}
        </CardContent>
      </Card>
      <p className="text-xs leading-5 text-muted-foreground">Cloud documents are stored in Supabase Storage and indexed in your private account-scoped library. Moving a file to Trash hides it from the active library without deleting the stored object. Local OCR and folder-processing tools are not part of this cloud page.</p>
    </div>
  );
}
