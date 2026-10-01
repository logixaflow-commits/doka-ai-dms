import { useEffect, useState } from 'react';
import { CloudUpload, Download, RefreshCw, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  getCloudDocumentDownloadUrl,
  listCloudDocuments,
  updateCloudDocument,
  uploadCloudDocument,
  type CloudDocument,
} from '@/lib/cloudDocuments';

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function CloudDocuments() {
  const [documents, setDocuments] = useState<CloudDocument[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const result = await listCloudDocuments(100, 0);
      setDocuments(result.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cloud documents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function upload() {
    if (!file) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await uploadCloudDocument(file);
      setDocuments((current) => [result.document, ...current.filter((item) => item.id !== result.document.id)]);
      setFile(null);
      const input = document.getElementById('doka-cloud-file') as HTMLInputElement | null;
      if (input) input.value = '';
      setMessage(`Uploaded ${result.document.filename}; its SHA-256 fingerprint was calculated and stored.`);
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
    try {
      const result = await updateCloudDocument(item.id, { status });
      setDocuments((current) => current.map((row) => row.id === item.id ? result.document : row));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update document status.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Cloud Documents</h1>
        <p className="text-sm text-slate-500">Private Supabase Storage with account-scoped document access.</p>
      </div>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><CloudUpload className="h-5 w-5" />Upload a document</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <input
            id="doka-cloud-file"
            type="file"
            className="block w-full text-sm"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            disabled={busy}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={upload} disabled={!file || busy}>
              <CloudUpload className="mr-2 h-4 w-4" />{busy ? 'Working…' : 'Upload securely'}
            </Button>
            {file && <span className="text-sm text-slate-500">{file.name} · {formatSize(file.size)}</span>}
          </div>
          <p className="text-xs text-slate-500">Maximum 50 MiB per file. Files are private and scoped to your signed-in account. SHA-256 is calculated before upload.</p>
        </CardContent>
      </Card>

      {error && <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {message && <div role="status" className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">{message}</div>}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>Stored documents ({documents.length})</CardTitle>
            <Button variant="outline" size="sm" onClick={() => void refresh()} disabled={loading || busy}>
              <RefreshCw className="mr-2 h-4 w-4" />Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? <p className="py-8 text-center text-sm text-slate-500">Loading documents…</p> :
            documents.length === 0 ? <div className="py-8 text-center text-sm text-slate-500"><FileText className="mx-auto mb-2 h-8 w-8 opacity-40" />No cloud documents yet.</div> :
              <div className="space-y-3">
                {documents.map((item) => (
                  <div key={item.id} className="flex flex-col gap-3 rounded-lg border p-4 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="break-all font-medium">{item.filename}</span>
                        <Badge variant="outline">{item.status}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{formatSize(item.size_bytes)} · {item.content_type} · {formatDate(item.created_at)}</p>
                      <p className="mt-1 break-all font-mono text-[11px] text-slate-400">SHA-256: {item.sha256}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <select
                        aria-label={`Status for ${item.filename}`}
                        className="rounded-md border bg-background px-2 py-2 text-sm"
                        value={item.status}
                        disabled={busy}
                        onChange={(event) => void changeStatus(item, event.target.value as CloudDocument['status'])}
                      >
                        <option value="active">Active</option>
                        <option value="review">Review</option>
                        <option value="quarantined">Quarantined</option>
                        <option value="archived">Archived</option>
                      </select>
                      <Button size="sm" variant="outline" onClick={() => void download(item)} disabled={busy}>
                        <Download className="mr-2 h-4 w-4" />Download
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
          }
        </CardContent>
      </Card>

      <p className="text-xs text-slate-500">Cloud file storage and metadata work directly through Supabase Auth, Storage, PostgREST and RLS. Local OCR, text extraction and workspace processing still require the local Python runtime or a separately selected API host.</p>
    </div>
  );
}
