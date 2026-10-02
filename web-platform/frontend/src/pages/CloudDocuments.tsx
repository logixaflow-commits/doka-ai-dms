import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, ArrowDownToLine, CheckCircle2, CloudUpload, Eye, File, History,
  Files, FolderInput, HardDrive, Pencil, RefreshCw, RotateCcw,
  Search, ShieldCheck, Trash2, UploadCloud, X,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  bulkUpdateCloudDocuments, createCloudDocumentVersion, getCloudDocumentDownloadUrl, getCloudDocumentPreviewUrl, listCloudDocumentVersions, listCloudDocuments, listCloudFolders, permanentlyDeleteCloudDocument,
  restoreCloudDocument, restoreCloudDocumentVersion, trashCloudDocument,
  updateCloudDocument, uploadCloudDocument, type CloudDocument, type CloudDocumentVersion,
} from '@/lib/cloudDocuments';

const MAX_FILE_BYTES = 50 * 1024 * 1024;
type BatchUploadItem = { id: string; file: File; status: 'queued' | 'uploading' | 'complete' | 'failed'; error?: string };

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
  const [batchQueue, setBatchQueue] = useState<BatchUploadItem[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [folderFilter, setFolderFilter] = useState('all');
  const [folderPaths, setFolderPaths] = useState<string[]>(['/']);
  const [showTrash, setShowTrash] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editFolder, setEditFolder] = useState('/');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkStatus, setBulkStatus] = useState<CloudDocument['status']>('active');
  const [versionsDocument, setVersionsDocument] = useState<CloudDocument | null>(null);
  const [versions, setVersions] = useState<CloudDocumentVersion[]>([]);
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const [result, folderResult] = await Promise.all([
        listCloudDocuments({
          limit: 100, offset: 0, search: search.trim() || undefined,
          status: statusFilter === 'all' ? undefined : statusFilter as CloudDocument['status'],
          trash: showTrash, folderPath: folderFilter === 'all' || showTrash ? undefined : folderFilter,
        }),
        listCloudFolders().catch(() => ({ folders: ['/'] })),
      ]);
      setDocuments(result.documents || []);
      setFolderPaths(folderResult.folders || ['/']);
      setSelectedIds([]);
      setHasMore((result.documents || []).length === 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cloud documents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, [showTrash, folderFilter, statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

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
        trash: showTrash, folderPath: folderFilter === 'all' || showTrash ? undefined : folderFilter,
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

  function queueBatchFiles(files: FileList | null) {
    if (!files?.length) return;
    const incoming = Array.from(files);
    const accepted = incoming.filter(item => item.size <= MAX_FILE_BYTES);
    if (accepted.length !== incoming.length) setError('Files over 50 MiB were skipped from the batch queue.');
    setBatchQueue(current => [
      ...current,
      ...accepted.map((item, index) => ({
        id: `${item.name}:${item.lastModified}:${item.size}:${current.length + index}`,
        file: item,
        status: 'queued' as const,
      })),
    ]);
  }

  async function processBatch(ids?: string[]) {
    if (busy) return;
    const selected = batchQueue.filter(item => ids ? ids.includes(item.id) : item.status === 'queued' || item.status === 'failed');
    if (!selected.length) return;
    setBusy(true); setError(''); setMessage('');
    let uploaded = 0;
    for (const item of selected) {
      setBatchQueue(current => current.map(row => row.id === item.id ? { ...row, status: 'uploading', error: undefined } : row));
      try {
        const result = await uploadCloudDocument(item.file);
        setDocuments(current => [result.document, ...current.filter(row => row.id !== result.document.id)]);
        setBatchQueue(current => current.map(row => row.id === item.id ? { ...row, status: 'complete', error: undefined } : row));
        uploaded += 1;
      } catch (err) {
        setBatchQueue(current => current.map(row => row.id === item.id ? { ...row, status: 'failed', error: err instanceof Error ? err.message : 'Upload failed.' } : row));
      }
    }
    setMessage(`Batch finished: ${uploaded} uploaded, ${selected.length - uploaded} failed.`);
    setBusy(false);
  }

  function retryFailedBatch() {
    const failed = batchQueue.filter(item => item.status === 'failed').map(item => item.id);
    if (failed.length) void processBatch(failed);
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

  async function preview(item: CloudDocument) {
    const previewWindow = window.open('about:blank', '_blank');
    if (!previewWindow) {
      setError('Allow pop-ups for Doka to open the document preview.');
      return;
    }
    previewWindow.opener = null;
    setBusy(true); setError('');
    try {
      const result = await getCloudDocumentPreviewUrl(item.id);
      previewWindow.location.href = result.url;
    } catch (err) {
      previewWindow.close();
      setError(err instanceof Error ? err.message : 'Unable to create a preview link.');
    } finally { setBusy(false); }
  }

  async function openVersions(item: CloudDocument) {
    setVersionsDocument(item);
    setVersions([]);
    setVersionFile(null);
    setVersionsLoading(true);
    setError('');
    try {
      const result = await listCloudDocumentVersions(item.id);
      setVersions(result.versions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load version history.');
    } finally { setVersionsLoading(false); }
  }

  async function saveVersion() {
    if (!versionsDocument || !versionFile) return;
    if (versionFile.size > MAX_FILE_BYTES) {
      setError('This version exceeds the 50 MiB upload limit.');
      return;
    }
    if (!window.confirm(`Upload a new version of “${versionsDocument.filename}”? The current version will be preserved in history.`)) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await createCloudDocumentVersion(versionsDocument.id, versionFile);
      setDocuments(current => current.map(item => item.id === result.document.id ? result.document : item));
      setVersionsDocument(result.document);
      setVersionFile(null);
      const history = await listCloudDocumentVersions(result.document.id);
      setVersions(history.versions || []);
      setMessage(`A new version of “${result.document.filename}” was saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save document version.');
    } finally { setBusy(false); }
  }

  async function restoreVersion(version: CloudDocumentVersion) {
    if (!versionsDocument || !window.confirm(`Restore version ${version.version_no}? The current version will be preserved in history.`)) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await restoreCloudDocumentVersion(versionsDocument.id, version.id);
      setDocuments(current => current.map(item => item.id === result.document.id ? result.document : item));
      setVersionsDocument(result.document);
      const history = await listCloudDocumentVersions(result.document.id);
      setVersions(history.versions || []);
      setMessage(`Version ${version.version_no} restored.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to restore this version.');
    } finally { setBusy(false); }
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
      const nextName = editName.trim();
      const nextFolder = editFolder.trim() || '/';
      if (!nextName || nextName.length > 255 || nextName.includes('/') || nextName.includes('\\\\') || nextName.includes('\\0')) {
        throw new Error('Enter a valid file name (maximum 255 characters).');
      }
      if (!nextFolder || nextFolder.includes('\\\\') || nextFolder.includes('\\0')) {
        throw new Error('Enter a valid folder path.');
      }
      // Apply both metadata fields in one PATCH to avoid racing two updates
      // against the same row and accidentally overwriting one another.
      const result = await updateCloudDocument(item.id, {
        ...(nextName !== item.filename ? { filename: nextName } : {}),
        ...(nextFolder !== (item.folder_path || '/') ? { folder_path: nextFolder } : {}),
      });
      const updated = result.document;
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

  async function permanentlyDelete(item: CloudDocument) {
    if (!window.confirm(`Permanently remove “${item.filename}” and its stored versions? This cannot be undone.`)) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await permanentlyDeleteCloudDocument(item.id);
      setDocuments(current => current.filter(row => row.id !== item.id));
      setMessage(`Removed “${item.filename}” and ${result.objects_deleted} stored object(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to permanently remove document.');
    } finally { setBusy(false); }
  }

  function toggleSelected(id: string, checked: boolean) {
    setSelectedIds(current => checked ? [...new Set([...current, id])] : current.filter(value => value !== id));
  }

  async function applyBulkStatus() {
    if (!selectedIds.length) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await bulkUpdateCloudDocuments(selectedIds, 'status', bulkStatus);
      const byId = new Map(result.documents.map(document => [document.id, document]));
      setDocuments(current => current.map(item => byId.get(item.id) || item));
      setMessage(`Updated status for ${result.updated_count} document(s) atomically.`);
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk status update failed. Refresh the library before retrying.');
      await refresh();
    } finally { setBusy(false); }
  }

  async function bulkTrash() {
    if (!selectedIds.length || !window.confirm(`Move ${selectedIds.length} selected document(s) to Trash?`)) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await bulkUpdateCloudDocuments(selectedIds, 'trash');
      const removedIds = new Set(result.documents.map(document => document.id));
      setDocuments(current => current.filter(item => !removedIds.has(item.id)));
      setMessage(`Moved ${result.updated_count} document(s) to Trash atomically.`);
      setSelectedIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk Trash failed. Refresh the library before retrying.');
      await refresh();
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

      {!showTrash && (
        <Card className="rounded-2xl border-border/70 shadow-sm">
          <CardContent className="space-y-4 p-5 sm:p-6">
            <div><h2 className="font-semibold">Batch upload queue</h2><p className="mt-1 text-xs text-muted-foreground">Add multiple files, upload them sequentially and retry any failed item. Each file is limited to 50 MiB.</p></div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <input aria-label="Choose multiple files for batch upload" type="file" multiple onChange={event => { queueBatchFiles(event.target.files); event.target.value = ''; }} disabled={busy} className="min-w-0 flex-1 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-muted file:px-3 file:py-2 file:text-xs" />
              <Button onClick={() => void processBatch()} disabled={busy || !batchQueue.some(item => item.status === 'queued' || item.status === 'failed')}>Upload queue</Button>
              <Button variant="outline" onClick={retryFailedBatch} disabled={busy || !batchQueue.some(item => item.status === 'failed')}>Retry failed</Button>
            </div>
            {batchQueue.length > 0 && <div className="divide-y divide-border/70 rounded-xl border border-border/70">
              {batchQueue.map(item => <div key={item.id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0"><p className="break-all text-sm font-medium">{item.file.name}</p><p className="text-xs text-muted-foreground">{formatSize(item.file.size)} · {item.error || item.status}</p></div>
                <Badge variant={item.status === 'complete' ? 'default' : item.status === 'failed' ? 'destructive' : 'outline'} className="capitalize">{item.status}</Badge>
              </div>)}
              <div className="flex justify-end p-3"><Button size="sm" variant="ghost" onClick={() => setBatchQueue(current => current.filter(item => item.status !== 'complete'))} disabled={busy}>Clear completed</Button></div>
            </div>}
          </CardContent>
        </Card>
      )}

      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      {message && <div role="status" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />{message}</div>}

      <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <div className="flex flex-col gap-4 border-b border-border/70 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            {!showTrash && documents.length > 0 && <input type="checkbox" aria-label="Select all visible documents" checked={documents.length > 0 && documents.every(item => selectedIds.includes(item.id))} onChange={event => setSelectedIds(event.target.checked ? documents.map(item => item.id) : [])} disabled={busy} className="h-4 w-4 accent-primary" />}
            <div><h2 className="font-semibold">{showTrash ? 'Deleted documents' : 'Document library'} <span className="ml-1 text-sm font-normal text-muted-foreground">({documents.length})</span></h2><p className="mt-1 text-xs text-muted-foreground">{showTrash ? 'Restore a document to return it to your library.' : 'Only documents belonging to your account are shown.'}</p></div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={search} onChange={event => setSearch(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void refresh(); }} placeholder="Search file names" className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 sm:w-56" /></div>
            <select aria-label="Filter by status" value={statusFilter} onChange={event => setStatusFilter(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary sm:w-36"><option value="all">All statuses</option><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>
            {!showTrash && <select aria-label="Filter by folder" value={folderFilter} onChange={event => setFolderFilter(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary sm:w-40"><option value="all">All folders</option>{folderPaths.map(folder => <option key={folder} value={folder}>{folder === '/' ? 'Root folder' : folder}</option>)}</select>}
          </div>
        </div>
        {selectedIds.length > 0 && !showTrash && (
          <div className="flex flex-col gap-3 border-b border-border/70 bg-primary/[0.04] px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p className="text-sm font-medium">{selectedIds.length} document(s) selected</p>
            <div className="flex flex-wrap items-center gap-2">
              <select aria-label="Bulk status" value={bulkStatus} onChange={event => setBulkStatus(event.target.value as CloudDocument['status'])} className="h-9 rounded-lg border border-input bg-background px-2 text-xs"><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>
              <Button size="sm" variant="outline" onClick={() => void applyBulkStatus()} disabled={busy}>Apply status</Button>
              <Button size="sm" variant="outline" onClick={() => void bulkTrash()} disabled={busy} className="text-rose-600">Move to Trash</Button>
              <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])} disabled={busy}>Clear</Button>
            </div>
          </div>
        )}
        <CardContent className="p-0">
          {loading ? <div className="space-y-3 p-6"><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /></div> :
            documents.length === 0 ? <div className="px-6 py-14 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground"><File className="h-7 w-7" /></span><h3 className="mt-4 font-semibold">{emptyTitle}</h3><p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{showTrash ? 'Documents you delete will appear here for recovery.' : 'Choose a file above to create your private cloud library.'}</p></div> :
              <div className="divide-y divide-border/70">{documents.map(item => <div key={item.id} className="flex flex-col gap-4 px-5 py-4 transition-colors hover:bg-muted/30 lg:flex-row lg:items-center lg:justify-between sm:px-6">
                <div className="flex min-w-0 items-start gap-3">
                  {!showTrash && <input type="checkbox" aria-label={`Select ${item.filename}`} checked={selectedIds.includes(item.id)} onChange={event => toggleSelected(item.id, event.target.checked)} disabled={busy} className="mt-3 h-4 w-4 shrink-0 accent-primary" />}
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
                    <>
                      <Button size="sm" variant="outline" onClick={() => void restore(item)} disabled={busy} className="h-9 rounded-lg"><RotateCcw className="mr-2 h-4 w-4" />Restore</Button>
                      <Button size="sm" variant="destructive" onClick={() => void permanentlyDelete(item)} disabled={busy} className="h-9 rounded-lg"><Trash2 className="mr-2 h-4 w-4" />Delete forever</Button>
                    </>
                  ) : (
                    <>
                      <select aria-label={`Status for ${item.filename}`} className="h-9 min-w-28 rounded-lg border border-input bg-background px-2 text-xs" value={item.status} disabled={busy} onChange={event => void changeStatus(item, event.target.value as CloudDocument['status'])}><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>
                      <Button size="sm" variant="outline" onClick={() => void openVersions(item)} disabled={busy} className="h-9 rounded-lg"><History className="mr-1 h-4 w-4" />Versions</Button>
                      <Button size="sm" variant="ghost" onClick={() => beginEdit(item)} disabled={busy} className="h-9 rounded-lg" aria-label={`Edit ${item.filename}`}><Pencil className="mr-1 h-4 w-4" />Edit</Button>
                      <Button size="sm" variant="ghost" onClick={() => void trash(item)} disabled={busy} className="h-9 rounded-lg text-rose-600 hover:text-rose-700" aria-label={`Trash ${item.filename}`}><Trash2 className="mr-1 h-4 w-4" />Trash</Button>
                      {['application/pdf', 'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'text/plain', 'text/csv'].includes((item.content_type || '').split(';')[0].trim().toLowerCase()) && <Button size="sm" variant="outline" onClick={() => void preview(item)} disabled={busy} className="h-9 rounded-lg"><Eye className="mr-2 h-4 w-4" />Preview</Button>}
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
      {versionsDocument && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="doka-version-dialog-title">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border bg-background p-5 shadow-2xl sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div><h2 id="doka-version-dialog-title" className="text-lg font-semibold">Version history</h2><p className="mt-1 break-all text-sm text-muted-foreground">{versionsDocument.filename}</p></div>
              <Button size="icon" variant="ghost" onClick={() => { setVersionsDocument(null); setVersions([]); setVersionFile(null); }} aria-label="Close version history"><X className="h-4 w-4" /></Button>
            </div>
            <div className="mt-5 rounded-xl border border-border/70 p-4">
              <p className="text-sm font-medium">Upload a new version</p>
              <p className="mt-1 text-xs text-muted-foreground">The current file is retained as a previous version. Maximum size: 50 MiB.</p>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <input type="file" onChange={event => setVersionFile(event.target.files?.[0] || null)} disabled={busy} className="min-w-0 flex-1 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-muted file:px-3 file:py-2 file:text-xs" />
                <Button onClick={() => void saveVersion()} disabled={busy || !versionFile}>Save new version</Button>
              </div>
            </div>
            <div className="mt-5">
              <h3 className="text-sm font-semibold">Previous versions</h3>
              {versionsLoading ? <p className="py-6 text-center text-sm text-muted-foreground">Loading history…</p> :
                versions.length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">No previous versions yet.</p> :
                <div className="mt-2 divide-y divide-border/70 rounded-xl border border-border/70">
                  {versions.map(version => <div key={version.id} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0"><p className="text-sm font-medium">Version {version.version_no} · {version.filename || versionsDocument.filename}</p><p className="mt-1 text-xs text-muted-foreground">{formatSize(version.size_bytes)} · {formatDate(version.created_at)} · SHA-256 {version.sha256.slice(0, 12)}…</p></div>
                    <Button size="sm" variant="outline" onClick={() => void restoreVersion(version)} disabled={busy}>Restore this version</Button>
                  </div>)}
                </div>
              }
            </div>
          </div>
        </div>
      )}
      <div className="flex items-start gap-2 text-xs leading-5 text-muted-foreground"><FolderInput className="mt-0.5 h-4 w-4 shrink-0" /><p>Folders are logical metadata paths; moving a document never changes its immutable object key or SHA-256 fingerprint.</p></div>
    </div>
  );
}
