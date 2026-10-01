import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FolderKanban, ShieldCheck, Bot, FileCheck2, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const HEALTH_BASE = API_BASE.endsWith('/api') ? API_BASE.slice(0, -4) : API_BASE;

type SystemConfig = { edition: string; ai_enabled: boolean; source_read_only: boolean; workspace_root_configured: boolean; };
type Health = { status: string; edition: string; ai_enabled: boolean; source_read_only: boolean; };

export default function PersonalDashboard() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<Health | null>(null);
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [error, setError] = useState('');

  async function refresh() {
    setError('');
    try {
      const [healthResponse, configResponse] = await Promise.all([fetch(`${HEALTH_BASE}/health`), fetch(`${API_BASE}/config`)]);
      if (!healthResponse.ok || !configResponse.ok) throw new Error('Local backend is not reachable.');
      setHealth(await healthResponse.json());
      setConfig(await configResponse.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to read local system status.');
    }
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Doka</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Safe local document organization with the original source kept read-only.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refresh}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button variant="outline" onClick={() => navigate('/admin/cloud-documents')}>Cloud Documents</Button>
          <Button onClick={() => navigate('/admin/workspace')}><FolderKanban className="mr-2 h-4 w-4" />Open Safe Workspace</Button>
        </div>
      </div>
      {error && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="h-5 w-5" />Source protection</CardTitle></CardHeader><CardContent><Badge variant={health?.source_read_only ? 'secondary' : 'destructive'}>{health?.source_read_only ? 'READ-ONLY' : 'CHECK CONFIG'}</Badge><p className="mt-2 text-xs text-slate-500">Original source is never used as a writable workspace.</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><FileCheck2 className="h-5 w-5" />Local workflow</CardTitle></CardHeader><CardContent><p className="font-medium">Copy → Verify → Read → Review → Approve</p><p className="mt-2 text-xs text-slate-500">Organization copies approved files into Final.</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Bot className="h-5 w-5" />AI</CardTitle></CardHeader><CardContent><Badge variant={health?.ai_enabled ? 'secondary' : 'outline'}>{health?.ai_enabled ? 'ENABLED' : 'OFF BY DEFAULT'}</Badge><p className="mt-2 text-xs text-slate-500">Local processing works without AI providers.</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-base">Backend status</CardTitle></CardHeader><CardContent><Badge variant={health?.status === 'healthy' ? 'secondary' : 'destructive'}>{health?.status || 'CHECKING'}</Badge><p className="mt-2 text-xs text-slate-500">Doka · {config?.edition || health?.edition || 'personal-local'}</p></CardContent></Card>
      </div>
      <Card>
        <CardHeader><CardTitle>What to do next</CardTitle></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Button className="justify-start" variant="outline" onClick={() => navigate('/admin/workspace')}>1. Import a test folder</Button>
          <Button className="justify-start" variant="outline" onClick={() => navigate('/admin/workspace')}>2. Scan and read the verified copy</Button>
          <Button className="justify-start" variant="outline" onClick={() => navigate('/admin/workspace')}>3. Review duplicate/version suggestions</Button>
          <Button className="justify-start" variant="outline" onClick={() => navigate('/admin/workspace')}>4. Approve a small batch and create a backup</Button>
        </CardContent>
      </Card>
    </div>
  );
}
