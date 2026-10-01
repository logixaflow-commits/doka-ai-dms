import { getAccessToken, getCurrentUser, getSupabaseApiConfig, refreshSession } from './supabaseAuth';

const BUCKET = 'doka-documents';
const MAX_OBJECT_BYTES = 50 * 1024 * 1024;
const SIGNED_URL_TTL_SECONDS = 300;

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

interface SupabaseContext {
  url: string;
  publishableKey: string;
  accessToken: string;
  userId: string;
}

function encodeStoragePath(path: string) {
  return path.split('/').map((segment) => encodeURIComponent(segment)).join('/');
}

async function getContext(): Promise<SupabaseContext> {
  const user = await getCurrentUser();
  const accessToken = getAccessToken();
  if (!user || !accessToken) throw new Error('Authentication required.');

  const config = getSupabaseApiConfig();
  return { ...config, accessToken, userId: user.id };
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
      typeof payload?.message === 'string' ? payload.message :
      typeof payload?.msg === 'string' ? payload.msg :
      typeof payload?.error_description === 'string' ? payload.error_description :
      typeof payload?.error === 'string' ? payload.error :
      'Supabase document request failed.';
    throw new Error(message);
  }
  return payload as T;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const context = await getContext();

  const send = (accessToken: string) => fetch(`${context.url}${path}`, {
    ...init,
    headers: {
      apikey: context.publishableKey,
      Authorization: `Bearer ${accessToken}`,
      ...(init.headers || {}),
    },
  });

  let response = await send(context.accessToken);
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed?.access_token) throw new Error('Session expired.');
    response = await send(refreshed.access_token);
  }
  return parseResponse<T>(response);
}

async function sha256(file: File) {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function safeFilename(filename: string) {
  const basename = filename.replace(/\\\\/g, '/').split('/').pop() || 'document';
  return basename.replace(/[^\\p{L}\\p{N}._-]+/gu, '_').replace(/^[._-]+|[._-]+$/g, '') || 'document';
}

function documentQuery(values: Record<string, string>) {
  return new URLSearchParams(values).toString();
}

/**
 * Cloud document metadata and bytes use Supabase's user-scoped REST/Storage APIs.
 * RLS and Storage policies enforce ownership; no service-role credential is used.
 * This keeps basic cloud document operations available without a separate Python host.
 */
export async function listCloudDocuments(limit = 100, offset = 0) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 500 || !Number.isInteger(offset) || offset < 0) {
    throw new Error('Invalid document pagination.');
  }
  const query = documentQuery({
    select: '*',
    order: 'created_at.desc',
    limit: String(limit),
    offset: String(offset),
  });
  const documents = await request<CloudDocument[]>(`/rest/v1/doka_documents?${query}`);
  return { documents };
}

export async function uploadCloudDocument(file: File) {
  if (file.size > MAX_OBJECT_BYTES) {
    throw new Error('Document exceeds the 50 MiB storage limit.');
  }

  const context = await getContext();

  const digest = await sha256(file);
  const filename = safeFilename(file.name);
  const objectKey = `users/${context.userId}/documents/${digest}/${filename}`;
  const storagePath = `/storage/v1/object/${BUCKET}/${encodeStoragePath(objectKey)}`;

  const sendUpload = (accessToken: string) => fetch(`${context.url}${storagePath}`, {
    method: 'POST',
    headers: {
      apikey: context.publishableKey,
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': file.type || 'application/octet-stream',
      'x-upsert': 'false',
    },
    body: file,
  });
  let uploadResponse = await sendUpload(context.accessToken);
  if (uploadResponse.status === 401) {
    const refreshed = await refreshSession();
    if (!refreshed?.access_token) throw new Error('Session expired.');
    uploadResponse = await sendUpload(refreshed.access_token);
  }
  await parseResponse<{ Key?: string }>(uploadResponse);

  const row = {
    owner_id: context.userId,
    object_key: objectKey,
    filename,
    content_type: file.type || 'application/octet-stream',
    size_bytes: file.size,
    sha256: digest,
    status: 'active',
    metadata: {},
  };

  try {
    const inserted = await request<CloudDocument[]>(
      `/rest/v1/doka_documents?${documentQuery({ select: '*' })}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Prefer: 'return=representation',
        },
        body: JSON.stringify(row),
      },
    );
    if (!inserted[0]) throw new Error('Document metadata was not returned after upload.');
    return { document: inserted[0] };
  } catch (error) {
    // Compensate only for the object this upload just created; never mask the
    // metadata error if Storage cleanup itself fails.
    try {
      await request(`/storage/v1/object/${BUCKET}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prefixes: [objectKey] }),
      });
    } catch {
      // A later orphan-cleanup job can reconcile this rare failure.
    }
    throw error;
  }
}

export async function getCloudDocumentDownloadUrl(documentId: string) {
  const query = documentQuery({ id: `eq.${documentId}`, select: 'id,object_key,sha256', limit: '1' });
  const documents = await request<Pick<CloudDocument, 'id' | 'object_key' | 'sha256'>[]>(
    `/rest/v1/doka_documents?${query}`,
  );
  const document = documents[0];
  if (!document) throw new Error('Document not found.');

  const signed = await request<{ signedURL?: string; signedUrl?: string }>(
    `/storage/v1/object/sign/${BUCKET}/${encodeStoragePath(document.object_key)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expiresIn: SIGNED_URL_TTL_SECONDS }),
    },
  );
  const signedPath = signed.signedURL || signed.signedUrl;
  if (!signedPath) throw new Error('Supabase did not return a signed download URL.');

  const { url } = getSupabaseApiConfig();
  const downloadUrl = signedPath.startsWith('http')
    ? signedPath
    : `${url}/storage/v1${signedPath.startsWith('/') ? signedPath : `/${signedPath}`}`;

  return { url: downloadUrl, sha256: document.sha256, expires_seconds: SIGNED_URL_TTL_SECONDS };
}

export async function updateCloudDocument(
  documentId: string,
  update: { status?: CloudDocument['status']; metadata?: Record<string, unknown> },
) {
  if (update.status === undefined && update.metadata === undefined) {
    throw new Error('No document fields were provided for update.');
  }
  const query = documentQuery({ id: `eq.${documentId}`, select: '*' });
  const rows = await request<CloudDocument[]>(`/rest/v1/doka_documents?${query}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Prefer: 'return=representation',
    },
    body: JSON.stringify(update),
  });
  if (!rows[0]) throw new Error('Document not found or no permitted fields were updated.');
  return { document: rows[0] };
}
