import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Settings as SettingsIcon,
  Mail,
  Shield,
  Bell,
  HardDrive,
  Brain,
  Save,
  RefreshCw
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

const API_BASE = '/api';

interface SystemConfig {
  environment: string;
  debug: boolean;
  max_file_size: number;
  allowed_extensions: string[];
  ocr_enabled: boolean;
  ai_enabled: boolean;
  duplicate_detection: boolean;
  email_enabled: boolean;
  auto_approve_threshold: number;
  review_threshold: number;
}

interface EmailConfig {
  smtp_enabled: boolean;
  smtp_server: string;
  smtp_port: number;
  smtp_username: string;
  smtp_from_email: string;
  admin_email: string;
}

interface StorageConfig {
  minio_endpoint: string;
  minio_bucket: string;
  storage_path: string;
}

function getToken() {
  return localStorage.getItem('access_token');
}

async function apiFetch(url: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  const [systemConfig, setSystemConfig] = useState<SystemConfig>({
    environment: 'development',
    debug: true,
    max_file_size: 100,
    allowed_extensions: ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
    ocr_enabled: true,
    ai_enabled: false,
    duplicate_detection: true,
    email_enabled: false,
    auto_approve_threshold: 0.85,
    review_threshold: 0.70,
  });

  const [emailConfig, setEmailConfig] = useState<EmailConfig>({
    smtp_enabled: false,
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_username: '',
    smtp_from_email: '',
    admin_email: '',
  });

  const [storageConfig, setStorageConfig] = useState<StorageConfig>({
    minio_endpoint: 'localhost:9000',
    minio_bucket: 'logistics-documents',
    storage_path: '/data/documents',
  });

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const response = await apiFetch(`${API_BASE}/admin/settings`);
      if (response.ok) {
        const data = await response.json();
        if (data.system) setSystemConfig(data.system);
        if (data.email) setEmailConfig(data.email);
        if (data.storage) setStorageConfig(data.storage);
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    } finally {
      setLoading(false);
    }
  }

  async function saveSettings() {
    setSaving(true);
    setMessage(null);

    try {
      const response = await apiFetch(`${API_BASE}/admin/settings`, {
        method: 'PUT',
        body: JSON.stringify({
          system: systemConfig,
          email: emailConfig,
          storage: storageConfig,
        }),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully' });
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to save settings' });
      }
    } catch (e) {
      console.error('Failed to save settings:', e);
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  }

  async function testEmailConfig() {
    try {
      const response = await apiFetch(`${API_BASE}/admin/settings/test-email`, {
        method: 'POST',
        body: JSON.stringify(emailConfig),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Email test sent successfully' });
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Email test failed' });
      }
    } catch (e) {
      console.error('Email test failed:', e);
      setMessage({ type: 'error', text: 'Email test failed' });
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">System Settings</h2>
          <p className="text-slate-500 dark:text-slate-400">Configure system parameters and integrations</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadSettings}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={saveSettings} disabled={saving}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {message && (
        <Alert variant={message.type === 'success' ? 'default' : 'destructive'}>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="system" className="space-y-4">
        <TabsList>
          <TabsTrigger value="system">System</TabsTrigger>
          <TabsTrigger value="email">Email</TabsTrigger>
          <TabsTrigger value="storage">Storage</TabsTrigger>
          <TabsTrigger value="ai">AI & OCR</TabsTrigger>
        </TabsList>

        {/* System Settings */}
        <TabsContent value="system" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="w-5 h-5" />
                General Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Environment</Label>
                  <Select
                    value={systemConfig.environment}
                    onValueChange={(value) => setSystemConfig({ ...systemConfig, environment: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="development">Development</SelectItem>
                      <SelectItem value="staging">Staging</SelectItem>
                      <SelectItem value="production">Production</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Max File Size (MB)</Label>
                  <Input
                    type="number"
                    value={systemConfig.max_file_size}
                    onChange={(e) => setSystemConfig({ ...systemConfig, max_file_size: parseInt(e.target.value) })}
                  />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Debug Mode</Label>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Enable detailed logging and error messages</p>
                </div>
                <Switch
                  checked={systemConfig.debug}
                  onCheckedChange={(checked) => setSystemConfig({ ...systemConfig, debug: checked })}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Classification Thresholds
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Auto-Approve Threshold ({(systemConfig.auto_approve_threshold * 100).toFixed(0)}%)</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">Documents above this confidence score are auto-approved</p>
                <Input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={systemConfig.auto_approve_threshold}
                  onChange={(e) => setSystemConfig({ ...systemConfig, auto_approve_threshold: parseFloat(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Review Threshold ({(systemConfig.review_threshold * 100).toFixed(0)}%)</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400">Documents below this score require manual review</p>
                <Input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={systemConfig.review_threshold}
                  onChange={(e) => setSystemConfig({ ...systemConfig, review_threshold: parseFloat(e.target.value) })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Email Settings */}
        <TabsContent value="email" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="w-5 h-5" />
                Email Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Enable Email Notifications</Label>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Send email alerts for document rejections and system events</p>
                </div>
                <Switch
                  checked={emailConfig.smtp_enabled}
                  onCheckedChange={(checked) => setEmailConfig({ ...emailConfig, smtp_enabled: checked })}
                />
              </div>
              <Separator />
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>SMTP Server</Label>
                    <Input
                      value={emailConfig.smtp_server}
                      onChange={(e) => setEmailConfig({ ...emailConfig, smtp_server: e.target.value })}
                      disabled={!emailConfig.smtp_enabled}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>SMTP Port</Label>
                    <Input
                      type="number"
                      value={emailConfig.smtp_port}
                      onChange={(e) => setEmailConfig({ ...emailConfig, smtp_port: parseInt(e.target.value) })}
                      disabled={!emailConfig.smtp_enabled}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>SMTP Username</Label>
                  <Input
                    value={emailConfig.smtp_username}
                    onChange={(e) => setEmailConfig({ ...emailConfig, smtp_username: e.target.value })}
                    disabled={!emailConfig.smtp_enabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label>From Email</Label>
                  <Input
                    type="email"
                    value={emailConfig.smtp_from_email}
                    onChange={(e) => setEmailConfig({ ...emailConfig, smtp_from_email: e.target.value })}
                    disabled={!emailConfig.smtp_enabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Admin Email</Label>
                  <Input
                    type="email"
                    value={emailConfig.admin_email}
                    onChange={(e) => setEmailConfig({ ...emailConfig, admin_email: e.target.value })}
                    disabled={!emailConfig.smtp_enabled}
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={testEmailConfig}
                  disabled={!emailConfig.smtp_enabled}
                >
                  <Bell className="w-4 h-4 mr-2" />
                  Send Test Email
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Storage Settings */}
        <TabsContent value="storage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HardDrive className="w-5 h-5" />
                Storage Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>MinIO Endpoint</Label>
                  <Input
                    value={storageConfig.minio_endpoint}
                    onChange={(e) => setStorageConfig({ ...storageConfig, minio_endpoint: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Bucket Name</Label>
                  <Input
                    value={storageConfig.minio_bucket}
                    onChange={(e) => setStorageConfig({ ...storageConfig, minio_bucket: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Storage Path</Label>
                <Input
                  value={storageConfig.storage_path}
                  onChange={(e) => setStorageConfig({ ...storageConfig, storage_path: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI & OCR Settings */}
        <TabsContent value="ai" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5" />
                AI & OCR Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Enable OCR Processing</Label>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Extract text from scanned documents using Tesseract</p>
                </div>
                <Switch
                  checked={systemConfig.ocr_enabled}
                  onCheckedChange={(checked) => setSystemConfig({ ...systemConfig, ocr_enabled: checked })}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Enable AI Features</Label>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Use OpenAI for enhanced duplicate detection and classification</p>
                </div>
                <Switch
                  checked={systemConfig.ai_enabled}
                  onCheckedChange={(checked) => setSystemConfig({ ...systemConfig, ai_enabled: checked })}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Enable Duplicate Detection</Label>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Automatically detect duplicate documents</p>
                </div>
                <Switch
                  checked={systemConfig.duplicate_detection}
                  onCheckedChange={(checked) => setSystemConfig({ ...systemConfig, duplicate_detection: checked })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}