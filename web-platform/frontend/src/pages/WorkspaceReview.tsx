import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

const API_BASE = `${(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')}/workspace`;

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

type ImportSession = Pick<Status, 'session_id' | 'state' | 'files_verified' | 'files_total'>;
type SearchResult = { relative_path: string; text_preview?: string | null };
type OcrResult = {
  relative_path: string;
  extraction_method?: string | null;
  language?: string | null;
  corrected_text?: string | null;
  text_preview?: string | null;
  ocr_corrected?: boolean;
};
type OcrValidationStatus = { available: boolean; executable?: string | null };
type ActionResult = { status: string };
type BackupInfo = { archive: string; created_at?: string; sha256?: string };

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

function LocalWorkspaceReview() {
  const [sessionId, setSessionId] = useState('');
  const [source, setSource] = useState('');
  const [status, setStatus] = useState<Status | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [ocrStatus, setOcrStatus] = useState<OcrValidationStatus | null>(null);
  const [backupStatus, setBackupStatus] = useState<string>('');
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [sessions, setSessions] = useState<ImportSession[]>([]);
  const [showReviewOnly, setShowReviewOnly] = useState(false);
  const [extensionFilter, setExtensionFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [ocrResults, setOcrResults] = useState<OcrResult[]>([]);
  const [editingOcr, setEditingOcr] = useState<string | null>(null);
  const [ocrDraft, setOcrDraft] = useState('');

  const visibleProposals = useMemo(
    () => showReviewOnly ? proposals.filter(p => p.action.startsWith('review')) : proposals,
    [proposals, showReviewOnly]
  );
  const selectedCount = selected.size;
  const reviewCount = useMemo(() => proposals.filter(p => p.action.startsWith('review')).length, [proposals]);

  const loadSessions = useCallback(async () => {
    try {
      const response = await api('/imports?limit=50');
      if (response.ok) {
        const data = await response.json() as { imports?: ImportSession[] };
        setSessions(data.imports || []);
      } else if (response.status === 401 || response.status === 403) {
        setMessage('Please sign in with a staff account to use Safe Workspace.');
      }
    } catch {
      setMessage('Safe Workspace is unavailable. Check that the local backend is running.');
    }
  }, []);

  const loadBackups = useCallback(async () => {
    try {
      const response = await api('/backups');
      if (response.ok) {
        const data = await response.json() as { backups?: BackupInfo[] };
        setBackups(data.backups || []);
      }
    } catch {
      setMessage('Backup list is unavailable. Check that the local backend is running.');
    }
  }, []);

  function resumeSession(id: string) {
    setSessionId(id);
    setStatus(null);
    setProposals([]);
    setSelected(new Set());
    setSearchResults([]);
    setOcrResults([]);
    setEditingOcr(null);
    setOcrDraft('');
    setMessage('Existing workspace session loaded.');
  }

  async function startImport() {
    setBusy(true); setMessage('');
    try {
      const response = await api('/imports', { method: 'POST', body: JSON.stringify(source.trim() ? { source: source.trim() } : {}) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Import failed');
      setSessionId(data.session_id);
      setStatus(data);
      loadSessions();
      setProposals([]);
      setSelected(new Set());
      setSearchResults([]);
      setOcrResults([]);
      setEditingOcr(null);
      setOcrDraft('');
      setMessage('Import started. The original source is not modified.');
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Import failed'); }
    finally { setBusy(false); }
  }

  const loadStatus = useCallback(async () => {
    if (!sessionId) return;
    const response = await api(`/imports/${encodeURIComponent(sessionId)}`);
    if (response.ok) setStatus(await response.json() as Status);
  }, [sessionId]);

  async function runStep(step: 'scan' | 'understand' | 'plan') {
    setBusy(true); setMessage('');
    // Clear dependent state before the request so a failed scan/OCR/plan cannot
    // leave results or approvals from an earlier operation visible and actionable.
    setProposals([]);
    setSelected(new Set());
    if (step === 'scan') {
      setSearchResults([]);
      setOcrResults([]);
      setEditingOcr(null);
      setOcrDraft('');
    } else if (step === 'understand') {
      setOcrResults([]);
      setEditingOcr(null);
      setOcrDraft('');
    }
    try {
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/${step}`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `${step} failed`);
      if (step === 'plan') {
        setProposals(data.proposals || []);
      }
      if (step === 'understand') {
        const detail = await api(`/imports/${encodeURIComponent(sessionId)}/understanding`);
        if (!detail.ok) throw new Error('OCR results could not be loaded.');
        setOcrResults((await detail.json()).results || []);
      }
      await loadStatus();
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
      await loadBackups();
      setMessage('Workspace backup created and SHA-256 recorded.');
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Backup failed'); }
    finally { setBusy(false); }
  }

  async function verifyBackup(archivePath: string) {
    const archiveName = archivePath.split(/[\\/]/).pop() || archivePath;
    setBusy(true); setMessage('');
    try {
      const response = await api(`/backups/verify?archive_name=${encodeURIComponent(archiveName)}`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Backup verification failed');
      setMessage(data.verified ? `Backup verified: ${archiveName}` : `Backup integrity check failed: ${archiveName}`);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Backup verification failed'); }
    finally { setBusy(false); }
  }

  async function restoreBackup(archivePath: string) {
    const archiveName = archivePath.split(/[\\/]/).pop() || archivePath;
    if (!window.confirm(`Restore ${archiveName} into a separate Recovery folder? The active workspace will not be overwritten.`)) return;
    setBusy(true); setMessage('');
    try {
      const response = await api(`/backups/restore?archive_name=${encodeURIComponent(archiveName)}`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Backup restore failed');
      setMessage(`Backup restored to Recovery: ${data.recovery_path}. Active workspace unchanged.`);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Backup restore failed'); }
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

  async function saveOcrCorrection(relativePath: string) {
    if (!sessionId) return;
    setBusy(true); setMessage('');
    try {
      const encoded = relativePath.split('/').map(encodeURIComponent).join('/');
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/understanding/${encoded}`, {
        method: 'PUT',
        body: JSON.stringify({ text: ocrDraft }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'OCR correction failed');
      setOcrResults(prev => prev.map(item => item.relative_path === relativePath
        ? { ...item, corrected_text: ocrDraft, ocr_corrected: Boolean(ocrDraft.trim()) }
        : item));
      setEditingOcr(null);
      // The previous categorization may depend on OCR text; require a fresh plan.
      setProposals([]);
      setSelected(new Set());
      setMessage('OCR correction saved as metadata; rebuild the review plan before applying. The document file was not changed.');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'OCR correction failed');
    } finally {
      setBusy(false);
    }
  }

  async function searchWorkingCopy() {
    if (!sessionId || !query.trim()) return;
    setBusy(true); setMessage('');
    try {
      const params = new URLSearchParams({ q: query.trim(), limit: '100' });
      if (extensionFilter.trim()) params.set('extension', extensionFilter.trim());
      if (categoryFilter.trim()) params.set('category', categoryFilter.trim());
      if (showReviewOnly) params.set('review_only', 'true');
      const response = await api(`/imports/${encodeURIComponent(sessionId)}/search?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Search failed');
      setSearchResults(data.results || []);
      setMessage(data.total ? `Found ${data.total} matching file(s).` : 'No matching files found.');
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
      const results = (data.results || []) as ActionResult[];
      setMessage(`Apply completed: ${results.filter(result => result.status === 'copied').length} copied.`);
      setSelected(new Set());
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
      const results = (data.results || []) as ActionResult[];
      setMessage(`Undo completed: ${results.filter(result => result.status === 'removed').length} removed.`);
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Undo failed'); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    void Promise.resolve().then(loadSessions);
    void Promise.resolve().then(loadBackups);
  }, [loadBackups, loadSessions]);

  useEffect(() => {
    if (!sessionId || ['completed', 'completed_with_errors', 'failed', 'scanned'].includes(status?.state || '')) return;
    void Promise.resolve().then(loadStatus);
    const timer = window.setInterval(() => void loadStatus(), 3000);
    return () => window.clearInterval(timer);
  }, [loadStatus, sessionId, status?.state]);

  function toggle(path: string) {
    const next = new Set(selected);
    if (next.has(path)) next.delete(path);
    else next.add(path);
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

      <Card>
        <CardHeader><CardTitle>Resume an existing workspace session</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2 items-center">
            <select
              className="flex-1 rounded-md border px-3 py-2 text-sm"
              value=""
              onChange={e => e.target.value && resumeSession(e.target.value)}
            >
              <option value="">Select a previous session…</option>
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id.slice(0, 8)} · {s.state} · {s.files_verified}/{s.files_total} verified
                </option>
              ))}
            </select>
            <Button variant="outline" onClick={loadSessions}>Refresh</Button>
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
              <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={showReviewOnly} onCheckedChange={(v) => setShowReviewOnly(Boolean(v))} />
            Show manual-review items only ({reviewCount})
          </label>
          <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => runStep('scan')} disabled={busy || status?.state === 'running'}>Scan Copy</Button>
                <Button variant="outline" onClick={() => runStep('understand')} disabled={busy || status?.state === 'running'}>Read / OCR</Button>
                <Button onClick={() => runStep('plan')} disabled={busy || status?.state === 'running'}>Build Review Plan</Button>
                <Button variant="outline" onClick={undo} disabled={busy}>Undo Applied Copies</Button>
                <Button variant="outline" onClick={createBackup} disabled={busy}>Backup Workspace</Button>
                <Button variant="outline" onClick={validateOcr} disabled={busy}>Check OCR</Button>
              </div>
              {ocrStatus && <div className="text-xs text-slate-500">OCR: {ocrStatus.available ? 'Myanmar + English ready' : 'Needs attention'} · {ocrStatus.executable}</div>}
              {backupStatus && <div className="text-xs text-slate-500 break-all">Latest backup SHA-256: {backupStatus}</div>}
              {backups.length > 0 && (
                <div className="space-y-2 border-t pt-3">
                  <div className="text-sm font-medium">Backup history</div>
                  {backups.map(backup => {
                    const archiveName = backup.archive.split(/[\\/]/).pop() || backup.archive;
                    return (
                      <div key={backup.archive} className="flex flex-wrap items-center justify-between gap-2 rounded border p-2">
                        <div className="min-w-0">
                          <div className="break-all text-xs font-medium">{archiveName}</div>
                          <div className="break-all text-xs text-slate-500">{backup.created_at || ''}</div>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => verifyBackup(backup.archive)} disabled={busy}>Verify</Button>
                          <Button size="sm" variant="outline" onClick={() => restoreBackup(backup.archive)} disabled={busy}>Restore to Recovery</Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Search working copy</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-3">
                <Input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchWorkingCopy()} placeholder="Filename, folder, OCR/text keyword..." />
                <Input value={extensionFilter} onChange={e => setExtensionFilter(e.target.value)} placeholder="Type, e.g. .pdf" />
                <Input value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} placeholder="Category, e.g. Invoice" />
              </div>
              <div className="mt-2 flex gap-2 items-center">
                <Button onClick={searchWorkingCopy} disabled={busy}>Search</Button>
                <span className="text-xs text-slate-500">Review-only filter uses the same review flag as Safe Workspace.</span>
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

          {ocrResults.length > 0 && (
            <Card>
              <CardHeader><CardTitle>OCR review & correction</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {ocrResults.filter(item => item.extraction_method?.startsWith('ocr') || item.language).slice(0, 20).map(item => (
                  <div key={item.relative_path} className="rounded-md border p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium break-all">{item.relative_path}</span>
                      <Button size="sm" variant="outline" onClick={() => { setEditingOcr(item.relative_path); setOcrDraft(item.corrected_text || item.text_preview || ''); }}>Edit OCR</Button>
                    </div>
                    {editingOcr === item.relative_path ? (
                      <div className="space-y-2">
                        <textarea className="min-h-32 w-full rounded-md border p-2 text-sm" value={ocrDraft} onChange={e => setOcrDraft(e.target.value)} />
                        <div className="flex gap-2">
                          <Button onClick={() => saveOcrCorrection(item.relative_path)} disabled={busy}>Save correction</Button>
                          <Button variant="outline" onClick={() => setEditingOcr(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-600 whitespace-pre-wrap line-clamp-5">{item.corrected_text || item.text_preview || 'No extracted text.'}</p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {proposals.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>3. Review organization proposals</CardTitle>
                  <div className="text-sm text-slate-500">{selectedCount} selected · {reviewCount} need review · showing {visibleProposals.length}</div>
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
                      {visibleProposals.map(p => (
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


function CloudWorkspaceNotice() {
  return (
    <div className="mx-auto max-w-3xl py-8">
      <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-900 px-7 py-8 text-white sm:px-9">
          <div className="mb-4 inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium text-blue-100">LOCAL-ONLY FEATURE</div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Safe Workspace runs on your computer</h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100">Folder import, OCR, file scanning and approval workflows need access to your local files. This cloud website does not have access to your computer's filesystem.</p>
        </div>
        <div className="space-y-4 p-7 sm:p-9">
          <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/70">
            <p className="text-sm font-medium">What you can do here</p>
            <p className="mt-1 text-sm text-muted-foreground">Upload and manage private cloud documents, update their review status, and download them securely.</p>
          </div>
          <a href="/admin/cloud-documents" className="inline-flex h-11 items-center justify-center rounded-xl bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90">Open Cloud Documents <span className="ml-2" aria-hidden="true">→</span></a>
        </div>
      </div>
    </div>
  );
}

export default function WorkspaceReview() {
  if (import.meta.env.PROD) return <CloudWorkspaceNotice />;
  return <LocalWorkspaceReview />;
}
