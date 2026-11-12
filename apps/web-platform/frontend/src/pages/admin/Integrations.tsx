import { AlertCircle, Cloud, Github, MessageCircle, ShieldCheck } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const services = [
  { name: 'Doka Cloud API', detail: 'Document metadata, private storage and account-scoped API access.', icon: Cloud, state: 'Core service' },
  { name: 'Supabase', detail: 'Authentication and private document metadata storage.', icon: ShieldCheck, state: 'Core service' },
  { name: 'Telegram', detail: 'Notifications are restricted to the configured group and topic. End-to-end delivery is not verified by this page.', icon: MessageCircle, state: 'Delivery unverified' },
  { name: 'GitHub', detail: 'Repository and development automation are managed through the authorized GitHub connection.', icon: Github, state: 'Assistant-managed' },
];

export default function IntegrationsPage() {
  return (
    <div className="doka-dashboard">
      <section>
        <p className="doka-eyebrow text-muted-foreground">Settings / Connections</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Connections Center</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Review the services used by Doka. A service is only shown as connected after its authorization and health can be verified.</p>
      </section>
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Connection controls are not enabled yet</AlertTitle>
        <AlertDescription>The current production API does not expose secure provider authorization, disconnect or enable/disable endpoints. This page will not show fake Connect switches or ask you to paste secrets into the browser. OAuth consent and server-side credential storage must be implemented before those controls can be safely enabled.</AlertDescription>
      </Alert>
      <section className="grid gap-4 md:grid-cols-2">
        {services.map(service => (
          <Card key={service.name} className="doka-panel h-full border-0 shadow-none">
            <CardHeader><div className="flex items-start justify-between gap-3"><div className="flex min-w-0 items-center gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted text-foreground"><service.icon className="h-5 w-5" /></span><div className="min-w-0"><CardTitle className="text-base">{service.name}</CardTitle><CardDescription className="mt-1">{service.detail}</CardDescription></div></div><Badge variant="outline" className="shrink-0">{service.state}</Badge></div></CardHeader>
            <CardContent><p className="text-xs leading-5 text-muted-foreground">No credential values are displayed or stored on this page.</p></CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
