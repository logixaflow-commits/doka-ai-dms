import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Download,
  Calendar,
  FileText,
  Users,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

const API_BASE = '/api';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

interface AnalyticsData {
  document_trends: Array<{ name: string; value: number }>;
  category_breakdown: Array<{ name: string; value: number }>;
  user_activity: Array<{ name: string; uploads: number; approvals: number }>;
  processing_times: Array<{ name: string; avg_time: number }>;
  error_rates: Array<{ name: string; rate: number }>;
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

// Mock data for demonstration (in real app, this would come from API)
const mockAnalyticsData: AnalyticsData = {
  document_trends: [
    { name: 'Jan', value: 45 },
    { name: 'Feb', value: 52 },
    { name: 'Mar', value: 38 },
    { name: 'Apr', value: 65 },
    { name: 'May', value: 58 },
    { name: 'Jun', value: 72 },
  ],
  category_breakdown: [
    { name: 'Invoice', value: 35 },
    { name: 'Bill of Lading', value: 25 },
    { name: 'NRC', value: 15 },
    { name: 'FDA', value: 10 },
    { name: 'Customs', value: 8 },
    { name: 'Other', value: 7 },
  ],
  user_activity: [
    { name: 'Admin', uploads: 45, approvals: 120 },
    { name: 'Staff1', uploads: 32, approvals: 85 },
    { name: 'Staff2', uploads: 28, approvals: 72 },
    { name: 'Staff3', uploads: 15, approvals: 45 },
  ],
  processing_times: [
    { name: 'OCR', avg_time: 2.5 },
    { name: 'Classification', avg_time: 1.2 },
    { name: 'Duplicate Check', avg_time: 0.8 },
    { name: 'Total', avg_time: 4.5 },
  ],
  error_rates: [
    { name: 'OCR Failures', rate: 2.5 },
    { name: 'Classification Errors', rate: 1.8 },
    { name: 'Upload Errors', rate: 0.5 },
    { name: 'Storage Errors', rate: 0.2 },
  ],
};

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('30d');
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  async function loadAnalytics() {
    setLoading(true);
    try {
      // In real app, fetch from API
      // const response = await apiFetch(`${API_BASE}/admin/analytics?range=${timeRange}`);
      // if (response.ok) {
      //   setAnalytics(await response.json());
      // }
      
      // Using mock data for now
      setAnalytics(mockAnalyticsData);
    } catch (e) {
      console.error('Failed to load analytics:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleExportReport() {
    try {
      const response = await apiFetch(`${API_BASE}/admin/export/analytics?range=${timeRange}`, {
        method: 'POST',
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analytics-report-${timeRange}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Failed to export report');
      }
    } catch (e) {
      console.error('Failed to export report:', e);
      alert('Failed to export report');
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500 dark:text-slate-400">No analytics data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Analytics & Reports</h2>
          <p className="text-slate-500 dark:text-slate-400">System performance and usage metrics</p>
        </div>
        <div className="flex gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="1y">Last year</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleExportReport}>
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Documents</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">
                  {analytics.document_trends.reduce((sum, item) => sum + item.value, 0)}
                </p>
                <div className="flex items-center gap-1 mt-2 text-xs text-emerald-600">
                  <TrendingUp className="w-3 h-3" />
                  <span>+12% from previous period</span>
                </div>
              </div>
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Active Users</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">
                  {analytics.user_activity.length}
                </p>
                <div className="flex items-center gap-1 mt-2 text-xs text-emerald-600">
                  <TrendingUp className="w-3 h-3" />
                  <span>+3 new this period</span>
                </div>
              </div>
              <div className="w-12 h-12 bg-emerald-50 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Avg Processing Time</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">
                  {analytics.processing_times.find(p => p.name === 'Total')?.avg_time.toFixed(1)}s
                </p>
                <div className="flex items-center gap-1 mt-2 text-xs text-emerald-600">
                  <TrendingDown className="w-3 h-3" />
                  <span>-0.5s from previous</span>
                </div>
              </div>
              <div className="w-12 h-12 bg-amber-50 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Error Rate</p>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">
                  {analytics.error_rates.reduce((sum, item) => sum + item.rate, 0).toFixed(1)}%
                </p>
                <div className="flex items-center gap-1 mt-2 text-xs text-red-600">
                  <TrendingUp className="w-3 h-3" />
                  <span>+0.3% from previous</span>
                </div>
              </div>
              <div className="w-12 h-12 bg-red-50 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Document Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Document Processing Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={analytics.document_trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="#2563eb" fill="#2563eb" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Category Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Document Category Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={analytics.category_breakdown}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {analytics.category_breakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Activity */}
        <Card>
          <CardHeader>
            <CardTitle>User Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.user_activity}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="uploads" fill="#2563eb" name="Uploads" />
                <Bar dataKey="approvals" fill="#10b981" name="Approvals" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Processing Times */}
        <Card>
          <CardHeader>
            <CardTitle>Average Processing Times</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.processing_times} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={80} />
                <Tooltip />
                <Bar dataKey="avg_time" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Error Rates */}
      <Card>
        <CardHeader>
          <CardTitle>Error Rates by Type</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analytics.error_rates}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="rate" stroke="#ef4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}