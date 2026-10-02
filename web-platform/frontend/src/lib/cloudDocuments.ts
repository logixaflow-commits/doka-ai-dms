import { getAccessToken, getCurrentUser, refreshSession } from './supabaseAuth';

// Keep local Vite development on the local API proxy. Production uses the
// verified Cloudflare Worker unless an environment-specific origin overrides it.
const defaultApiBase = import.meta.env.DEV ? '' : 'https://doka.logixaflow.workers.dev';
const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || defaultApiBase).trim();
const API_BASE_URL = configuredApiBase.endsWith('/')
  ? configuredApiBase.slice(0, -1)
  : configuredApiBase;
const API_ROOT = `${API_BASE_URL}/api`;

export interface CloudDocument {
  id: string;
  object_key: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  status: 'active' | 'review' | 'quarantined' | 'archived';
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const raw = await response.text();
  let payload: any = {};
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = { message: raw };
    }
  }

  if (!response.ok) {
    const message =
      typeof payload?.detail === 'string' ? payload.detail :
      typeof payload?.message === 'string' ? payload.message :
      typeof payload?.msg === 'string' ? payload.msg :
      typeof payload?.error_description === 'string' ? payload.error_description :
      typeof payload?.error === 'string' ? payload.error :
      `Doka API request failed (${response.status}).`;
    throw new Error(message);
  }
  return payload as T;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let accessToken = getAccessToken();
  if (!accessToken) {
    await getCurrentUser();
    accessToken = getAccessToken();
  }
  if (!accessToken) throw new Error('Authentication required. Please sign in again.');

  const send = (token: string) => fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });

  let response = await send(accessToken);
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed?.access_token) throw new Error('Session expired. Please sign in again.');
    response = await send(refreshed.access_token);
  }
  return parseResponse<T>(response);
}

/** Cloud document operations go through the authenticated FastAPI cloud API.
 * Supabase Auth access tokens are forwarded; RLS and Storage policies remain
 * the final ownership boundary. No service-role credential reaches the browser.
 */
export async function listCloudDocuments(limit = 100, offset = 0) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 500 || !Number.isInteger(offset) || offset < 0) {
    throw new Error('Invalid document pagination.');
  }
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return request<{ documents: CloudDocument[] }>(`/documents?${query.toString()}`);
}

export async function uploadCloudDocument(file: File) {
  const body = new FormData();
  body.append('file', file);
  return request<{ document: CloudDocument }>('/documents', {
    method: 'POST',
    body,
  });
}

export async function getCloudDocumentDownloadUrl(documentId: string) {
  return request<{ url: string; sha256: string; expires_seconds: number }>(
    `/documents/${encodeURIComponent(documentId)}/download`,
  );
}

export async function updateCloudDocument(
  documentId: string,
  update: { status?: CloudDocument['status']; metadata?: Record<string, unknown> },
) {
  if (update.status === undefined && update.metadata === undefined) {
    throw new Error('No document fields were provided for update.');
  }
  return request<{ document: CloudDocument }>(
    `/documents/${encodeURIComponent(documentId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(update),
    },
  );
}
