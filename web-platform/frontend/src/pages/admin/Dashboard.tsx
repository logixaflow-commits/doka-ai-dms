import { useState, useEffect, useCallback } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line,
} from 'recharts';
import {
  FileText, Users, Clock, CheckCircle, XCircle, AlertTriangle,
  TrendingUp, Activity, Server, Zap
} from 'lucide-react';

const API_BASE = '/api';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  review: 'bg-yellow-100 text-yellow-800',
  unknown: 'bg-gray-100 text-gray-800',
  duplicate: 'bg-pink-100 text-pink-800',
  failed: 'bg-red-100 text-red-800',
};

interface StatsData {
  documents: {
    total: number;
    pending_review: number;
    approved_today: number;
    rejected_today: number;
    duplicates: number;
    suspicious: number;
    failed: number;
    category_distribution: Record<string, number>;
    status_distribution: Record<string, number>;
  };
  users: { total: number; active: number };
  sops: { total: number; overdue: number };
  reminders: { upcoming: number };
}

interface RecentDoc {
  id: number;
  original_filename: string;
  status: string;
  category: string | null;
  confidence: number | null;
  created_at: string;
}

interface SystemHealth {
  status: string;
  database: string;
  redis: string;
  minio: string;
  celery: string;
  uptime: number;
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

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] || STATUS_COLORS.unknown;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>{(status || 'UNKNOWN').toUpperCase()}</span>;
}

function formatDate(iso: string | null) {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Enhanced Stat Card with trend
function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  color, 
  subtitle, 
  trend,
  trendValue 
}: { 
  title: string; 
  value: number | string; 
  icon: LucideIcon; 
  color: string; 
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    slate: 'bg-slate-50 text-slate-600',
  };

  const trendColors = {
    up: 'text-emerald-600',
    down: 'text-red-600',
    neutral: 'text-slate-600',
  };

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
            <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">{value}</p>
            {subtitle && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{subtitle}</p>}
            {trend && trendValue && (
              <div className={`flex items-center gap-1 mt-2 text-xs ${trendColors[trend]}`}>
                {trend === 'up' && <TrendingUp className="w-3 h-3" />}
                {trend === 'down' && <TrendingUp className="w-3 h-3 rotate-180" />}
                {trendValue}
              </div>
            )}
          </div>
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorMap[color] || colorMap.slate}`}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [recentDocs, setRecentDocs] = useState<RecentDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);

  const loadDashboard = useCallback(async () => {
    try {
      const statsResp = await apiFetch(`${API_BASE}/admin/stats`);
      if (statsResp.ok) {
        const statsData = await statsResp.json();
        setStats(statsData);
      }

      const docsResp = await apiFetch(`${API_BASE}/documents?page_size=10`);
      if (docsResp.ok) {
        const docsData = await docsResp.json();
        setRecentDocs(docsData.items || []);
      }

      const healthResp = await fetch('/health');
      if (healthResp.ok) {
        setSystemHealth(await healthResp.json());
      }
    } catch (e) {
      console.error('Dashboard load error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(loadDashboard);
    const interval = setInterval(() => void loadDashboard(), 30000);
    return () => clearInterval(interval);
  }, [loadDashboard]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  const categoryData = stats?.documents?.category_distribution
    ? Object.entries(stats.documents.category_distribution).map(([name, value]) => ({ name, value }))
    : [];

  const statusData = stats?.documents?.status_distribution
    ? Object.entries(stats.documents.status_distribution).map(([name, value]) => ({ name, value }))
    : [];

  // Mock trend data (in real app, this would come from API)
  const documentTrend = [
    { name: 'Mon', value: 45 },
    { name: 'Tue', value: 52 },
    { name: 'Wed', value: 38 },
    { name: 'Thu', value: 65 },
    { name: 'Fri', value: 58 },
    { name: 'Sat', value: 42 },
    { name: 'Sun', value: 35 },
  ];

  return (
    <div className="space-y-6">
      {/* Key Performance Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Documents"
          value={stats?.documents?.total || 0}
          icon={FileText}
          color="blue"
          subtitle="All time"
          trend="up"
          trendValue="+12% from last week"
        />
        <StatCard
          title="Pending Review"
          value={stats?.documents?.pending_review || 0}
          icon={Clock}
          color="amber"
          subtitle="Awaiting action"
          trend="down"
          trendValue="-5% from yesterday"
        />
        <StatCard
          title="Active Users"
          value={stats?.users?.active || 0}
          icon={Users}
          color="emerald"
          subtitle={`of ${stats?.users?.total || 0} total`}
          trend="up"
          trendValue="+3 new today"
        />
        <StatCard
          title="System Health"
          value={systemHealth?.status === 'healthy' ? '98%' : '85%'}
          icon={Activity}
          color="purple"
          subtitle="All systems operational"
          trend="neutral"
          trendValue="Stable"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Approved Today"
          value={stats?.documents?.approved_today || 0}
          icon={CheckCircle}
          color="emerald"
        />
        <StatCard
          title="Rejected Today"
          value={stats?.documents?.rejected_today || 0}
          icon={XCircle}
          color="red"
        />
        <StatCard
          title="Duplicates Found"
          value={stats?.documents?.duplicates || 0}
          icon={AlertTriangle}
          color="amber"
        />
        <StatCard
          title="AI Processing"
          value="Active"
          icon={Zap}
          color="blue"
          subtitle="Processing queue"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Document Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Document Processing Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={documentTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Category Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Document Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Status Distribution & Recent Documents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Document Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={statusData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Documents */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentDocs.slice(0, 5).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {doc.original_filename}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {doc.category || 'Uncategorized'} • {formatDate(doc.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>
              ))}
              {recentDocs.length === 0 && (
                <p className="text-center text-slate-500 dark:text-slate-400 py-4">No recent documents</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Health Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="w-5 h-5" />
            System Health Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Database</span>
                <Badge variant={systemHealth?.database === 'connected' ? 'default' : 'destructive'}>
                  {systemHealth?.database || 'Unknown'}
                </Badge>
              </div>
              <Progress value={systemHealth?.database === 'connected' ? 100 : 0} />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Redis</span>
                <Badge variant={systemHealth?.redis === 'connected' ? 'default' : 'destructive'}>
                  {systemHealth?.redis || 'Unknown'}
                </Badge>
              </div>
              <Progress value={systemHealth?.redis === 'connected' ? 100 : 0} />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">MinIO Storage</span>
                <Badge variant={systemHealth?.minio === 'connected' ? 'default' : 'destructive'}>
                  {systemHealth?.minio || 'Unknown'}
                </Badge>
              </div>
              <Progress value={systemHealth?.minio === 'connected' ? 100 : 0} />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Celery Workers</span>
                <Badge variant={systemHealth?.celery === 'running' ? 'default' : 'destructive'}>
                  {systemHealth?.celery || 'Unknown'}
                </Badge>
              </div>
              <Progress value={systemHealth?.celery === 'running' ? 100 : 0} />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}