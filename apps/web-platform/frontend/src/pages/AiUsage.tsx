import { useEffect, useState } from 'react';
import { Activity, Cpu, RefreshCw, ShieldCheck, Sparkles, AlertTriangle, Send } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { CLOUD_API_ORIGIN } from '@/lib/cloudDocuments';

interface ProviderStat {
  configured: boolean;
  status: string;
  calls_today: number;
  total_calls: number;
  errors_today: number;
  last_used: string | null;
}

interface UsageSummary {
  project: string;
  timestamp: string;
  date: string;
  total_calls_today: number;
  active_chains: {
    chat_priority?: string[];
    rag_priority?: string[];
    classification?: string[];
  };
  providers: Record<string, ProviderStat>;
}

export default function AiUsage() {
  const [data, setData] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${CLOUD_API_ORIGIN}/api/ai/usage`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch usage`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Failed to connect to AI usage endpoint');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const loadUsage = async () => {
      try {
        const res = await fetch(`${CLOUD_API_ORIGIN}/api/ai/usage`, {
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch usage`);
        const json = await res.json();
        setData(json);
        setError(null);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error(err);
        setError(err instanceof Error ? err.message : 'Failed to connect to AI usage endpoint');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    void loadUsage();
    return () => controller.abort();
  }, []);

  const providers = data?.providers ? Object.entries(data.providers) : [];
  const activeCount = providers.filter(([, p]) => p.status === 'active').length;
  const errorCount = providers.reduce((sum, [, p]) => sum + (p.errors_today || 0), 0);

  return (
    <div className="doka-dashboard">
      {/* Top Hero Banner */}
      <section className="doka-hero relative overflow-hidden rounded-[26px] px-6 py-7 text-white shadow-[0_20px_55px_rgba(10,28,55,.15)] sm:px-9 sm:py-9 lg:px-10">
        <div className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full bg-cyan-300/10 blur-3xl" />
        <div className="relative z-10 flex flex-col justify-between gap-7 xl:flex-row xl:items-end">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[.07] px-3 py-1 text-[10px] font-bold tracking-[.14em] text-cyan-200">
              <Sparkles className="h-3.5 w-3.5" /> AI ENGINE & FAILOVER INTELLIGENCE
            </div>
            <h1 className="text-[32px] font-semibold leading-[1.15] tracking-tight sm:text-[40px]">
              Multi-Provider AI Quota & Health Tracking
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Live metering across Voyage AI RAG, Groq, Gemini, and Cohere with native Telegram 429 quota alerts.
            </p>
          </div>
          <div className="flex gap-2.5">
            <Button
              onClick={() => void fetchUsage()}
              disabled={loading}
              variant="outline"
              className="h-11 rounded-xl border-white/20 bg-white/[.07] px-4 text-white hover:bg-white/15 hover:text-white"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Usage
            </Button>
          </div>
        </div>
      </section>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-800 dark:border-rose-900/70 dark:bg-rose-950/30 dark:text-rose-200"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="font-semibold">Unable to fetch live usage statistics</p>
            <p className="mt-1 leading-5">{error}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => void fetchUsage()} className="shrink-0">
            Try again
          </Button>
        </div>
      )}

      {/* KPI Stat Cards */}
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="doka-stat border-0 shadow-none">
          <CardContent className="p-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">Total Calls Today</p>
                <p className="mt-3 truncate text-[28px] font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                  {loading ? '—' : (data?.total_calls_today ?? 0).toLocaleString()}
                </p>
                <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Across active AI chains</p>
              </div>
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] bg-blue-50 text-blue-700 dark:bg-blue-400/10 dark:text-blue-300">
                <Cpu className="h-[18px] w-[18px]" />
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="doka-stat border-0 shadow-none">
          <CardContent className="p-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">Active Providers</p>
                <p className="mt-3 truncate text-[28px] font-semibold tracking-tight text-cyan-500">
                  {loading ? '—' : `${activeCount} / ${providers.length}`}
                </p>
                <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Operational & ready</p>
              </div>
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] bg-cyan-50 text-cyan-700 dark:bg-cyan-400/10 dark:text-cyan-300">
                <ShieldCheck className="h-[18px] w-[18px]" />
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="doka-stat border-0 shadow-none">
          <CardContent className="p-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">429 Rate Limits</p>
                <p
                  className={`mt-3 truncate text-[28px] font-semibold tracking-tight ${
                    errorCount > 0 ? 'text-rose-500' : 'text-emerald-500'
                  }`}
                >
                  {loading ? '—' : errorCount}
                </p>
                <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Auto-failover triggers</p>
              </div>
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] ${
                  errorCount > 0
                    ? 'bg-rose-50 text-rose-700 dark:bg-rose-400/10 dark:text-rose-300'
                    : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300'
                }`}
              >
                <Activity className="h-[18px] w-[18px]" />
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="doka-stat border-0 shadow-none">
          <CardContent className="p-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">Telegram Direct Alert</p>
                <div className="mt-3 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-base font-bold text-emerald-600 dark:text-emerald-400">Live Active</span>
                </div>
                <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Direct bot quota monitoring</p>
              </div>
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[13px] bg-emerald-50 text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
                <Send className="h-[18px] w-[18px]" />
              </span>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Failover Chains Overview */}
      <section className="grid gap-5 xl:grid-cols-2">
        <div className="doka-panel p-6">
          <p className="doka-eyebrow text-slate-400">Failover Chain 1</p>
          <h2 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
            Document Classification & Processing
          </h2>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 font-mono font-semibold text-cyan-400">
              1. Groq (Qwen-27B)
            </span>
            <span className="text-slate-500">&rarr;</span>
            <span className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 font-mono text-slate-300">
              2. Gemini Flash
            </span>
            <span className="text-slate-500">&rarr;</span>
            <span className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 font-mono text-slate-300">
              3. Cohere
            </span>
            <span className="text-slate-500">&rarr;</span>
            <span className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 font-mono text-slate-300">
              4. Cloudflare
            </span>
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
            Upon HTTP 429 or quota exhaustion, requests immediately failover to next provider and notify Telegram.
          </p>
        </div>

        <div className="doka-panel p-6">
          <p className="doka-eyebrow text-slate-400">Failover Chain 2</p>
          <h2 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
            Vector Embeddings & RAG Search (512-D)
          </h2>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 font-mono font-semibold text-cyan-400">
              1. Voyage AI (voyage-3-lite)
            </span>
            <span className="text-slate-500">&rarr;</span>
            <span className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 font-mono text-slate-300">
              2. Cohere (embed-v4.0)
            </span>
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
            Both models output exactly 512-dimension vectors, allowing zero re-indexing vector failover.
          </p>
        </div>
      </section>

      {/* Provider Details Table */}
      <section className="doka-panel overflow-hidden">
        <div className="px-6 py-5">
          <p className="doka-eyebrow text-slate-400">Key Registry</p>
          <h2 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
            Real-Time Provider Usage & Status
          </h2>
        </div>
        <div className="border-t border-slate-100 dark:border-slate-800">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-100 bg-slate-50/50 text-slate-500 dark:border-slate-800 dark:bg-slate-900/50">
                <tr>
                  <th className="px-6 py-3 font-semibold">Provider</th>
                  <th className="px-6 py-3 font-semibold">Status</th>
                  <th className="px-6 py-3 text-right font-semibold">Calls Today</th>
                  <th className="px-6 py-3 text-right font-semibold">Total Calls</th>
                  <th className="px-6 py-3 text-right font-semibold">429 Errors</th>
                  <th className="px-6 py-3 font-semibold">Health Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {providers.map(([name, stat]) => {
                  const isExhausted = stat.status.includes('exhausted');
                  const isActive = stat.status === 'active';
                  return (
                    <tr key={name} className="doka-table-row">
                      <td className="px-6 py-4 font-semibold capitalize text-slate-900 dark:text-slate-100">
                        {name}
                      </td>
                      <td className="px-6 py-4">
                        <Badge
                          variant="outline"
                          className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                            isActive
                              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300'
                              : isExhausted
                              ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300'
                              : 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400'
                          }`}
                        >
                          {stat.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-slate-700 dark:text-slate-300">
                        {stat.calls_today}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-slate-500 dark:text-slate-400">
                        {stat.total_calls}
                      </td>
                      <td
                        className={`px-6 py-4 text-right font-mono font-semibold ${
                          stat.errors_today > 0 ? 'text-rose-500' : 'text-slate-500 dark:text-slate-400'
                        }`}
                      >
                        {stat.errors_today}
                      </td>
                      <td className="px-6 py-4 text-slate-500 dark:text-slate-400">
                        {isExhausted ? 'Quota alert dispatched' : isActive ? 'Ready / Operational' : 'Not configured'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
