import { Link } from 'react-router';
import { ArrowRight, Palette, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ThemeToggle } from '@/components/ThemeToggle';

export default function SettingsPage() {
  return (
    <div className="doka-dashboard">
      <section>
        <p className="doka-eyebrow text-muted-foreground">Workspace preferences</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Manage appearance and review the services used by this private workspace.</p>
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="doka-panel h-full border-0 shadow-none">
          <CardHeader><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-300"><Palette className="h-5 w-5" /></span><div><CardTitle>Appearance</CardTitle><CardDescription>Choose a comfortable display theme.</CardDescription></div></div></CardHeader>
          <CardContent className="flex items-center justify-between gap-4"><div><p className="text-sm font-medium">Color theme</p><p className="mt-1 text-xs text-muted-foreground">System, light or dark mode.</p></div><ThemeToggle /></CardContent>
        </Card>
        <Card className="doka-panel h-full border-0 shadow-none">
          <CardHeader><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"><ShieldCheck className="h-5 w-5" /></span><div><CardTitle>Account security</CardTitle><CardDescription>Private access is enforced by your signed-in session.</CardDescription></div></div></CardHeader>
          <CardContent><p className="text-sm text-muted-foreground">Cloud documents remain scoped to the authenticated account. Provider credentials must be stored server-side, never in this browser.</p></CardContent>
        </Card>
        <Card className="doka-panel h-full border-0 shadow-none lg:col-span-2">
          <CardHeader><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-300"><SlidersHorizontal className="h-5 w-5" /></span><div><CardTitle>Connected services</CardTitle><CardDescription>Review the services used by Doka and their verification status.</CardDescription></div></div></CardHeader>
          <CardContent><Link to="/admin/settings/integrations" className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Open Connections Center <ArrowRight className="h-4 w-4" /></Link></CardContent>
        </Card>
      </div>
    </div>
  );
}
