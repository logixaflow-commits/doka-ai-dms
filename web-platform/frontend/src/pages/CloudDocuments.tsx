import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, ArrowDownToLine, CheckCircle2, CloudUpload, File,
  Files, HardDrive, RefreshCw, Search, ShieldCheck, UploadCloud,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  getCloudDocumentDownloadUrl, listCloudDocuments, updateCloudDocument,
  uploadCloudDocument, type CloudDocument,
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
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const result = await listCloudDocuments(100, 0);
      setDocuments(result.documents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cloud documents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  const visibleDocuments = useMemo(() => documents.filter(item => {
    const matchesSearch = !search.trim() || `${item.filename} ${item.content_type}`.toLowerCase().includes(search.trim().toLowerCase());
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  }), [documents, search, statusFilter]);

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

  async function upload() {
    if (!file) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await uploadCloudDocument(file);
      setDocuments(current => [result.document, ...current.filter(item => item.id !== result.document.id)]);
      setFile(null);
      const input = document.getElementById('doka-cloud-file') as HTMLInputElement | null;
      if (input) input.value = '';
      setMessage(`Uploaded “${result.document.filename}”. SHA-256 integrity fingerprint saved.`);
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

  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary"><CloudUpload className="h-4 w-4" /> Private cloud library</div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Your documents</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Upload, find and manage files securely. Each document is stored privately and linked to your signed-in account.</p>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading || busy} className="h-10 rounded-xl">
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh library
        </Button>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-blue-50 p-3 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><Files className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Total documents</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : documents.length}</p></div></CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-violet-50 p-3 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300"><HardDrive className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Storage used</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : formatSize(totalBytes)}</p></div></CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-center gap-4 p-5"><span className="rounded-2xl bg-amber-50 p-3 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"><ShieldCheck className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">Marked for review</p><p className="mt-1 text-2xl font-semibold">{loading ? '—' : reviewCount}</p></div></CardContent></Card>
      </section>

      <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-3"><span className="rounded-2xl bg-primary/10 p-3 text-primary"><UploadCloud className="h-5 w-5" /></span><div><h2 className="font-semibold">Add files to your library</h2><p className="mt-1 text-sm text-muted-foreground">Maximum 50 MiB per file · Private storage · SHA-256 fingerprint</p></div></div>
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
      </Card>

      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      {message && <div role="status" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />{message}</div>}

      <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <div className="flex flex-col gap-4 border-b border-border/70 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div><h2 className="font-semibold">Document library <span className="ml-1 text-sm font-normal text-muted-foreground">({visibleDocuments.length})</span></h2><p className="mt-1 text-xs text-muted-foreground">Only documents belonging to your account are shown.</p></div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search documents…" className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15 sm:w-56" /></div>
            <select aria-label="Filter by status" value={statusFilter} onChange={event => setStatusFilter(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary sm:w-36"><option value="all">All statuses</option><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select>
          </div>
        </div>
        <CardContent className="p-0">
          {loading ? <div className="space-y-3 p-6"><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted" /></div> :
            visibleDocuments.length === 0 ? <div className="px-6 py-14 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-muted-foreground"><File className="h-7 w-7" /></span><h3 className="mt-4 font-semibold">{documents.length === 0 ? 'No documents yet' : 'No matching documents'}</h3><p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{documents.length === 0 ? 'Choose a file above to create your private cloud library.' : 'Try another search term or change the status filter.'}</p></div> :
              <div className="divide-y divide-border/70">{visibleDocuments.map(item => <div key={item.id} className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div className="flex min-w-0 items-start gap-3"><span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><File className="h-5 w-5" /></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="break-all text-sm font-medium">{item.filename}</p><Badge variant="outline" className="capitalize">{item.status}</Badge></div><p className="mt-1 text-xs text-muted-foreground">{formatSize(item.size_bytes)} · {item.content_type} · {formatDate(item.created_at)}</p><p className="mt-1 break-all font-mono text-[10px] text-muted-foreground/80">SHA-256 · {item.sha256}</p></div></div>
                <div className="flex shrink-0 items-center gap-2 pl-[52px] sm:pl-0"><select aria-label={`Status for ${item.filename}`} className="h-9 min-w-28 rounded-lg border border-input bg-background px-2 text-xs" value={item.status} disabled={busy} onChange={event => void changeStatus(item, event.target.value as CloudDocument['status'])}><option value="active">Active</option><option value="review">Review</option><option value="quarantined">Quarantined</option><option value="archived">Archived</option></select><Button size="sm" variant="outline" onClick={() => void download(item)} disabled={busy} className="h-9 rounded-lg"><ArrowDownToLine className="mr-2 h-4 w-4" />Download</Button></div>
              </div>)}</div>
          }
        </CardContent>
      </Card>
      <p className="text-xs leading-5 text-muted-foreground">Cloud documents are stored in Supabase Storage and indexed in your private account-scoped library. Local OCR and folder-processing tools are not part of this cloud page.</p>
    </div>
  );
}
