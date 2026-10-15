import { getAccessToken, getCurrentUser, refreshSession } from './supabaseAuth';

// Keep local Vite development on the local API proxy. Production uses the
// verified Cloudflare Worker unless an environment-specific origin overrides it.
const defaultApiBase = import.meta.env.DEV ? '' : 'https://doka-ai-dms.logixaflow.workers.dev';
const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || defaultApiBase).trim();
export const CLOUD_API_ORIGIN = configuredApiBase.endsWith('/')
  ? configuredApiBase.slice(0, -1)
  : configuredApiBase;
const API_ROOT = `${CLOUD_API_ORIGIN}/api`;
const MAX_UPLOAD_BYTES = Number(import.meta.env.VITE_DOKA_MAX_UPLOAD_BYTES || 5 * 1024 * 1024 * 1024);

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
  deleted_at: string | null;
  folder_path: string;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const raw = await response.text();
  let payload: Record<string, unknown> = {};
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
export interface CloudDocumentFilters {
  limit?: number;
  offset?: number;
  search?: string;
  status?: CloudDocument['status'];
  trash?: boolean;
  folderPath?: string;
}

export async function listCloudDocuments(filters: CloudDocumentFilters = {}) {
  const { limit = 100, offset = 0, search, status, trash = false, folderPath } = filters;
  if (!Number.isInteger(limit) || limit < 1 || limit > 500 || !Number.isInteger(offset) || offset < 0) {
    throw new Error('Invalid document pagination.');
  }
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset), trash: String(trash) });
  if (search?.trim()) query.set('search', search.trim());
  if (status) query.set('status', status);
  if (folderPath !== undefined) query.set('folder_path', folderPath);
  return request<{ documents: CloudDocument[] }>(`/documents?${query.toString()}`);
}

export interface StorageUploadSession {
  session_id: string;
  provider: 'supabase' | 'b2' | 'cloudinary' | 'mock';
  object_key: string;
  expires_at: number;
  upload: {
    method: string;
    url: string;
    headers: Record<string, string>;
    fields: Record<string, string>;
  };
  warnings: string[];
}

async function sha256Hex(file: File): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error('Browser cryptography is unavailable; cannot verify the upload fingerprint.');
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

async function directStorageUpload(session: StorageUploadSession, file: File): Promise<Record<string, unknown>> {
  if (session.provider === 'cloudinary') {
    const body = new FormData();
    Object.entries(session.upload.fields).forEach(([key, value]) => body.append(key, value));
    body.append('file', file);
    const response = await fetch(session.upload.url, { method: session.upload.method || 'POST', body });
    const raw = await response.text();
    if (!response.ok) throw new Error(`Cloudinary upload failed (${response.status}).`);
    try { return JSON.parse(raw) as Record<string, unknown>; } catch { return {}; }
  }

  const response = await fetch(session.upload.url, {
    method: session.upload.method || 'PUT',
    headers: session.upload.headers,
    body: file,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(detail || `Direct ${session.provider} upload failed (${response.status}).`);
  }
  return {};
}

async function createDirectStorageUpload(
  file: File,
  artifactType: 'source' | 'preview' | 'thumbnail' | 'cover' = 'source',
  documentId?: string,
) {
  if (file.size <= 0 || file.size > MAX_UPLOAD_BYTES) {
    throw new Error(`This file exceeds the configured upload limit of ${Math.round(MAX_UPLOAD_BYTES / (1024 * 1024))} MiB.`);
  }
  const sha256 = await sha256Hex(file);
  const session = await request<StorageUploadSession>('/storage/upload-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
      sha256,
      artifact_type: artifactType,
      ...(documentId ? { document_id: documentId } : {}),
    }),
  });
  const providerResult = await directStorageUpload(session, file);
  const completed = await request<{ document?: CloudDocument; stored?: Record<string, unknown>; warnings: string[] }>('/storage/upload-complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: session.session_id,
      size_bytes: file.size,
      sha256,
      provider_result: providerResult,
    }),
  });
  return {
    ...completed,
    warnings: [...(session.warnings || []), ...(completed.warnings || [])],
  };
}

export async function uploadCloudDocument(file: File) {
  return createDirectStorageUpload(file, 'source') as Promise<{ document: CloudDocument; warnings: string[] }>;
}

