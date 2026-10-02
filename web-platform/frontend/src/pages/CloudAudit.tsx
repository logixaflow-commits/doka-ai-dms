import { useEffect, useState } from 'react';
import { Activity, AlertCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { listCloudAuditEvents, type CloudAuditEvent } from '@/lib/cloudDocuments';

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export default function CloudAudit() {
  const [events, setEvents] = useState<CloudAuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true); setError('');
    try { setEvents((await listCloudAuditEvents(100)).events || []); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to load activity.'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);

  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary"><ShieldCheck className="h-4 w-4" /> Account history</div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">Activity</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">A private record of important document actions in your account.</p>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading} className="h-10 rounded-xl"><RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Refresh</Button>
      </section>
      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm"><CardContent className="p-0">
        {loading ? <div className="space-y-3 p-6"><div className="h-14 animate-pulse rounded-xl bg-muted" /><div className="h-14 animate-pulse rounded-xl bg-muted" /></div> :
          events.length === 0 ? <div className="px-6 py-14 text-center"><Activity className="mx-auto h-8 w-8 text-muted-foreground" /><h2 className="mt-4 font-semibold">No activity yet</h2><p className="mt-1 text-sm text-muted-foreground">Document actions will appear here after your first cloud operation.</p></div> :
          <div className="divide-y divide-border/70">{events.map(event => <div key={event.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div className="flex min-w-0 items-start gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><Activity className="h-4 w-4" /></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Badge variant="outline" className="capitalize">{event.action.replace('_', ' ')}</Badge><p className="break-all text-sm font-medium">{event.filename || 'Document'}</p></div><p className="mt-1 text-xs text-muted-foreground">{formatDate(event.created_at)}</p></div></div><p className="text-xs text-muted-foreground sm:max-w-[45%] sm:text-right">{event.document_id ? `Document ID: ${event.document_id}` : 'Account event'}</p></div>)}</div>}
      </CardContent></Card>
    </div>
  );
}
