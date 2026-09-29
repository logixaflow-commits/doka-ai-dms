import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

const API_BASE = '/api/workspace';

type Proposal = {
  relative_path: string;
  action: string;
  confidence: number;
  reason: string;
  category?: string;
  target?: string | null;
  suggested_filename?: string;
};

type Status = {
  session_id: string;
  state: string;
  progress?: number;
  files_total?: number;
  files_copied?: number;
  files_verified?: number;
  files_failed?: number;
  bytes_total?: number;
  bytes_copied?: number;
  working_copy?: string;
  error?: string | null;
};

function authHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function api(path: string, options: RequestInit = {}) {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(options.headers || {}) },
  });
}

export default function WorkspaceReview() {
  const [sessionId, setSessionId] = useState('');
  const [source, setSource] = useState('');
  const [status, setStatus] = useState<Status | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [ocrStatus, setOcrStatus] = useState<any>(null);
  const [backupStatus, setBackupStatus] = useState<string>('');

  const selectedCount = selected.size;
  const reviewCount = useMemo(() => proposals.filter(p => p.action.startsWith('review')).length, [proposals]);

  async function startImport() {
    setBusy(true); setMessage('');
    try {
      const response = await api('/imports', { method: 'POST', body: JSON.stringify(source.trim() ? { source: source.trim() } : {}) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Import failed');
      setSessionId(data.session_id);
      setStatus(data);
      setProposals([]);
      setSelected(new Set());
      setMessage('Import started. The original source is not modified.');
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Import failed'); }
    finally { setBusy(false); }
  }

  async function loadStatus() {
    if (!sessionId) return;
    const response = await api(`/imports/${encodeURIComponent(sessionId)}`);
    if (response.ok) setStatus(await response.json());
  }

  async function runStep(step: 'scan' | 'understand' | 'plan') {
    setBusy(true); setMessage('');
    try {
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/${step}`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `${step} failed`);
      if (step === 'plan') setProposals(data.proposals || []);
      setMessage(`${step} completed.`);
    } catch (e) { setMessage(e instanceof Error ? e.message : `${step} failed`); }
    finally { setBusy(false); }
  }

  async function validateOcr() {
    setBusy(true); setMessage('');
    try {
      const response = await api('/ocr/validate');
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'OCR validation failed');
      setOcrStatus(data);
      setMessage(data.available ? 'Myanmar + English OCR environment is available.' : 'OCR environment needs attention; see checks below.');
    } catch (e) { setMessage(e instanceof Error ? e.message : 'OCR validation failed'); }
    finally { setBusy(false); }
  }

  async function createBackup() {
    setBusy(true); setMessage('');
    try {
      const response = await api('/backups', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Backup failed');
      setBackupStatus(data.sha256 || '');
      setMessage('Workspace backup created and SHA-256 recorded.');
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Backup failed'); }
    finally { setBusy(false); }
  }

  async function downloadFile(relativePath: string) {
    try {
      const encoded = relativePath.split('/').map(encodeURIComponent).join('/');
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/files/${encoded}?download=true`);
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = relativePath.split('/').pop() || 'document';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Download failed'); }
  }

  async function previewFile(relativePath: string) {
    try {
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/files/${relativePath.split('/').map(encodeURIComponent).join('/')}`);
      if (!response.ok) throw new Error('Preview failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Preview failed'); }
  }

  async function searchWorkingCopy() {
    if (!sessionId || !query.trim()) return;
    setBusy(true); setMessage('');
    try {
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/search?q=${encodeURIComponent(query.trim())}&limit=100`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Search failed');
      setSearchResults(data.results || []);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Search failed'); }
    finally { setBusy(false); }
  }

  async function applySelected() {
    if (!sessionId || selected.size === 0) return;
    if (!window.confirm(`Copy ${selected.size} approved file(s) into Final? The working copy remains unchanged.`)) return;
    setBusy(true); setMessage('');
    try {
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/apply`, {
        method: 'POST',
        body: JSON.stringify({ approved_paths: Array.from(selected), confirm: true }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Apply failed');
      setMessage(`Apply completed: ${(data.results || []).filter((r: any) => r.status === 'copied').length} copied.`);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Apply failed'); }
    finally { setBusy(false); }
  }

  async function undo() {
    if (!sessionId || !window.confirm('Undo this session\'s verified Final copies? Changed files will be preserved.')) return;
    setBusy(true); setMessage('');
    try {
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/undo`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Undo failed');
      setMessage(`Undo completed: ${(data.results || []).filter((r: any) => r.status === 'removed').length} removed.`);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Undo failed'); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!sessionId) return;
    loadStatus();
    const timer = window.setInterval(loadStatus, 3000);
    return () => window.clearInterval(timer);
  }, [sessionId]);

  function toggle(path: string) {
    const next = new Set(selected);
    next.has(path) ? next.delete(path) : next.add(path);
    setSelected(next);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Safe Workspace</h1>
        <p className="text-sm text-slate-500">Copy → verify → understand → review → approve. Original source is never modified.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>1. Import a source folder</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Input value={source} onChange={e => setSource(e.target.value)} placeholder="Optional local source path; otherwise SOURCE_ROOT" />
          <div className="flex gap-2">
            <Button onClick={startImport} disabled={busy}>Start Safe Import</Button>
            {sessionId && <Badge variant="outline">{sessionId}</Badge>}
          </div>
        </CardContent>
      </Card>

      {sessionId && (
        <>
          <Card>
            <CardHeader><CardTitle>2. Processing status</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-3 text-sm">
                <span>Status: <strong>{status?.state || 'unknown'}</strong></span>
                <span>Progress: <strong>{Math.round((status?.progress || 0) * 100)}%</strong></span>
                <span>Verified: <strong>{status?.files_verified || 0}/{status?.files_total || 0}</strong></span>
                <span>Failed: <strong>{status?.files_failed || 0}</strong></span>
              </div>
              <div className="h-2 rounded bg-slate-100 overflow-hidden"><div className="h-full bg-blue-600" style={{ width: `${Math.round((status?.progress || 0) * 100)}%` }} /></div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => runStep('scan')} disabled={busy || status?.state === 'running'}>Scan Copy</Button>
                <Button variant="outline" onClick={() => runStep('understand')} disabled={busy}>Read / OCR</Button>
                <Button onClick={() => runStep('plan')} disabled={busy}>Build Review Plan</Button>
                <Button variant="outline" onClick={undo} disabled={busy}>Undo Applied Copies</Button>
                <Button variant="outline" onClick={createBackup} disabled={busy}>Backup Workspace</Button>
                <Button variant="outline" onClick={validateOcr} disabled={busy}>Check OCR</Button>
              </div>
              {ocrStatus && <div className="text-xs text-slate-500">OCR: {ocrStatus.available ? 'Myanmar + English ready' : 'Needs attention'} · {ocrStatus.executable}</div>}
              {backupStatus && <div className="text-xs text-slate-500 break-all">Backup SHA-256: {backupStatus}</div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Search working copy</CardTitle></CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchWorkingCopy()} placeholder="Filename, folder, OCR/text keyword..." />
                <Button onClick={searchWorkingCopy} disabled={busy || !query.trim()}>Search</Button>
              </div>
              {searchResults.length > 0 && (
                <div className="mt-4 space-y-2">
                  {searchResults.map((item) => <div key={item.relative_path} className="rounded border p-3">
                    <div className="flex items-start justify-between gap-3"><div className="font-medium break-all">{item.relative_path}</div><div className="flex gap-1"><Button variant="outline" size="sm" onClick={() => previewFile(item.relative_path)}>Preview</Button><Button variant="outline" size="sm" onClick={() => downloadFile(item.relative_path)}>Download</Button></div></div>
                    {item.text_preview && <div className="text-xs text-slate-500 mt-1 line-clamp-2">{item.text_preview}</div>}
                  </div>)}
                </div>
              )}
            </CardContent>
          </Card>

          {proposals.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>3. Review organization proposals</CardTitle>
                  <div className="text-sm text-slate-500">{selectedCount} selected · {reviewCount} need review</div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2 mb-4">
                  <Button variant="outline" onClick={() => setSelected(new Set(proposals.filter(p => !p.action.startsWith('review') && p.target).map(p => p.relative_path)))}>Select safe suggestions</Button>
                  <Button variant="outline" onClick={() => setSelected(new Set())}>Clear</Button>
                  <Button onClick={applySelected} disabled={busy || selected.size === 0}>Approve & Copy Selected</Button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="border-b text-left"><th className="p-2">✓</th><th className="p-2">File</th><th className="p-2">Action</th><th className="p-2">Confidence</th><th className="p-2">Reason</th><th className="p-2">Target</th></tr></thead>
                    <tbody>
                      {proposals.map(p => (
                        <tr key={p.relative_path} className="border-b align-top">
                          <td className="p-2"><Checkbox checked={selected.has(p.relative_path)} onCheckedChange={() => toggle(p.relative_path)} /></td>
                          <td className="p-2 max-w-[260px] break-all">{p.relative_path}</td>
                          <td className="p-2"><Badge variant={p.action.startsWith('review') ? 'destructive' : 'secondary'}>{p.action}</Badge></td>
                          <td className="p-2">{Math.round(p.confidence * 100)}%</td>
                          <td className="p-2">{p.reason}</td>
                          <td className="p-2 max-w-[360px] break-all">{p.target || 'Manual review'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {message && <div className="rounded border p-3 text-sm bg-slate-50">{message}</div>}
        </>
      )}
    </div>
  );
}
