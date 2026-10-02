import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Activity, ArrowDownToLine, ArrowRight, Cloud, CloudUpload, FileCheck2,
  FileText, HardDrive, RefreshCw, ShieldCheck, Sparkles,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { getCloudDocumentDownloadUrl, listCloudDocuments, type CloudDocument } from '@/lib/cloudDocuments';

const API_ORIGIN = import.meta.env.DEV ? '' : 'https://doka.logixaflow.workers.dev';

type ApiState = 'checking' | 'connected' | 'degraded' | 'offline';

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 ** 3)).toFixed(2)} GB`;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  }).format(date);
}

export default function PersonalDashboard() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<CloudDocument[]>([]);
  const [apiState, setApiState] = useState<ApiState>('checking');
  const [apiMessage, setApiMessage] = useState('Checking secure cloud connection');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [healthResponse, configResponse, documentResult] = await Promise.all([
        fetch(`${API_ORIGIN}/health`, { cache: 'no-store' }),
        fetch(`${API_ORIGIN}/api/config`, { cache: 'no-store' }),
        listCloudDocuments(100, 0),
      ]);
      if (!healthResponse.ok || !configResponse.ok) {
        throw new Error('The cloud service did not return a healthy response.');
      }
      const health = await healthResponse.json();
      const config = await configResponse.json();
      if (health.status !== 'healthy' || config.edition !== 'cloud-api' || config.local_workspace_available !== false) {
        throw new Error('Cloud service configuration did not match the expected Doka API.');
      }
      setDocuments(documentResult.documents || []);
      setApiState('connected');
      setApiMessage('Cloud API and document service are responding normally');
    } catch (err) {
      setApiState('degraded');
      setApiMessage('Some cloud services could not be verified');
      setError(err instanceof Error ? err.message : 'Unable to load cloud dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const totalBytes = useMemo(() => documents.reduce((sum, item) => sum + (item.size_bytes || 0), 0), [documents]);
  const reviewCount = useMemo(() => documents.filter(item => item.status === 'review').length, [documents]);
  const recentDocuments = documents.slice(0, 5);

  async function download(item: CloudDocument) {
    try {
      const result = await getCloudDocumentDownloadUrl(item.id);
      window.location.assign(result.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to download this document.');
    }
  }

  return (
    <div className="doka-dashboard space-y-7">
      <section className="doka-hero relative overflow-hidden rounded-3xl p-6 text-white shadow-xl sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full bg-cyan-300/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 right-1/3 h-64 w-64 rounded-full bg-indigo-300/15 blur-3xl" />
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium tracking-wide text-cyan-100">
              <Sparkles className="h-3.5 w-3.5" /> YOUR SECURE DOCUMENT SPACE
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Everything in its place.</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100 sm:text-base">
              Store, organize and retrieve your documents in one private workspace, protected by your account.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => navigate('/admin/cloud-documents')} className="h-11 rounded-xl bg-white px-5 font-semibold text-slate-900 shadow-lg hover:bg-blue-50">
              <CloudUpload className="mr-2 h-4 w-4" /> Upload documents
            </Button>
            <Button onClick={() => void refresh()} disabled={loading} variant="outline" className="h-11 rounded-xl border-white/30 bg-white/10 px-4 text-white hover:bg-white/20 hover:text-white">
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
        </div>
        <div className="relative z-10 mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-white/15 pt-5 text-xs text-blue-100">
          <span className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-300" /> Private by account</span>
          <span className="inline-flex items-center gap-2"><Cloud className="h-4 w-4 text-cyan-200" /> Supabase cloud storage</span>
          <span className="inline-flex items-center gap-2"><FileCheck2 className="h-4 w-4 text-indigo-200" /> SHA-256 integrity fingerprint</span>
        </div>
      </section>

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">{error}</div>}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="doka-stat-card"><CardContent className="flex items-start justify-between p-5">
          <div><p className="text-sm text-muted-foreground">Stored documents</p><p className="mt-2 text-3xl font-semibold tracking-tight">{loading ? '—' : documents.length}</p><p className="mt-1 text-xs text-muted-foreground">In your private library</p></div>
          <span className="rounded-2xl bg-blue-50 p-3 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300"><FileText className="h-5 w-5" /></span>
        </CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-start justify-between p-5">
          <div><p className="text-sm text-muted-foreground">Storage used</p><p className="mt-2 text-3xl font-semibold tracking-tight">{loading ? '—' : formatBytes(totalBytes)}</p><p className="mt-1 text-xs text-muted-foreground">Across listed documents</p></div>
          <span className="rounded-2xl bg-violet-50 p-3 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300"><HardDrive className="h-5 w-5" /></span>
        </CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-start justify-between p-5">
          <div><p className="text-sm text-muted-foreground">Needs review</p><p className="mt-2 text-3xl font-semibold tracking-tight">{loading ? '—' : reviewCount}</p><p className="mt-1 text-xs text-muted-foreground">Marked for your attention</p></div>
          <span className="rounded-2xl bg-amber-50 p-3 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"><FileCheck2 className="h-5 w-5" /></span>
        </CardContent></Card>
        <Card className="doka-stat-card"><CardContent className="flex items-start justify-between p-5">
          <div><p className="text-sm text-muted-foreground">Cloud connection</p><p className="mt-2 text-xl font-semibold tracking-tight">{apiState === 'checking' ? 'Checking' : apiState === 'connected' ? 'Connected' : 'Degraded'}</p><p className="mt-1 text-xs text-muted-foreground">API and account access</p></div>
          <span className={`rounded-2xl p-3 ${apiState === 'connected' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}><Activity className="h-5 w-5" /></span>
        </CardContent></Card>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.8fr)]">
        <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-border/70 px-5 py-4 sm:px-6">
            <div><h2 className="font-semibold">Recently added</h2><p className="mt-1 text-xs text-muted-foreground">Your latest documents</p></div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/cloud-documents')} className="rounded-lg text-primary">View library <ArrowRight className="ml-1 h-4 w-4" /></Button>
          </div>
          <CardContent className="p-0">
            {loading ? <div className="space-y-3 p-6"><div className="h-12 animate-pulse rounded-xl bg-muted" /><div className="h-12 animate-pulse rounded-xl bg-muted" /><div className="h-12 animate-pulse rounded-xl bg-muted" /></div> :
              recentDocuments.length === 0 ? <div className="px-6 py-12 text-center"><span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground"><FileText className="h-6 w-6" /></span><h3 className="mt-4 font-medium">Your library is ready</h3><p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">Upload your first document and it will appear here.</p><Button onClick={() => navigate('/admin/cloud-documents')} className="mt-4 rounded-xl"><CloudUpload className="mr-2 h-4 w-4" /> Add a document</Button></div> :
              <div className="divide-y divide-border/70">{recentDocuments.map(item => <div key={item.id} className="flex items-center gap-3 px-5 py-4 transition-colors hover:bg-muted/40 sm:px-6">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"><FileText className="h-5 w-5" /></span>
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{item.filename}</p><p className="mt-1 text-xs text-muted-foreground">{formatBytes(item.size_bytes)} · {formatDate(item.created_at)}</p></div>
                <Badge variant="outline" className="hidden capitalize sm:inline-flex">{item.status}</Badge>
                <Button variant="ghost" size="icon" aria-label={`Download ${item.filename}`} onClick={() => void download(item)} className="shrink-0 rounded-lg"><ArrowDownToLine className="h-4 w-4" /></Button>
              </div>)}</div>
            }
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/70 shadow-sm">
          <div className="border-b border-border/70 px-5 py-4"><h2 className="font-semibold">Service health</h2><p className="mt-1 text-xs text-muted-foreground">Live connection checks</p></div>
          <CardContent className="space-y-5 p-5">
            <div className="flex items-center gap-3"><span className={`h-2.5 w-2.5 rounded-full ${apiState === 'connected' ? 'bg-emerald-500' : apiState === 'checking' ? 'bg-amber-400 animate-pulse' : 'bg-rose-500'}`} /><div className="min-w-0 flex-1"><p className="text-sm font-medium">Doka Cloud API</p><p className="text-xs text-muted-foreground">{apiMessage}</p></div><Badge variant="outline" className="capitalize">{apiState}</Badge></div>
            <div className="flex items-center gap-3"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /><div className="min-w-0 flex-1"><p className="text-sm font-medium">Account security</p><p className="text-xs text-muted-foreground">Supabase session required for documents</p></div><Badge variant="secondary">Protected</Badge></div>
            <div className="rounded-xl bg-muted/60 p-4"><p className="text-sm font-medium">Local processing</p><p className="mt-1 text-xs leading-5 text-muted-foreground">OCR and Safe Workspace use your local computer and are not run by this cloud website.</p></div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
