import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Activity, 
  RefreshCw, 
  Server, 
  Database, 
  HardDrive, 
  Cpu,
  MemoryStick,
  Globe,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  FileText,
  Users,
  TrendingUp,
  TrendingDown
} from 'lucide-react';

// Mock Switch component for now (imported from ui/switch in real app)
function Switch({ checked, onCheckedChange }: { checked: boolean; onCheckedChange: (checked: boolean) => void }) {
  return (
    <button
      onClick={() => onCheckedChange(!checked)}
      className={`w-11 h-6 rounded-full p-1 transition-colors ${
        checked ? 'bg-blue-600' : 'bg-slate-300'
      }`}
    >
      <div
        className={`w-4 h-4 rounded-full bg-white transition-transform ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

const API_BASE = '/api';

interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down';
  uptime: number;
  version: string;
  last_check: string;
}

interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  uptime: number;
  cpu: number;
  memory: number;
  last_restart: string;
}

interface PerformanceMetrics {
  request_rate: number;
  avg_response_time: number;
  error_rate: number;
  active_connections: number;
}

interface StorageMetrics {
  total: number;
  used: number;
  available: number;
  documents_count: number;
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

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatUptime(seconds: number) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function MonitoringDashboard() {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [storage, setStorage] = useState<StorageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    loadMonitoringData();
    
    const interval = setInterval(loadMonitoringData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  async function loadMonitoringData() {
    try {
      setLoading(true);
      
      const [healthRes, servicesRes, perfRes, storageRes] = await Promise.all([
        apiFetch(`${API_BASE}/monitoring/health`),
        apiFetch(`${API_BASE}/monitoring/services`),
        apiFetch(`${API_BASE}/monitoring/performance`),
        apiFetch(`${API_BASE}/monitoring/storage`),
      ]);

      if (healthRes.ok) {
        const data = await healthRes.json();
        setSystemHealth(data);
      }

      if (servicesRes.ok) {
        const data = await servicesRes.json();
        setServices(data.services || []);
      }

      if (perfRes.ok) {
        const data = await perfRes.json();
        setPerformance(data);
      }

      if (storageRes.ok) {
        const data = await storageRes.json();
        setStorage(data);
      }
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
    } finally {
      setLoading(false);
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'healthy':
      case 'running':
        return 'bg-green-100 text-green-800';
      case 'degraded':
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'down':
      case 'stopped':
        return 'bg-slate-100 text-slate-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case 'healthy':
      case 'running':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'degraded':
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'down':
      case 'stopped':
        return <AlertTriangle className="w-4 h-4 text-slate-500" />;
      default:
        return <Activity className="w-4 h-4 text-slate-500" />;
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">System Monitoring</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Real-time system health and performance metrics
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadMonitoringData} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* System Health Overview */}
      {systemHealth && (
        <Card className={systemHealth.status === 'healthy' ? 'border-green-200' : systemHealth.status === 'degraded' ? 'border-amber-200' : 'border-red-200'}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(systemHealth.status)}
                <div>
                  <CardTitle>System Status: {systemHealth.status.charAt(0).toUpperCase() + systemHealth.status.slice(1)}</CardTitle>
                  <CardDescription>
                    Version {systemHealth.version} • Uptime: {formatUptime(systemHealth.uptime)}
                  </CardDescription>
                </div>
              </div>
              <Badge className={getStatusColor(systemHealth.status)}>
                {systemHealth.status.toUpperCase()}
              </Badge>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Performance Metrics */}
      {performance && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">Request Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-blue-500" />
                <div className="text-2xl font-bold">{performance.request_rate}</div>
                <span className="text-sm text-slate-500">req/s</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">Avg Response Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-green-500" />
                <div className="text-2xl font-bold">{performance.avg_response_time}</div>
                <span className="text-sm text-slate-500">ms</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">Error Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <div className="text-2xl font-bold">{(performance.error_rate * 100).toFixed(2)}%</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600 dark:text-slate-400">Active Connections</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-500" />
                <div className="text-2xl font-bold">{performance.active_connections}</div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Storage Metrics */}
      {storage && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="w-5 h-5" />
              Storage Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    {formatBytes(storage.used)} of {formatBytes(storage.total)} used
                  </span>
                  <span className="text-sm font-medium">
                    {((storage.used / storage.total) * 100).toFixed(1)}%
                  </span>
                </div>
                <Progress value={(storage.used / storage.total) * 100} />
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-600 dark:text-slate-400">Documents: {storage.documents_count}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-600 dark:text-slate-400">Available: {formatBytes(storage.available)}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Services Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="w-5 h-5" />
            Services Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {services.length === 0 ? (
              <div className="text-center py-8 text-slate-500">No service data available</div>
            ) : (
              services.map((service, index) => (
                <div key={index} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(service.status)}
                      <div>
                        <div className="font-medium">{service.name}</div>
                        <div className="text-sm text-slate-500">
                          Uptime: {formatUptime(service.uptime)}
                        </div>
                      </div>
                    </div>
                    <Badge className={getStatusColor(service.status)}>
                      {service.status.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-slate-500 mb-1">CPU Usage</div>
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-slate-400" />
                        <Progress value={service.cpu} className="flex-1" />
                        <span className="text-sm font-medium w-12 text-right">{service.cpu}%</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500 mb-1">Memory Usage</div>
                      <div className="flex items-center gap-2">
                        <MemoryStick className="w-4 h-4 text-slate-400" />
                        <Progress value={service.memory} className="flex-1" />
                        <span className="text-sm font-medium w-12 text-right">{service.memory}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Detailed Tabs */}
      <Tabs defaultValue="logs" className="w-full">
        <TabsList>
          <TabsTrigger value="logs">System Logs</TabsTrigger>
          <TabsTrigger value="errors">Error Logs</TabsTrigger>
          <TabsTrigger value="metrics">Detailed Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="logs" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent System Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="font-medium">INFO</span>
                    <span className="text-slate-500">2024-01-15 10:30:45</span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-400">System health check completed successfully</div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="font-medium">INFO</span>
                    <span className="text-slate-500">2024-01-15 10:25:30</span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-400">Document processing task completed</div>
                </div>
                <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="font-medium">WARNING</span>
                    <span className="text-slate-500">2024-01-15 10:20:15</span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-400">High memory usage detected (85%)</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="errors" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Error Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-slate-500">
                No errors logged in the last 24 hours
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Detailed Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-50 dark:bg-slate-900 rounded">
                    <div className="text-sm text-slate-500 mb-1">Total Requests (24h)</div>
                    <div className="text-2xl font-bold flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-green-500" />
                      12,456
                    </div>
                  </div>
                  <div className="p-4 bg-slate-50 dark:bg-slate-900 rounded">
                    <div className="text-sm text-slate-500 mb-1">Total Errors (24h)</div>
                    <div className="text-2xl font-bold flex items-center gap-2">
                      <TrendingDown className="w-5 h-5 text-green-500" />
                      23
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
