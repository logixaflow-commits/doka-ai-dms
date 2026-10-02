import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, ArrowDownToLine, CheckCircle2, CloudUpload, File,
  Files, FolderInput, HardDrive, Pencil, RefreshCw, RotateCcw,
  Search, ShieldCheck, Trash2, UploadCloud, X,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  getCloudDocumentDownloadUrl, listCloudDocuments, moveCloudDocument,
  renameCloudDocument, restoreCloudDocument, trashCloudDocument,
  updateCloudDocument, uploadCloudDocument, type CloudDocument,
} from '@/lib/cloudDocuments';

const MAX_FILE_BYTES = 50 * 1024 * 1024;

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
  const [showTrash, setShowTrash] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editFolder, setEditFolder] = useState('/');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const result = await listCloudDocuments({
        limit: 100, offset: 0, search: search.trim() || undefined,
        status: statusFilter === 'all' ? undefined : statusFilter as CloudDocument['status'],
        trash: showTrash,
      });
      setDocuments(result.documents || []);
      setHasMore((result.documents || []).length === 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cloud documents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, [showTrash]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalBytes = useMemo(() => documents.reduce((sum, item) => sum + item.size_bytes, 0), [documents]);
  const reviewCount = useMemo(() => documents.filter(item => item.status === 'review').length, [documents]);

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

  async function loadMore() {
    if (loading || busy || !hasMore) return;
    setBusy(true); setError('');
    try {
      const result = await listCloudDocuments({
        limit: 100, offset: documents.length, search: search.trim() || undefined,
        status: statusFilter === 'all' ? undefined : statusFilter as CloudDocument['status'],
        trash: showTrash,
      });
      setDocuments(current => [...current, ...(result.documents || [])]);
      setHasMore((result.documents || []).length === 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load more documents.');
    } finally { setBusy(false); }
  }

  async function upload() {
    if (!file) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await uploadCloudDocument(file);
      setDocuments(current => [result.document, ...current.filter(item => item.id !== result.document.id)]);
      setFile(null);
      const input = document.getElementById('doka-cloud-file') as HTMLInputElement | null;
      if (input) input.value = '';
      setMessage(`Uploaded “${result.document.filename}”. SHA-256 integrity fingerprint saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally { setBusy(false); }
  }

  async function download(item: CloudDocument) {
    setBusy(true); setError('');
    try {
      const result = await getCloudDocumentDownloadUrl(item.id);
      window.location.assign(result.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create a download link.');
      setBusy(false);
    }
  }

  async function changeStatus(item: CloudDocument, status: CloudDocument['status']) {
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await updateCloudDocument(item.id, { status });
      setDocuments(current => current.map(row => row.id === item.id ? result.document : row));
      setMessage(`Status updated for “${item.filename}”.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update document status.');
    } finally { setBusy(false); }
  }

  function beginEdit(item: CloudDocument) {
    setEditingId(item.id);
    setEditName(item.filename);
    setEditFolder(item.folder_path || '/');
    setError(''); setMessage('');
  }

  function cancelEdit() {
    setEditingId(null); setEditName(''); setEditFolder('/');
  }

  async function saveEdit(item: CloudDocument) {
    setBusy(true); setError(''); setMessage('');
    try {
      const [renamed, moved] = await Promise.all([
        editName.trim() !== item.filename ? renameCloudDocument(item.id, editName) : Promise.resolve({ document: item }),
        editFolder.trim() !== (item.folder_path || '/') ? moveCloudDocument(item.id, editFolder) : Promise.resolve({ document: item }),
      ]);
      const updated = moved.document.filename === item.filename && renamed.document.folder_path !== item.folder_path
        ? { ...moved.document, filename: renamed.document.filename }
        : renamed.document.folder_path === item.folder_path
          ? { ...renamed.document, folder_path: moved.document.folder_path }
          : moved.document;
      setDocuments(current => current.map(row => row.id === item.id ? updated : row));
      setMessage(`Saved “${updated.filename}”.`);
      cancelEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update document.');
    } finally { setBusy(false); }
  }

  async function trash(item: CloudDocument) {
    if (!window.confirm(`Move “${item.filename}” to Trash?`)) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await trashCloudDocument(item.id);
      setDocuments(current => current.filter(row => row.id !== item.id));
      setMessage(`Moved “${item.filename}” to Trash. You can restore it later.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to move document to Trash.');
    } finally { setBusy(false); }
  }

  async function restore(item: CloudDocument) {
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await restoreCloudDocument(item.id);
      setDocuments(current => current.filter(row => row.id !== item.id));
      setMessage(`Restored “${result.document.filename}”.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to restore document.');
    } finally { setBusy(false); }
  }

  const emptyTitle = showTrash ? 'Trash is empty' : documents.length === 0 ? 'No documents yet' : 'No matching documents';

  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary"><CloudUpload className="h-4 w-4" /> Private cloud library</div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">{showTrash ? 'Trash' : 'Your documents'}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{showTrash ? 'Deleted documents stay recoverable until you choose a permanent deletion policy.' : 'Upload, find, organize and manage files securely. Each document is private to your signed-in account.'}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant={showTrash ? 'default' : 'outline'} onClick={() => setShowTrash(value => !value)} disabled={busy} className="h-10 rounded-xl">
            {showTrash ? <Files className="mr-2 h-4 w-4" /> : <Trash2 className="mr-2 h-4 w-4" />}
            {showTrash ? 'Library' : 'Trash'}
          </Button>
          <Button variant="outline" onClick={() => void refresh()} disabled={loading || busy} className="h-10 rounded-xl">
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </section>

      {!showTrash && <section className="grid gap-4 sm:grid-cols-3">
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-blue-50 p-3 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><Files className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Total documents</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : documents.length}</p></div></CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-violet-50 p-3 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300"><HardDrive className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Storage used</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : formatSize(totalBytes)}</p></div></CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-amber-50 p-3 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"><ShieldCheck className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Marked for review</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : reviewCount}</p></div></CardContent></Card>
      </section>}

      {!showTrash && <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-3"><span className="rounded-2xl bg-primary/10 p-3 text-primary"><UploadCloud className="h-5 w-5" /></span><div><h2 className="font-semibold">Add files to your library</h2><p className="mt-1 text-sm text-muted-foreground">Maximum 50 MiB per file · Private storage · SHA-256 fingerprint</p></div></div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label htmlFor="doka-cloud-file" className="inline-flex h-10 cursor-pointer items-center justify-center rounded-xl border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-muted"><File className="mr-2 h-4 w-4" /> Choose file</label>
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
        <div className="flex flex-col gap-4 border-b border-border/70 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div><h2 className="font-semibold">{showTrash ? 'Deleted documents' : 'Document library'} <span className="ml-1 text-sm font-normal text-muted-foreground">({documents.length})</span></h2><p className="mt-1 text-xs text-muted-foreground">{showTrash ? 'Restore a document to return it to your library.' : 'Only documents belonging to your account are shown.'}</p></div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={search} onChange={event => setSearch(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void refresh(); }} placeholder="Search file names" className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 sm:w-56" /></div>
            <select aria-label="Filter by status" value={statusFilter} onChange={event => { setStatusFilter(event.target.value); void refresh(); }} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary sm:w-36"><option value="all">All statuses</option><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>
          </div>
        </div>
        <CardContent className="p-0">
          {loading ? <div className="space-y-3 p-6"><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /></div> :
            documents.length === 0 ? <div className="px-6 py-14 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground"><File className="h-7 w-7" /></span><h3 className="mt-4 font-semibold">{emptyTitle}</h3><p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{showTrash ? 'Documents you delete will appear here for recovery.' : 'Choose a file above to create your private cloud library.'}</p></div> :
              <div className="divide-y divide-border/70">{documents.map(item => <div key={item.id} className="flex flex-col gap-4 px-5 py-4 transition-colors hover:bg-muted/30 lg:flex-row lg:items-center lg:justify-between sm:px-6">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><File className="h-5 w-5" /></span>
                  <div className="min-w-0 flex-1">
                    {editingId === item.id ? (
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="text-xs text-muted-foreground">File name<input value={editName} onChange={event => setEditName(event.target.value)} className="mt-1 h-9 w-full rounded-lg border border-input bg-background px-3 text-sm" /></label>
                        <label className="text-xs text-muted-foreground">Folder path<input value={editFolder} onChange={event => setEditFolder(event.target.value)} placeholder="/" className="mt-1 h-9 w-full rounded-lg border border-input bg-background px-3 text-sm" /></label>
                        <div className="flex gap-2 sm:col-span-2"><Button size="sm" onClick={() => void saveEdit(item)} disabled={busy}><CheckCircle2 className="mr-1 h-4 w-4" />Save</Button><Button size="sm" variant="outline" onClick={cancelEdit} disabled={busy}><X className="mr-1 h-4 w-4" />Cancel</Button></div>
                      </div>
                    ) : (
                      <>
                        <div className="flex flex-wrap items-center gap-2"><p className="break-all text-sm font-medium">{item.filename}</p><Badge variant="outline" className="capitalize">{item.status}</Badge></div>
                        <p className="mt-1 text-xs text-muted-foreground">{item.folder_path || '/'} · {formatSize(item.size_bytes)} · {item.content_type} · {formatDate(item.created_at)}</p>
                        <p className="mt-1 break-all font-mono text-[10px] text-muted-foreground/80">SHA-256 · {item.sha256}</p>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 pl-[52px] lg:pl-0">
                  {showTrash ? (
                    <Button size="sm" variant="outline" onClick={() => void restore(item)} disabled={busy} className="h-9 rounded-lg"><RotateCcw className="mr-2 h-4 w-4" />Restore</Button>
                  ) : (
                    <>
                      <select aria-label={`Status for ${item.filename}`} className="h-9 min-w-28 rounded-lg border border-input bg-background px-2 text-xs" value={item.status} disabled={busy} onChange={event => void changeStatus(item, event.target.value as CloudDocument['status'])}><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>
                      <Button size="sm" variant="ghost" onClick={() => beginEdit(item)} disabled={busy} className="h-9 rounded-lg" aria-label={`Edit ${item.filename}`}><Pencil className="mr-1 h-4 w-4" />Edit</Button>
                      <Button size="sm" variant="ghost" onClick={() => void trash(item)} disabled={busy} className="h-9 rounded-lg text-rose-600 hover:text-rose-700" aria-label={`Trash ${item.filename}`}><Trash2 className="mr-1 h-4 w-4" />Trash</Button>
                      <Button size="sm" variant="outline" onClick={() => void download(item)} disabled={busy} className="h-9 rounded-lg"><ArrowDownToLine className="mr-2 h-4 w-4" />Download</Button>
                    </>
                  )}
                </div>
              </div>)}</div>
          }
          {!loading && hasMore && documents.length > 0 && (
            <div className="border-t border-border/70 px-5 py-4 text-center sm:px-6">
              <Button variant="outline" onClick={() => void loadMore()} disabled={busy} className="rounded-xl">Load more documents</Button>
            </div>
          )}
        </CardContent>
      </Card>
      <div className="flex items-start gap-2 text-xs leading-5 text-muted-foreground"><FolderInput className="mt-0.5 h-4 w-4 shrink-0" /><p>Folders are logical metadata paths; moving a document never changes its immutable object key or SHA-256 fingerprint.</p></div>
    </div>
  );
}
