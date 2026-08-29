import { useState } from 'react';
import { Shield, Search, Filter, Download, Calendar, User, Activity, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Alert, AlertDescription } from '@/components/ui/alert';

export interface AuditLog {
  id: string;
  timestamp: Date;
  userId: string;
  username: string;
  action: string;
  entityType: 'document' | 'user' | 'system' | 'security';
  entityId: string;
  entityName: string;
  details: string;
  ipAddress: string;
  userAgent: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
}

interface AuditTrailViewerProps {
  documentId?: string;
  userId?: string;
}

export default function AuditTrailViewer({ documentId, userId }: AuditTrailViewerProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<AuditLog[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [entityFilter, setEntityFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);

  const actionOptions = [
    { value: 'all', label: 'All Actions' },
    { value: 'create', label: 'Create' },
    { value: 'read', label: 'Read' },
    { value: 'update', label: 'Update' },
    { value: 'delete', label: 'Delete' },
    { value: 'share', label: 'Share' },
    { value: 'download', label: 'Download' },
    { value: 'upload', label: 'Upload' },
    { value: 'login', label: 'Login' },
    { value: 'logout', label: 'Logout' },
  ];

  const entityOptions = [
    { value: 'all', label: 'All Entities' },
    { value: 'document', label: 'Documents' },
    { value: 'user', label: 'Users' },
    { value: 'system', label: 'System' },
    { value: 'security', label: 'Security' },
  ];

  const severityOptions = [
    { value: 'all', label: 'All Severities' },
    { value: 'info', label: 'Info' },
    { value: 'warning', label: 'Warning' },
    { value: 'error', label: 'Error' },
    { value: 'critical', label: 'Critical' },
  ];

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (documentId) params.append('document_id', documentId);
      if (userId) params.append('user_id', userId);

      const response = await fetch(`/api/audit-trail?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to load audit logs');

      const data = await response.json();
      setLogs(data);
      setFilteredLogs(data);
    } catch (err) {
      // Use mock data for demo
      const mockLogs = generateMockAuditLogs();
      setLogs(mockLogs);
      setFilteredLogs(mockLogs);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = logs;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (log) =>
          log.username.toLowerCase().includes(query) ||
          log.action.toLowerCase().includes(query) ||
          log.entityName.toLowerCase().includes(query) ||
          log.details.toLowerCase().includes(query)
      );
    }

    // Action filter
    if (actionFilter !== 'all') {
      filtered = filtered.filter((log) => log.action.toLowerCase() === actionFilter);
    }

    // Entity filter
    if (entityFilter !== 'all') {
      filtered = filtered.filter((log) => log.entityType === entityFilter);
    }

    // Severity filter
    if (severityFilter !== 'all') {
      filtered = filtered.filter((log) => log.severity === severityFilter);
    }

    // Date filter
    if (dateFrom) {
      filtered = filtered.filter((log) => new Date(log.timestamp) >= new Date(dateFrom));
    }
    if (dateTo) {
      filtered = filtered.filter((log) => new Date(log.timestamp) <= new Date(dateTo));
    }

    setFilteredLogs(filtered);
  };

  const exportAuditLogs = () => {
    const csv = [
      'Timestamp,User,Action,Entity Type,Entity Name,Details,IP Address,Severity',
      ...filteredLogs.map((log) =>
        [
          log.timestamp.toISOString(),
          log.username,
          log.action,
          log.entityType,
          log.entityName,
          log.details,
          log.ipAddress,
          log.severity,
        ].join(',')
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-trail-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleString();
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      case 'error':
        return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
      case 'warning':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
      default:
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
    }
  };

  const getEntityIcon = (entityType: string) => {
    switch (entityType) {
      case 'document':
        return <FileText className="w-4 h-4" />;
      case 'user':
        return <User className="w-4 h-4" />;
      case 'system':
        return <Activity className="w-4 h-4" />;
      case 'security':
        return <Shield className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5" />
          Audit Trail
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="space-y-3 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Filters</span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <label className="text-xs text-slate-500 dark:text-slate-400">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                <Input
                  placeholder="Search logs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-500 dark:text-slate-400">Action</label>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {actionOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-500 dark:text-slate-400">Entity Type</label>
              <Select value={entityFilter} onValueChange={setEntityFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {entityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-slate-500 dark:text-slate-400">Severity</label>
              <Select value={severityFilter} onValueChange={setSeverityFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {severityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs text-slate-500 dark:text-slate-400">From Date</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500 dark:text-slate-400">To Date</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={applyFilters} size="sm">
              <Filter className="w-4 h-4 mr-2" />
              Apply Filters
            </Button>
            <Button onClick={loadAuditLogs} variant="outline" size="sm">
              Refresh
            </Button>
            <Button onClick={exportAuditLogs} variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>

        {/* Audit Logs */}
        <div className="space-y-2">
          {filteredLogs.length === 0 ? (
            <Alert>
              <Shield className="h-4 w-4" />
              <AlertDescription>
                No audit logs found matching your filters.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {filteredLogs.map((log) => (
                <div
                  key={log.id}
                  className="p-4 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <Avatar className="w-8 h-8">
                        <AvatarFallback className="text-xs bg-slate-200 dark:bg-slate-700">
                          {log.username.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>

                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-slate-900 dark:text-slate-100 text-sm">
                            {log.username}
                          </span>
                          <span className="text-slate-400">•</span>
                          <span className="text-xs text-slate-600 dark:text-slate-400">
                            {log.action}
                          </span>
                          <Badge className={`text-xs ${getSeverityColor(log.severity)}`}>
                            {log.severity}
                          </Badge>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                          <div className="flex items-center gap-1">
                            {getEntityIcon(log.entityType)}
                            <span>{log.entityType}</span>
                          </div>
                          <span className="text-slate-400">•</span>
                          <span>{log.entityName}</span>
                          <span className="text-slate-400">•</span>
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            <span>{formatTime(log.timestamp)}</span>
                          </div>
                        </div>

                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {log.details}
                        </p>

                        <div className="text-xs text-slate-400 dark:text-slate-500">
                          IP: {log.ipAddress}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400 text-center">
          Showing {filteredLogs.length} of {logs.length} audit logs
        </div>
      </CardContent>
    </Card>
  );
}

function generateMockAuditLogs(): AuditLog[] {
  const now = new Date();
  return [
    {
      id: '1',
      timestamp: new Date(now.getTime() - 1000 * 60 * 5),
      userId: '1',
      username: 'John Doe',
      action: 'upload',
      entityType: 'document',
      entityId: 'doc-1',
      entityName: 'invoice_001.pdf',
      details: 'Uploaded new document via drag and drop',
      ipAddress: '192.168.1.100',
      userAgent: 'Mozilla/5.0',
      severity: 'info',
    },
    {
      id: '2',
      timestamp: new Date(now.getTime() - 1000 * 60 * 15),
      userId: '2',
      username: 'Jane Smith',
      action: 'download',
      entityType: 'document',
      entityId: 'doc-2',
      entityName: 'contract_2024.pdf',
      details: 'Downloaded document for review',
      ipAddress: '192.168.1.101',
      userAgent: 'Mozilla/5.0',
      severity: 'info',
    },
    {
      id: '3',
      timestamp: new Date(now.getTime() - 1000 * 60 * 30),
      userId: '1',
      username: 'John Doe',
      action: 'share',
      entityType: 'document',
      entityId: 'doc-1',
      entityName: 'invoice_001.pdf',
      details: 'Generated share link with 24h expiration',
      ipAddress: '192.168.1.100',
      userAgent: 'Mozilla/5.0',
      severity: 'warning',
    },
    {
      id: '4',
      timestamp: new Date(now.getTime() - 1000 * 60 * 45),
      userId: '3',
      username: 'Bob Johnson',
      action: 'login',
      entityType: 'security',
      entityId: 'user-3',
      entityName: 'Bob Johnson',
      details: 'User logged in successfully',
      ipAddress: '192.168.1.102',
      userAgent: 'Mozilla/5.0',
      severity: 'info',
    },
    {
      id: '5',
      timestamp: new Date(now.getTime() - 1000 * 60 * 60),
      userId: 'system',
      username: 'System',
      action: 'delete',
      entityType: 'document',
      entityId: 'doc-3',
      entityName: 'old_document.pdf',
      details: 'Auto-deleted expired document',
      ipAddress: '127.0.0.1',
      userAgent: 'System',
      severity: 'warning',
    },
    {
      id: '6',
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 2),
      userId: '4',
      username: 'Alice Williams',
      action: 'update',
      entityType: 'document',
      entityId: 'doc-4',
      entityName: 'meeting_notes.docx',
      details: 'Updated document content',
      ipAddress: '192.168.1.103',
      userAgent: 'Mozilla/5.0',
      severity: 'info',
    },
    {
      id: '7',
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 3),
      userId: 'system',
      username: 'System',
      action: 'backup',
      entityType: 'system',
      entityId: 'backup-1',
      entityName: 'Daily Backup',
      details: 'Completed daily backup of all documents',
      ipAddress: '127.0.0.1',
      userAgent: 'System',
      severity: 'info',
    },
    {
      id: '8',
      timestamp: new Date(now.getTime() - 1000 * 60 * 60 * 5),
      userId: '1',
      username: 'John Doe',
      action: 'login',
      entityType: 'security',
      entityId: 'user-1',
      entityName: 'John Doe',
      details: 'Failed login attempt - invalid password',
      ipAddress: '192.168.1.100',
      userAgent: 'Mozilla/5.0',
      severity: 'error',
    },
  ];
}
