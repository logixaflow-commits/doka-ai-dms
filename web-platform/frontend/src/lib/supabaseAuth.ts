const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

const ACCESS_TOKEN_KEY = 'doka_cloud_access_token';
const REFRESH_TOKEN_KEY = 'doka_cloud_refresh_token';
const USER_KEY = 'doka_cloud_user';

export interface SupabaseUser {
  id: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
  username?: string;
  role?: string;
}

interface AuthSession {
  access_token: string;
  refresh_token: string;
  user?: SupabaseUser;
}

function assertConfigured() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error('Supabase Auth is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.');
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  assertConfigured();
  const response = await fetch(`${SUPABASE_URL}/auth/v1${path}`, {
    ...init,
    headers: {
      apikey: SUPABASE_KEY,
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      typeof payload?.msg === 'string' ? payload.msg :
      typeof payload?.message === 'string' ? payload.message :
      typeof payload?.error_description === 'string' ? payload.error_description :
      'Authentication request failed';
    throw new Error(message);
  }
  return payload as T;
}

function saveSession(session: AuthSession) {
  localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  if (session.user) {
    localStorage.setItem(USER_KEY, JSON.stringify(session.user));
  }
}

function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isSupabaseConfigured() {
  if (!SUPABASE_URL || !SUPABASE_KEY) return false;
  const placeholders = ['your-project-ref', 'your_public_key'];
  return !placeholders.some(value => SUPABASE_URL.includes(value) || SUPABASE_KEY.includes(value));
}

export function getSupabaseApiConfig() {
  assertConfigured();
  return { url: SUPABASE_URL!, publishableKey: SUPABASE_KEY! };
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredUser(): SupabaseUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SupabaseUser;
  } catch {
    return null;
  }
}

export async function signIn(email: string, password: string) {
  const session = await request<AuthSession>('/token?grant_type=password', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  saveSession(session);
  return session;
}

export async function signUp(email: string, password: string) {
  const session = await request<AuthSession>('/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (session.access_token && session.refresh_token) {
    saveSession(session);
  }
  return session;
}

export async function refreshSession() {
  const refresh_token = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refresh_token) return null;

  try {
    const session = await request<AuthSession>('/token?grant_type=refresh_token', {
      method: 'POST',
      body: JSON.stringify({ refresh_token }),
    });
    saveSession(session);
    return session;
  } catch {
    clearSession();
    return null;
  }
}

export async function getCurrentUser() {
  const accessToken = getAccessToken();
  if (!accessToken) return null;

  try {
    const user = await request<SupabaseUser>('/user', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  } catch {
    const refreshed = await refreshSession();
    if (!refreshed?.access_token) return null;

    try {
      const user = await request<SupabaseUser>('/user', {
        headers: { Authorization: `Bearer ${refreshed.access_token}` },
      });
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return user;
    } catch {
      clearSession();
      return null;
    }
  }
}

export async function signOut() {
  const accessToken = getAccessToken();
  if (accessToken && isSupabaseConfigured()) {
    await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_KEY!,
        Authorization: `Bearer ${accessToken}`,
      },
    }).catch(() => undefined);
  }
  clearSession();
}
