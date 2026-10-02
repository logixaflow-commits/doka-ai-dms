import { useState } from 'react';
import { ArrowRight, FileCheck2, FolderLock, ShieldCheck, Sparkles } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
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
  const configured = isSupabaseConfigured();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      if (!configured) throw new Error('Supabase Auth is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to the Vercel project, then redeploy.');
      if (mode === 'login') {
        await signIn(email.trim(), password);
        onLogin();
      } else {
        const session = await signUp(email.trim(), password);
        if (session.access_token) onLogin();
        else {
          setMessage('Account created. Check your email to confirm your account, then sign in.');
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
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#f5f7fb] p-4 dark:bg-slate-950 sm:p-6">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-blue-200/40 blur-3xl dark:bg-blue-900/20" />
      <div className="pointer-events-none absolute -bottom-40 -right-24 h-[28rem] w-[28rem] rounded-full bg-violet-200/40 blur-3xl dark:bg-violet-900/20" />
      <div className="absolute right-5 top-5 z-10"><ThemeToggle /></div>
      <div className="relative z-10 grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-slate-200/80 bg-white shadow-[0_30px_100px_-45px_rgba(15,23,42,.35)] dark:border-slate-800 dark:bg-slate-900 lg:min-h-[640px] lg:grid-cols-[1.05fr_.95fr]">
        <section className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-[#101b31] via-[#17345b] to-[#24527d] p-10 text-white lg:flex">
          <div className="pointer-events-none absolute -right-28 top-10 h-80 w-80 rounded-full border-[48px] border-white/[0.045]" />
          <div className="pointer-events-none absolute -bottom-36 -left-24 h-96 w-96 rounded-full border-[56px] border-cyan-200/[0.06]" />
          <div className="relative z-10 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-200 to-blue-400 text-xl font-black text-slate-950 shadow-lg">D</div>
            <div><p className="text-xl font-semibold tracking-tight">Doka</p><p className="text-[10px] font-semibold uppercase tracking-[.2em] text-blue-200">Document workspace</p></div>
          </div>
          <div className="relative z-10 max-w-md py-10">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs text-cyan-100"><Sparkles className="h-3.5 w-3.5" /> A calmer way to manage files</div>
            <h1 className="text-4xl font-semibold leading-[1.15] tracking-tight">Your documents.<br />Organized and protected.</h1>
            <p className="mt-5 text-sm leading-7 text-blue-100">A private place for the files that matter. Keep your documents together, find them when you need them, and stay in control of your workspace.</p>
            <div className="mt-9 space-y-4">
              <div className="flex items-center gap-3 text-sm text-blue-50"><span className="rounded-xl bg-white/10 p-2.5"><FolderLock className="h-4 w-4 text-cyan-200" /></span> Private, account-scoped document storage</div>
              <div className="flex items-center gap-3 text-sm text-blue-50"><span className="rounded-xl bg-white/10 p-2.5"><ShieldCheck className="h-4 w-4 text-emerald-200" /></span> Secure access with your account</div>
              <div className="flex items-center gap-3 text-sm text-blue-50"><span className="rounded-xl bg-white/10 p-2.5"><FileCheck2 className="h-4 w-4 text-violet-200" /></span> SHA-256 integrity fingerprints</div>
            </div>
          </div>
          <p className="relative z-10 text-xs text-blue-200/70">Your workspace, ready when you are.</p>
        </section>

        <section className="flex items-center justify-center p-6 sm:p-10 lg:p-12">
          <div className="w-full max-w-sm">
            <div className="mb-9 flex items-center gap-3 lg:hidden">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-200 to-blue-500 text-lg font-black text-slate-950">D</div>
              <div><p className="text-lg font-semibold tracking-tight">Doka</p><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-muted-foreground">Document workspace</p></div>
            </div>
            <div className="mb-8">
              <p className="text-xs font-semibold uppercase tracking-[.18em] text-primary">{mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">{mode === 'login' ? 'Sign in to Doka' : 'Create your account'}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{mode === 'login' ? 'Enter your details to access your private document library.' : 'Create an account to start your private document library.'}</p>
            </div>
            <Card className="border-0 shadow-none">
              <CardContent className="p-0">
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-2"><Label htmlFor="email">Email address</Label><Input id="email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" required className="h-12 rounded-xl bg-background px-4" /></div>
                  <div className="space-y-2"><div className="flex items-center justify-between"><Label htmlFor="password">Password</Label><span className="text-[11px] text-muted-foreground">At least 8 characters</span></div><Input id="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={8} value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter your password" required className="h-12 rounded-xl bg-background px-4" /></div>
                  {message && <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-5 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">{message}</div>}
                  <Button type="submit" className="h-12 w-full rounded-xl text-sm font-semibold shadow-md shadow-primary/15" disabled={loading || !configured}>{loading ? 'Please wait…' : mode === 'login' ? 'Sign in securely' : 'Create account'}<ArrowRight className="ml-2 h-4 w-4" /></Button>
                  {!configured && <p className="text-xs leading-5 text-rose-600">Authentication configuration is missing. Contact the administrator.</p>}
                  <p className="text-center text-sm text-muted-foreground">{mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}<button type="button" className="font-semibold text-primary hover:underline" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setMessage(''); }}>{mode === 'login' ? 'Create one' : 'Sign in'}</button></p>
                </form>
              </CardContent>
            </Card>
            <div className="mt-8 flex items-center justify-center gap-2 text-[11px] text-muted-foreground"><ShieldCheck className="h-3.5 w-3.5" /> Your documents are private to your account</div>
          </div>
        </section>
      </div>
    </main>
  );
}
