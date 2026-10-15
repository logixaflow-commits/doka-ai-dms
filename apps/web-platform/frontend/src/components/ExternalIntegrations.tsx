import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Link, RefreshCw, TestTube, Settings, Shield, Ship, Globe, CheckCircle, AlertCircle, Trash2, Plus } from 'lucide-react';

const API_BASE = '/api';

interface Integration {
  id: number;
  name: string;
  type: 'customs' | 'shipping' | 'email' | 'storage';
  base_url: string;
  api_key: string;
  enabled: boolean;
  last_sync: string | null;
  status: 'active' | 'inactive' | 'error';
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

const INTEGRATION_TYPES = [
  { value: 'customs', label: 'Customs API', icon: Shield, description: 'Myanmar Customs Authority integration' },
  { value: 'shipping', label: 'Shipping API', icon: Ship, description: 'Logistics and shipping provider integration' },
  { value: 'email', label: 'Email Service', icon: Globe, description: 'Transactional email service' },
  { value: 'storage', label: 'Cloud Storage', icon: Globe, description: 'External cloud storage integration' },
] as const;

export default function ExternalIntegrations() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // New integration form state
  const [integrationName, setIntegrationName] = useState('');
  const [integrationType, setIntegrationType] = useState<'customs' | 'shipping' | 'email' | 'storage'>('customs');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    loadIntegrations();
  }, []);

  async function loadIntegrations() {
    try {
      setLoading(true);
      const response = await apiFetch(`${API_BASE}/integrations`);
      if (response.ok) {
        const data = await response.json();
        setIntegrations(data.integrations || []);
      }
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  }

  async function createIntegration() {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/integrations`, {
        method: 'POST',
        body: JSON.stringify({
          name: integrationName,
          type: integrationType,
          base_url: baseUrl,
          api_key: apiKey,
        }),
      });

      if (response.ok) {
        setSuccess('Integration created successfully');
        setShowCreateDialog(false);
        resetForm();
        loadIntegrations();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create integration');
      }
    } catch (err) {
      setError('Error creating integration');
      console.error('Failed to create integration:', err);
    }
  }

  async function toggleIntegration(integrationId: number, enabled: boolean) {
    try {
      const response = await apiFetch(`${API_BASE}/integrations/${integrationId}/toggle`, {
        method: 'POST',
        body: JSON.stringify({ enabled }),
      });

      if (response.ok) {
        loadIntegrations();
      }
    } catch (err) {
      console.error('Failed to toggle integration:', err);
    }
  }

  async function testIntegration(integrationId: number) {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/integrations/${integrationId}/test`, {
        method: 'POST',
      });

      if (response.ok) {
        setSuccess('Integration test successful');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Integration test failed');
      }
    } catch (err) {
      setError('Error testing integration');
      console.error('Failed to test integration:', err);
    }
  }

  async function syncIntegration(integrationId: number) {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/integrations/${integrationId}/sync`, {
        method: 'POST',
      });

      if (response.ok) {
        setSuccess('Integration synced successfully');
        loadIntegrations();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Integration sync failed');
      }
    } catch (err) {
      setError('Error syncing integration');
      console.error('Failed to sync integration:', err);
    }
  }

  async function deleteIntegration(integrationId: number) {
    if (!confirm('Are you sure you want to delete this integration?')) return;

    try {
      const response = await apiFetch(`${API_BASE}/integrations/${integrationId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadIntegrations();
      }
    } catch (err) {
      console.error('Failed to delete integration:', err);
    }
  }

  function resetForm() {
    setIntegrationName('');
    setIntegrationType('customs');
    setBaseUrl('');
    setApiKey('');
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading integrations...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">External Integrations</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Connect with external services and APIs
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadIntegrations} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Add Integration
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Create Integration Dialog */}
      {showCreateDialog && (
        <Card className="border-blue-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link className="w-5 h-5" />
              Add New Integration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Integration Name</Label>
                <Input
                  value={integrationName}
                  onChange={(e) => setIntegrationName(e.target.value)}
                  placeholder="e.g., Myanmar Customs API"
                />
              </div>
              <div className="space-y-2">
                <Label>Integration Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  {INTEGRATION_TYPES.map(type => (
                    <div
                      key={type.value}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        integrationType === type.value
                          ? 'bg-blue-50 dark:bg-blue-950 border-blue-500'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-900'
                      }`}
                      onClick={() => setIntegrationType(type.value)}
                    >
                      <div className="flex items-center gap-2">
                        <type.icon className="w-4 h-4" />
                        <div>
                          <div className="font-medium text-sm">{type.label}</div>
                          <div className="text-xs text-slate-500">{type.description}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Base URL</Label>
                <Input
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.example.com"
                />
              </div>
              <div className="space-y-2">
                <Label>API Key</Label>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter API key"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={createIntegration}>
                  Create Integration
                </Button>
                <Button onClick={() => { setShowCreateDialog(false); resetForm(); }} variant="outline">
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Integrations List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {integrations.length === 0 ? (
          <Card className="col-span-2">
            <CardContent className="py-12 text-center">
              <Link className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">
                No Integrations Configured
              </h3>
              <p className="text-slate-500 dark:text-slate-400">
                Add your first external integration to connect with external services
              </p>
            </CardContent>
          </Card>
        ) : (
          integrations.map(integration => {
            const typeInfo = INTEGRATION_TYPES.find(t => t.value === integration.type);
            return (
              <Card key={integration.id} className={!integration.enabled ? 'opacity-60' : ''}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <typeInfo.icon className="w-8 h-8 text-slate-400" />
                      <div>
                        <CardTitle className="text-lg">{integration.name}</CardTitle>
                        <CardDescription>{typeInfo.description}</CardDescription>
                      </div>
                    </div>
                    <Badge variant={integration.status === 'active' ? 'default' : integration.status === 'error' ? 'destructive' : 'secondary'}>
                      {integration.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500">Base URL</span>
                        <span className="font-mono text-xs">{integration.base_url}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500">Last Sync</span>
                        <span>{integration.last_sync ? new Date(integration.last_sync).toLocaleString() : 'Never'}</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={integration.enabled}
                          onCheckedChange={(checked) => toggleIntegration(integration.id, checked)}
                        />
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                          {integration.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={() => testIntegration(integration.id)}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        <TestTube className="w-4 h-4 mr-2" />
                        Test
                      </Button>
                      <Button
                        onClick={() => syncIntegration(integration.id)}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        disabled={!integration.enabled}
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Sync
                      </Button>
                      <Button
                        onClick={() => deleteIntegration(integration.id)}
                        variant="ghost"
                        size="icon"
                        className="text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Integration Types Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Supported Integration Types
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {INTEGRATION_TYPES.map(type => (
              <div key={type.value} className="p-4 border rounded-lg">
                <div className="flex items-center gap-3 mb-2">
                  <type.icon className="w-5 h-5 text-slate-400" />
                  <div className="font-medium">{type.label}</div>
                </div>
                <p className="text-sm text-slate-500">{type.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
