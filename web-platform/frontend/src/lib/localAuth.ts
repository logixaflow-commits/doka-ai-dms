import { isSupabaseConfigured, type SupabaseUser } from '@/lib/supabaseAuth';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'supabase_user';

type LocalSession = { access_token: string; refresh_token: string; token_type: 'bearer' };
type LocalIdentity = { username: string; role: string };

export function isLocalAuthEnabled() {
  return import.meta.env.DEV && !isSupabaseConfigured();
}

async function readError(response: Response) {
  const payload = await response.json().catch(() => ({}));
  return typeof payload?.detail === 'string' ? payload.detail : 'Local authentication failed.';
}

export async function signInLocal(username: string, password: string) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error(await readError(response));
  const session = await response.json() as LocalSession;
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  const user = await getLocalCurrentUser();
  if (!user) throw new Error('Local login succeeded but the session could not be verified.');
  return user;
}

async function refreshLocalSession() {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    clearLocalSession();
    return false;
  }
  const session = await response.json() as LocalSession;
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  return true;
}

function clearLocalSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function getLocalCurrentUser(): Promise<SupabaseUser | null> {
  let accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (!accessToken) return null;

  let response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    if (!await refreshLocalSession()) return null;
    accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!accessToken) return null;
    response = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  }
  if (!response.ok) {
    clearLocalSession();
    return null;
  }

  const identity = await response.json() as LocalIdentity;
  const user: SupabaseUser = {
    id: `local:${identity.username}`,
    username: identity.username,
    role: identity.role,
  };
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}
