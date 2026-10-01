import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ThemeToggle } from '@/components/ThemeToggle';
import { isSupabaseConfigured, signIn, signUp } from '@/lib/supabaseAuth';

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      if (!isSupabaseConfigured()) {
        throw new Error('Supabase Auth is not configured. Add the Supabase environment variables in Vercel.');
      }

      if (mode === 'login') {
        await signIn(email.trim(), password);
        onLogin();
      } else {
        const session = await signUp(email.trim(), password);
        if (session.access_token) {
          onLogin();
        } else {
          setMessage('Account created. Check your email to confirm the account, then sign in.');
          setMode('login');
        }
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex justify-between items-center mb-2">
            <CardTitle className="text-2xl dark:text-slate-100">Doka Login</CardTitle>
            <ThemeToggle />
          </div>
          <p className="text-center text-slate-500 dark:text-slate-400 text-sm">
            Secure document workspace
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            {message && (
              <div className="text-sm bg-slate-100 dark:bg-slate-800 p-3 rounded-md">
                {message}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
            </Button>
            <button
              type="button"
              className="w-full text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
              onClick={() => {
                setMode(mode === 'login' ? 'signup' : 'login');
                setMessage('');
              }}
            >
              {mode === 'login' ? 'Need an account? Create one' : 'Already have an account? Sign in'}
            </button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
