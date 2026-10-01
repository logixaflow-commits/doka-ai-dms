import { getAccessToken, refreshSession } from './supabaseAuth';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api';

async function authHeaders() {
  let token = getAccessToken();
  if (!token) throw new Error('Authentication required.');
  return { Authorization: `Bearer ${token}` };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let headers = await authHeaders();
  let response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init.headers || {}) },
  });

  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed?.access_token) throw new Error('Session expired.');
    headers = await authHeaders();
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...headers, ...(init.headers || {}) },
    });
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'Doka API request failed.');
  }
  return payload as T;
}

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

export async function listCloudDocuments(limit = 100, offset = 0) {
  return request<{ documents: CloudDocument[] }>(
    `/documents?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`,
  );
}

export async function uploadCloudDocument(file: File) {
  const form = new FormData();
  form.append('file', file);
  return request<{ document: CloudDocument }>('/documents', {
    method: 'POST',
    body: form,
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
  return request<{ document: CloudDocument }>(`/documents/${encodeURIComponent(documentId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
}
