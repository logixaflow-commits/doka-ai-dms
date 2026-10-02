import { useState, useEffect, useCallback } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Search,
  Filter,
  Download,
  Calendar,
  User,
  Activity,
  FileText,
  Settings,
  Shield,
  Trash2,
  AlertTriangle
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

const API_BASE = '/api';

interface AuditLog {
  id: number;
  timestamp: string;
  user: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: string;
  ip_address: string;
  status: string;
}

const ACTION_TYPES = ['all', 'create', 'read', 'update', 'delete', 'login', 'logout', 'export', 'approve', 'reject'];
const RESOURCE_TYPES = ['all', 'document', 'user', 'role', 'permission', 'setting', 'system'];
const STATUSES = ['all', 'success', 'failure', 'warning'];

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

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric',
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
}

function getActionIcon(action: string) {
  const icons: Record<string, LucideIcon> = {
    create: FileText,
    read: Activity,
    update: Settings,
    delete: Trash2,
    login: User,
    logout: User,
    export: Download,
    approve: Shield,
    reject: AlertTriangle,
  };
  return icons[action] || Activity;
}

function getStatusBadge(status: string) {
  const statusColors: Record<string, string> = {
    success: 'bg-emerald-100 text-emerald-800',
    failure: 'bg-red-100 text-red-800',
    warning: 'bg-amber-100 text-amber-800',
  };
  
  return (
    <Badge className={statusColors[status] || 'bg-gray-100 text-gray-800'}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [resourceFilter, setResourceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const loadAuditLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (actionFilter !== 'all') params.append('action', actionFilter);
      if (resourceFilter !== 'all') params.append('resource_type', resourceFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      
      const response = await apiFetch(`${API_BASE}/admin/audit?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      }
    } catch (e) {
      console.error('Failed to load audit logs:', e);
    } finally {
      setLoading(false);
    }
  }, [actionFilter, resourceFilter, statusFilter, dateFrom, dateTo]);

  useEffect(() => {
    void Promise.resolve().then(loadAuditLogs);
  }, [loadAuditLogs]);

  async function handleExportLogs() {
    try {
      const params = new URLSearchParams();
      if (actionFilter !== 'all') params.append('action', actionFilter);
      if (resourceFilter !== 'all') params.append('resource_type', resourceFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);

      const response = await apiFetch(`${API_BASE}/admin/audit/export?${params.toString()}`, {
        method: 'POST',
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Failed to export logs');
      }
    } catch (e) {
      console.error('Failed to export logs:', e);
      alert('Failed to export logs');
    }
  }

  const filteredLogs = logs.filter(log => {
    const matchesSearch = 
      log.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.details.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  if (loading) {
    return (
      <div className="space-y-4">
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
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Audit Logs</h2>
          <p className="text-slate-500 dark:text-slate-400">System activity and security events</p>
        </div>
        <Button onClick={handleExportLogs}>
          <Download className="w-4 h-4 mr-2" />
          Export Logs
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                <Input
                  placeholder="Search logs by user, action, or details..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Action" />
                </SelectTrigger>
                <SelectContent>
                  {ACTION_TYPES.map((action) => (
                    <SelectItem key={action} value={action}>
                      {action.charAt(0).toUpperCase() + action.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={resourceFilter} onValueChange={setResourceFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Resource" />
                </SelectTrigger>
                <SelectContent>
                  {RESOURCE_TYPES.map((resource) => (
                    <SelectItem key={resource} value={resource}>
                      {resource.charAt(0).toUpperCase() + resource.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  {STATUSES.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  placeholder="From date"
                />
              </div>
              <div className="flex-1">
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  placeholder="To date"
                />
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery('');
                  setActionFilter('all');
                  setResourceFilter('all');
                  setStatusFilter('all');
                  setDateFrom('');
                  setDateTo('');
                }}
              >
                <Filter className="w-4 h-4 mr-2" />
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredLogs.map((log) => {
                const ActionIcon = getActionIcon(log.action);
                return (
                  <TableRow key={log.id}>
                    <TableCell>
                      <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                        <Calendar className="w-4 h-4" />
                        {formatDate(log.timestamp)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                          <User className="w-3 h-3 text-blue-600" />
                        </div>
                        <span className="font-medium">{log.user}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <ActionIcon className="w-4 h-4 text-slate-500" />
                        <span className="capitalize">{log.action}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {log.resource_type}
                      </Badge>
                      {log.resource_id && (
                        <span className="text-xs text-slate-500 ml-1">#{log.resource_id}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <p className="text-sm text-slate-600 dark:text-slate-400 max-w-xs truncate">
                        {log.details}
                      </p>
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                        {log.ip_address}
                      </code>
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(log.status)}
                    </TableCell>
                  </TableRow>
                );
              })}
              {filteredLogs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-slate-500 dark:text-slate-400">
                    No audit logs found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}