import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { Activity, ArrowDownToLine, ArrowRight, Cloud, CloudUpload, FileCheck2, FileText, HardDrive, RefreshCw, ShieldCheck, Sparkles, FolderOpen, Clock3, CircleAlert, LockKeyhole, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { CLOUD_API_ORIGIN, getCloudDocumentDownloadUrl, listCloudDocuments, type CloudDocument } from '@/lib/cloudDocuments';

type ApiState = 'checking' | 'connected' | 'degraded' | 'offline';
function formatBytes(bytes: number) { if (bytes < 1024) return `${bytes} B`; if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`; if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`; return `${(bytes / 1024 ** 3).toFixed(2)} GB`; }
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date); }

export default function PersonalDashboard() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<CloudDocument[]>([]);
  const [apiState, setApiState] = useState<ApiState>('checking');
  const [apiMessage, setApiMessage] = useState('Verifying cloud services');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [healthResponse, configResponse, documentResult] = await Promise.all([
        fetch(`${CLOUD_API_ORIGIN}/health`, { cache: 'no-store' }),
        fetch(`${CLOUD_API_ORIGIN}/api/config`, { cache: 'no-store' }),
        listCloudDocuments({ limit: 100, offset: 0 }),
      ]);
      if (!healthResponse.ok || !configResponse.ok) throw new Error('The cloud service did not return a healthy response.');
      const health = await healthResponse.json(); const config = await configResponse.json();
      if (health.status !== 'healthy' || config.edition !== 'cloud-api' || config.local_workspace_available !== false) throw new Error('Cloud service configuration did not match the expected Doka API.');
      setDocuments(documentResult.documents || []); setApiState('connected'); setApiMessage('Cloud API and document service are responding normally');
    } catch (err) {
      setApiState('degraded'); setApiMessage('Cloud service could not be fully verified'); setError(err instanceof Error ? err.message : 'Unable to load cloud dashboard.');
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);
  const totalBytes = useMemo(() => documents.reduce((sum, item) => sum + (item.size_bytes || 0), 0), [documents]);
  const reviewCount = useMemo(() => documents.filter(item => item.status === 'review').length, [documents]);
  const recentDocuments = documents.slice(0, 5);
  async function download(item: CloudDocument) { try { const result = await getCloudDocumentDownloadUrl(item.id); window.location.assign(result.url); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to download this document.'); } }
  const statItems = [
    { label: 'Documents stored', value: loading ? '—' : documents.length.toLocaleString(), note: 'In your private library', icon: FileText, tone: 'blue' },
    { label: 'Storage used', value: loading ? '—' : formatBytes(totalBytes), note: 'Across listed documents', icon: HardDrive, tone: 'violet' },
    { label: 'Needs attention', value: loading ? '—' : reviewCount.toLocaleString(), note: 'Marked for your review', icon: FileCheck2, tone: 'amber' },
    { label: 'Cloud service', value: apiState === 'checking' ? 'Checking' : apiState === 'connected' ? 'Connected' : 'Degraded', note: 'API and account access', icon: Activity, tone: apiState === 'connected' ? 'green' : 'slate' },
  ];
  return <div className="doka-dashboard">
    <section className="doka-hero relative overflow-hidden rounded-[26px] px-6 py-7 text-white shadow-[0_20px_55px_rgba(10,28,55,.15)] sm:px-9 sm:py-9 lg:px-10">
      <div className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full bg-cyan-300/10 blur-3xl"/><div className="pointer-events-none absolute -bottom-32 right-1/3 h-72 w-72 rounded-full bg-indigo-300/10 blur-3xl"/>
      <div className="relative z-10 flex flex-col justify-between gap-7 xl:flex-row xl:items-end"><div className="max-w-2xl">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[.07] px-3 py-1.5 text-[10px] font-bold tracking-[.14em] text-cyan-100"><Sparkles className="h-3.5 w-3.5"/> YOUR PRIVATE DOCUMENT HUB</div>
        <h1 className="max-w-xl text-[34px] font-semibold leading-[1.1] tracking-[-.045em] sm:text-[44px]">A calmer way to manage your documents.</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-slate-300 sm:text-[15px]">Keep important files organized, accessible and protected in one workspace built around your account.</p>
      </div><div className="flex flex-wrap gap-2.5"><Button onClick={() => navigate('/admin/cloud-documents')} className="h-11 rounded-xl bg-cyan-300 px-5 font-semibold text-slate-950 shadow-lg shadow-cyan-950/20 hover:bg-cyan-200"><CloudUpload className="mr-2 h-4 w-4"/> Add documents</Button><Button onClick={() => void refresh()} disabled={loading} variant="outline" className="h-11 rounded-xl border-white/20 bg-white/[.07] px-4 text-white hover:bg-white/15 hover:text-white"><RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`}/> Refresh</Button></div></div>
      <div className="relative z-10 mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-white/10 pt-5 text-[11px] font-medium text-slate-300"><span className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-300"/> Account-scoped access</span><span className="inline-flex items-center gap-2"><Cloud className="h-4 w-4 text-cyan-200"/> Private cloud storage</span><span className="inline-flex items-center gap-2"><FileCheck2 className="h-4 w-4 text-indigo-200"/> SHA-256 integrity checks</span></div>
    </section>
    {error && <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-800 dark:border-rose-900/70 dark:bg-rose-950/30 dark:text-rose-200"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0"/><div className="min-w-0 flex-1"><p className="font-semibold">We couldn't refresh your workspace</p><p className="mt-1 leading-5">{error}</p></div><Button variant="ghost" size="sm" onClick={() => void refresh()} className="shrink-0">Try again</Button></div>}
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{statItems.map(item => <Card key={item.label} className="doka-stat border-0 shadow-none"><CardContent className="p-0"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">{item.label}</p><p className="mt-3 truncate text-[28px] font-semibold leading-none tracking-[-.04em] text-slate-900 dark:text-slate-100">{item.value}</p><p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">{item.note}</p></div><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] ${item.tone === 'blue' ? 'bg-blue-50 text-blue-700 dark:bg-blue-400/10 dark:text-blue-300' : item.tone === 'violet' ? 'bg-violet-50 text-violet-700 dark:bg-violet-400/10 dark:text-violet-300' : item.tone === 'amber' ? 'bg-amber-50 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300' : item.tone === 'green' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}><item.icon className="h-[18px] w-[18px]"/></span></div></CardContent></Card>)}</section>
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,.8fr)]">
      <div className="doka-panel overflow-hidden"><div className="flex items-center justify-between gap-3 px-5 py-5 sm:px-6"><div><p className="doka-eyebrow text-slate-400">Your library</p><h2 className="mt-1.5 text-lg font-semibold text-slate-900 dark:text-slate-100">Recently added</h2><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">The latest files in your workspace</p></div><Button variant="outline" size="sm" onClick={() => navigate('/admin/cloud-documents')} className="h-9 rounded-xl border-slate-200 bg-white text-xs dark:border-slate-700 dark:bg-slate-900">Open library <ArrowRight className="ml-1.5 h-3.5 w-3.5"/></Button></div>
        <div className="border-t border-slate-100 dark:border-slate-800">{loading ? <div className="space-y-3 p-6">{[1,2,3].map(i => <div key={i} className="h-[58px] animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800"/>)}</div> : recentDocuments.length === 0 ? <div className="px-6 py-12 text-center"><span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-slate-800"><FolderOpen className="h-5 w-5"/></span><h3 className="mt-4 text-sm font-semibold text-slate-900 dark:text-slate-100">Your library is ready</h3><p className="mx-auto mt-1 max-w-xs text-xs leading-5 text-slate-500 dark:text-slate-400">Add your first document to start building a secure, organized library.</p><Button onClick={() => navigate('/admin/cloud-documents')} className="mt-4 h-9 rounded-xl"><CloudUpload className="mr-2 h-4 w-4"/> Upload a file</Button></div> : <div>{recentDocuments.map(item => <div key={item.id} className="doka-table-row flex items-center gap-3 px-5 py-4 sm:px-6"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-400/10 dark:text-blue-300"><FileText className="h-[18px] w-[18px]"/></span><div className="min-w-0 flex-1"><p className="truncate text-[13px] font-semibold text-slate-800 dark:text-slate-100">{item.filename}</p><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{formatBytes(item.size_bytes)} <span className="mx-1">·</span> {formatDate(item.created_at)}</p></div><Badge variant="outline" className="hidden rounded-full px-2 text-[10px] capitalize sm:inline-flex">{item.status}</Badge><Button variant="ghost" size="icon" aria-label={`Download ${item.filename}`} onClick={() => void download(item)} className="h-8 w-8 shrink-0 rounded-lg text-slate-500"><ArrowDownToLine className="h-4 w-4"/></Button></div>)}</div>}</div>
      </div>
      <div className="space-y-5"><div className="doka-panel overflow-hidden"><div className="px-5 py-5"><p className="doka-eyebrow text-slate-400">System status</p><h2 className="mt-1.5 text-lg font-semibold text-slate-900 dark:text-slate-100">Connection health</h2><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Live checks from this workspace</p></div><div className="space-y-4 border-t border-slate-100 px-5 py-5 dark:border-slate-800"><div className="flex items-start gap-3"><span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${apiState === 'connected' ? 'bg-emerald-500' : apiState === 'checking' ? 'animate-pulse bg-amber-400' : 'bg-rose-500'}`}/><div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-800 dark:text-slate-100">Doka Cloud API</p><p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">{apiMessage}</p></div><Badge variant="outline" className="rounded-full text-[9px] capitalize">{apiState}</Badge></div><div className="flex items-start gap-3"><span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-emerald-500"/><div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-800 dark:text-slate-100">Account protection</p><p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">A signed-in session is required to access private documents.</p></div><LockKeyhole className="h-4 w-4 text-emerald-600 dark:text-emerald-400"/></div></div></div>
        <div className="doka-panel p-5"><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-400/10 dark:text-indigo-300"><Clock3 className="h-5 w-5"/></span><div><p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Designed for privacy</p><p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Cloud storage with local tools</p></div></div><p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">OCR and Safe Workspace processing run on your computer. They are separate from the cloud dashboard.</p><Button variant="ghost" onClick={() => navigate('/admin/activity')} className="mt-2 h-8 px-0 text-xs font-semibold text-blue-700 hover:bg-transparent dark:text-blue-300">Review account activity <ChevronRight className="ml-1 h-3.5 w-3.5"/></Button></div>
      </div>
    </section>
  </div>;
}