export async function exportCloudDocumentToGoogleDrive(documentId: string) {
  const session = await request<{
    session_id: string;
    provider: 'google_drive';
    source_document: { id: string; size_bytes: number; sha256: string; download_url: string };
    upload: { method: string; url: string; headers: Record<string, string>; fields: Record<string, string> };
  }>(`/documents/${encodeURIComponent(documentId)}/export/google-drive/upload-session`);

  const source = await fetch(session.source_document.download_url);
  if (!source.ok || !source.body) throw new Error('Unable to read the source document for Google Drive export.');

  const reader = source.body.getReader();
  const chunkSize = 8 * 1024 * 1024;
  let pending = new Uint8Array(0);
  let offset = 0;
  let driveFileId = '';
  let finalPayload: Record<string, unknown> = {};

  const sendChunk = async (chunk: Uint8Array, start: number, total: number) => {
    const end = start + chunk.byteLength - 1;
    const response = await fetch(session.upload.url, {
      method: 'PUT',
      headers: {
        ...session.upload.headers,
        'Content-Length': String(chunk.byteLength),
        'Content-Range': `bytes ${start}-${end}/${total}`,
      },
      body: new Uint8Array(chunk).buffer,
    });
    if (response.status !== 200 && response.status !== 201 && response.status !== 308) {
      throw new Error(`Google Drive upload failed (${response.status}).`);
    }
    if (response.status === 200 || response.status === 201) {
      finalPayload = await response.json().catch(() => ({}));
      driveFileId = typeof finalPayload.id === 'string' ? finalPayload.id : '';
    }
  };

  const append = async (incoming: Uint8Array) => {
    const merged = new Uint8Array(pending.byteLength + incoming.byteLength);
    merged.set(pending);
    merged.set(incoming, pending.byteLength);
    pending = merged;
    while (pending.byteLength >= chunkSize) {
      const chunk = pending.slice(0, chunkSize);
      pending = pending.slice(chunkSize);
      await sendChunk(chunk, offset, session.source_document.size_bytes);
      offset += chunk.byteLength;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    await append(value);
  }
  if (pending.byteLength > 0) {
    await sendChunk(pending, offset, session.source_document.size_bytes);
    offset += pending.byteLength;
  }
  if (offset !== session.source_document.size_bytes || !driveFileId) {
    throw new Error('Google Drive did not report a completed file.');
  }

  return request<{ document: CloudDocument }>(`/documents/${encodeURIComponent(documentId)}/export/google-drive/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: session.session_id,
      file_id: driveFileId,
      size_bytes: session.source_document.size_bytes,
      sha256: session.source_document.sha256,
    }),
  });
}


export async function getCloudDocumentDownloadUrl(documentId: string) {
  return request<{ url: string; sha256: string; expires_seconds: number }>(
    `/documents/${encodeURIComponent(documentId)}/download`,
  );
}

export async function updateCloudDocument(
  documentId: string,
  update: { status?: CloudDocument['status']; metadata?: Record<string, unknown>; filename?: string; folder_path?: string },
) {
  if (update.status === undefined && update.metadata === undefined && update.filename === undefined && update.folder_path === undefined) {
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


export async function trashCloudDocument(documentId: string) {
  return request<{ document: CloudDocument }>(`/documents/${encodeURIComponent(documentId)}`, { method: 'DELETE' });
}

export async function restoreCloudDocument(documentId: string) {
  return request<{ document: CloudDocument }>(`/documents/${encodeURIComponent(documentId)}/restore`, { method: 'POST' });
}

export async function renameCloudDocument(documentId: string, filename: string) {
  const normalized = filename.trim();
  if (!normalized || normalized.length > 255 || normalized.includes('/') || normalized.includes('\\') || normalized.includes('\0')) {
    throw new Error('Enter a valid file name (maximum 255 characters).');
  }
  return updateCloudDocument(documentId, { filename: normalized });
}


export async function moveCloudDocument(documentId: string, folderPath: string) {
  const normalized = folderPath.trim() || '/';
  const segments = normalized.split('/').filter(Boolean);
  if (normalized.includes('\\') || normalized.includes('\0') || segments.some(part => part === '.' || part === '..')) {
    throw new Error('Enter a valid folder path.');
  }
  return updateCloudDocument(documentId, { folder_path: normalized === '/' ? '/' : `/${segments.join('/')}` });
}


export interface CloudAuditEvent {
  id: string;
  document_id: string | null;
  action: 'upload' | 'download' | 'preview' | 'update' | 'trash' | 'restore' | 'permanent_delete' | 'version_create' | 'version_restore' | 'export' | 'backup';
  filename: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export async function listCloudAuditEvents(limit = 100) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 500) throw new Error('Invalid audit pagination.');
  return request<{ events: CloudAuditEvent[] }>(`/audit?limit=${limit}`);
}

export async function permanentlyDeleteCloudDocument(documentId: string) {
  return request<{ deleted: boolean; document_id: string; objects_deleted: number }>(
    `/documents/${encodeURIComponent(documentId)}/permanent`,
    { method: 'DELETE' },
  );
}

export async function getCloudDocumentPreviewUrl(documentId: string) {
  return request<{ url: string; sha256: string; expires_seconds: number }>(
    `/documents/${encodeURIComponent(documentId)}/preview`,
  );
}


export async function bulkUpdateCloudDocuments(
  documentIds: string[],
  action: 'status' | 'trash',
  status?: CloudDocument['status'],
) {
  if (!documentIds.length || documentIds.length > 100 || new Set(documentIds).size !== documentIds.length) {
    throw new Error('Select between 1 and 100 unique documents.');
  }
  if (action === 'status' && !status) throw new Error('Choose a status for the selected documents.');
  return request<{ documents: CloudDocument[]; updated_count: number }>('/documents/bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds, action, status: action === 'status' ? status : null }),
  });
}


export async function listCloudFolders() {
  return request<{ folders: string[] }>('/folders');
}

export interface CloudDocumentVersion {
  id: string;
  document_id: string;
  version_no: number;
  filename: string | null;
  content_type: string | null;
  size_bytes: number;
  sha256: string;
  created_at: string;
}

export async function listCloudDocumentVersions(documentId: string) {
  return request<{ versions: CloudDocumentVersion[] }>(
    `/documents/${encodeURIComponent(documentId)}/versions`,
  );
}

export async function createCloudDocumentVersion(documentId: string, file: File) {
  if (!(file instanceof File)) throw new Error('A file is required.');
  return createDirectStorageUpload(file, 'source', documentId) as Promise<{ document: CloudDocument; warnings: string[] }>;
}

export async function restoreCloudDocumentVersion(documentId: string, versionId: string) {
  return request<{ document: CloudDocument }>(
    `/documents/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(versionId)}/restore`,
    { method: 'POST' },
  );
}
