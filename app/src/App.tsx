import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { Filter } from 'lucide-react';
import Login from '@/components/Login';
import DocumentUpload from '@/components/DocumentUpload';
import { ThemeToggle } from '@/components/ThemeToggle';
import AdvancedSearch, { type SearchFilters } from '@/components/AdvancedSearch';
import ToastContainer from '@/components/Toast';
import ErrorBoundary from '@/components/ErrorBoundary';
import AdminLayout from '@/layouts/AdminLayout';
import { Dashboard as AdminDashboard, Documents, Users, Analytics, Permissions, Audit, Settings } from '@/pages/admin';

const API_BASE = '/api';

// Colors for charts
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



// Enhanced Stat Card Component with trend indicator
function StatCard({ title, value, icon, color, subtitle, trend, trendValue }: { 
  title: string; 
  value: number | string; 
  icon: string; 
  color: string; 
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
    emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
    amber: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
    red: 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400',
    purple: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
    slate: 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  };
  
  const trendColor = trend === 'up' ? 'text-emerald-600' : trend === 'down' ? 'text-red-600' : 'text-slate-500';
  const trendIcon = trend === 'up' ? 'fa-arrow-up' : trend === 'down' ? 'fa-arrow-down' : 'fa-minus';
  
  return (
    <Card className="hover:shadow-md transition-shadow duration-200">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
            <p className="text-3xl font-bold text-slate-800 dark:text-slate-100 mt-1">{value}</p>
            <div className="flex items-center gap-2 mt-1">
              {subtitle && <p className="text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>}
              {trend && trendValue && (
                <span className={`text-xs font-medium ${trendColor} flex items-center gap-1`}>
                  <i className={`fas ${trendIcon} text-[10px]`}></i>
                  {trendValue}
                </span>
              )}
            </div>
          </div>
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorMap[color] || colorMap.slate} shadow-sm`}>
            <i className={`fas ${icon} text-xl`}></i>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Main Dashboard
function MainDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [recentDocs, setRecentDocs] = useState<RecentDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [searchResults, setSearchResults] = useState<RecentDoc[]>([]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
    navigate('/login');
  };

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  async function loadDashboard() {
    try {
      // Load stats
      const statsResp = await apiFetch(`${API_BASE}/admin/stats`);
      if (statsResp.ok) {
        const statsData = await statsResp.json();
        setStats(statsData);
      }

      // Load recent documents
      const docsResp = await apiFetch(`${API_BASE}/documents?page_size=10`);
      if (docsResp.ok) {
        const docsData = await docsResp.json();
        setRecentDocs(docsData.items || []);
      }

      // Health check
      const healthResp = await fetch('/health');
      if (healthResp.ok) {
        setSystemHealth(await healthResp.json());
      }
    } catch (e) {
      console.error('Dashboard load error:', e);
    } finally {
      setLoading(false);
    }
  }

  const handleAdvancedSearch = async (filters: SearchFilters) => {
    try {
      const params = new URLSearchParams();
      
      if (filters.query) params.append('query', filters.query);
      if (filters.category) params.append('category', filters.category);
      if (filters.status) params.append('status', filters.status);
      if (filters.dateFrom) params.append('date_from', filters.dateFrom);
      if (filters.dateTo) params.append('date_to', filters.dateTo);
      if (filters.uploader) params.append('uploader', filters.uploader);
      if (filters.minSize) params.append('min_size', filters.minSize.toString());
      if (filters.maxSize) params.append('max_size', filters.maxSize.toString());
      if (filters.fileType) params.append('file_type', filters.fileType);

      const searchResp = await apiFetch(`${API_BASE}/search/advanced?${params.toString()}`);
      if (searchResp.ok) {
        const searchData = await searchResp.json();
        setSearchResults(searchData.results || []);
      }
    } catch (e) {
      console.error('Advanced search error:', e);
    }
  };

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

  // Prepare chart data
  const categoryData = stats?.documents?.category_distribution
    ? Object.entries(stats.documents.category_distribution).map(([name, value]) => ({ name, value }))
    : [];

  const statusData = stats?.documents?.status_distribution
    ? Object.entries(stats.documents.status_distribution).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Office DMS Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Enterprise AI Document Management System</p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
          >
            <Filter className="w-4 h-4 mr-2" />
            Advanced Search
          </Button>
          <ThemeToggle />
          <Button onClick={handleLogout} variant="outline">
            Logout
          </Button>
        </div>
      </div>

      {/* Upload Section */}
      <DocumentUpload onUploadComplete={loadDashboard} />

      {/* Advanced Search Section */}
      {showAdvancedSearch && (
        <AdvancedSearch onSearch={handleAdvancedSearch} />
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-slate-700 dark:text-slate-300">
              Search Results ({searchResults.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {searchResults.map((doc) => (
                <div 
                  key={doc.id} 
                  className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <div className="flex-1">
                    <p className="font-medium text-slate-800 dark:text-slate-200">{doc.original_filename}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {doc.category || 'Uncategorized'} • {formatDate(doc.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Documents" value={stats?.documents?.total || 0} icon="fa-files" color="blue" subtitle="All time" trend="up" trendValue="+12%" />
        <StatCard title="Pending Review" value={stats?.documents?.pending_review || 0} icon="fa-inbox" color="amber" subtitle="Needs approval" trend="down" trendValue="-5%" />
        <StatCard title="Approved Today" value={stats?.documents?.approved_today || 0} icon="fa-check-circle" color="emerald" trend="up" trendValue="+8%" />
        <StatCard title="Duplicates" value={stats?.documents?.duplicates || 0} icon="fa-copy" color="purple" subtitle="Detected by AI" />
        <StatCard title="Suspicious" value={stats?.documents?.suspicious || 0} icon="fa-exclamation-triangle" color="red" />
        <StatCard title="Failed" value={stats?.documents?.failed || 0} icon="fa-times-circle" color="red" subtitle="Processing errors" trend="down" trendValue="-2%" />
        <StatCard title="SOPs Overdue" value={stats?.sops?.overdue || 0} icon="fa-clock" color="amber" />
        <StatCard title="Upcoming Reminders" value={stats?.reminders?.upcoming || 0} icon="fa-bell" color="blue" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-700">Document Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={statusData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                />
                <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]}>
                  {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Category Distribution */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-700">Document Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  dataKey="value"
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Documents Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold text-slate-700">Recent Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {recentDocs.length === 0 ? (
            <div className="text-center py-8 text-slate-400">
              <i className="fas fa-inbox text-3xl mb-2"></i>
              <p>No documents yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-3 font-semibold text-slate-500">Document</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-500">Category</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-500">Confidence</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-500">Status</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-500">Created</th>
                    <th className="text-right py-2 px-3 font-semibold text-slate-500">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50">
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <i className="fas fa-file text-slate-400 text-xs"></i>
                          <span className="font-medium text-slate-700">{doc.original_filename}</span>
                        </div>
                      </td>
                      <td className="py-2 px-3 text-slate-600">{doc.category || 'Unknown'}</td>
                      <td className="py-2 px-3">
                        {doc.confidence ? (
                          <div className="flex items-center gap-2">
                            <Progress value={doc.confidence * 100} className="w-16 h-1.5" />
                            <span className="text-xs font-medium">{Math.round(doc.confidence * 100)}%</span>
                          </div>
                        ) : '-'}
                      </td>
                      <td className="py-2 px-3"><StatusBadge status={doc.status} /></td>
                      <td className="py-2 px-3 text-slate-500">{formatDate(doc.created_at)}</td>
                      <td className="py-2 px-3 text-right">
                        <a href={`/documents/${doc.id}`} className="text-blue-600 hover:text-blue-800 font-medium text-xs">
                          Review
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* System Health */}
      {systemHealth && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-700">System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4 text-sm">
              {Object.entries(systemHealth.services || {}).map(([service, info]: [string, any]) => (
                <div key={service} className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${info.status === 'connected' || info.status === 'healthy' ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                  <span className="text-slate-600 capitalize">{service}:</span>
                  <span className="font-medium text-slate-800">{info.status}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Main App Component with Routing
export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    setIsAuthenticated(!!token);
    setLoading(false);
  }, []);

  const handleLogin = (token: string) => {
    setIsAuthenticated(true);
    // console.log('Logged in with token:', token); // Debug logging
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Skeleton className="h-8 w-32" />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ToastContainer />
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/admin/dashboard" replace />
            ) : (
              <Login onLogin={handleLogin} />
            )
          }
        />
        {/* Admin Panel Routes */}
        <Route
          path="/admin/*"
          element={
            isAuthenticated ? (
              <AdminLayout />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="documents" element={<Documents />} />
          <Route path="users" element={<Users />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="permissions" element={<Permissions />} />
          <Route path="audit" element={<Audit />} />
          <Route path="settings" element={<Settings />} />
          <Route path="" element={<Navigate to="/admin/dashboard" replace />} />
        </Route>
        <Route
          path="/"
          element={<Navigate to={isAuthenticated ? "/admin/dashboard" : "/login"} replace />}
        />
      </Routes>
    </ErrorBoundary>
  );
}
