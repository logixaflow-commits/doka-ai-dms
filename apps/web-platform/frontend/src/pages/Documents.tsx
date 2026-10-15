import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Search, Eye, Trash2, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router';

const API_BASE = '/api';

interface Document {
  id: number;
  original_filename: string;
  status: string;
  category: string | null;
  confidence: number | null;
  created_at: string;
  file_size: number;
  ocr_text?: string;
  tags?: string[];
}

interface DocumentsResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
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
  const statusColors: Record<string, string> = {
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
  const cls = statusColors[status] || statusColors.unknown;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>{(status || 'UNKNOWN').toUpperCase()}</span>;
}

function formatDate(iso: string | null) {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

export default function Documents() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocs, setSelectedDocs] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const categories = ['Invoices', 'BL', 'NRC', 'FDA', 'Licenses', 'Household', 'Government', 'Association', 'Import', 'Export', 'Other'];
  const statuses = ['all', 'pending', 'processing', 'completed', 'approved', 'rejected', 'review', 'duplicate', 'failed'];

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '20',
      });

      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (categoryFilter !== 'all') params.append('category', categoryFilter);
      if (searchQuery) params.append('search', searchQuery);

      const response = await apiFetch(`${API_BASE}/documents?${params.toString()}`);
      if (response.ok) {
        const data: DocumentsResponse = await response.json();
        setDocuments(data.items || []);
        setTotalPages(Math.ceil(data.total / data.page_size));
        setTotalCount(data.total);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, statusFilter, categoryFilter, searchQuery]);

  useEffect(() => {
    void Promise.resolve().then(loadDocuments);
  }, [loadDocuments]);

  function handleSelectDoc(id: number) {
    const newSelected = new Set(selectedDocs);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedDocs(newSelected);
  }

  function handleSelectAll() {
    if (selectedDocs.size === documents.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(documents.map(doc => doc.id)));
    }
  }

  async function handleBulkApprove() {
    if (selectedDocs.size === 0) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/bulk-approve`, {
        method: 'POST',
        body: JSON.stringify({ document_ids: Array.from(selectedDocs) }),
      });
      if (response.ok) {
        setSelectedDocs(new Set());
        loadDocuments();
      }
    } catch (error) {
      console.error('Bulk approve failed:', error);
    }
  }

  async function handleBulkReject() {
    if (selectedDocs.size === 0) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/bulk-reject`, {
        method: 'POST',
        body: JSON.stringify({ document_ids: Array.from(selectedDocs) }),
      });
      if (response.ok) {
        setSelectedDocs(new Set());
        loadDocuments();
      }
    } catch (error) {
      console.error('Bulk reject failed:', error);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        loadDocuments();
      }
    } catch (error) {
      console.error('Delete failed:', error);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Documents</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Manage and organize your documents</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadDocuments} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => navigate('/documents/upload')} size="sm">
            Upload Document
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                <Input
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadDocuments()}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                {statuses.map(status => (
                  <SelectItem key={status} value={status}>
                    {status === 'all' ? 'All Statuses' : status.charAt(0).toUpperCase() + status.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(category => (
                  <SelectItem key={category} value={category}>{category}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedDocs.size > 0 && (
        <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950">
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                {selectedDocs.size} document{selectedDocs.size !== 1 ? 's' : ''} selected
              </span>
              <div className="flex gap-2">
                <Button onClick={handleBulkApprove} size="sm" variant="default">
                  Approve Selected
                </Button>
                <Button onClick={handleBulkReject} size="sm" variant="destructive">
                  Reject Selected
                </Button>
                <Button onClick={() => setSelectedDocs(new Set())} size="sm" variant="outline">
                  Clear Selection
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Documents Table */}
      <Card>
        <CardHeader>
          <CardTitle>Document List ({totalCount})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-500">Loading documents...</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 text-slate-500">No documents found</div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">
                      <Checkbox
                        checked={selectedDocs.size === documents.length && documents.length > 0}
                        onCheckedChange={handleSelectAll}
                      />
                    </TableHead>
                    <TableHead>Filename</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedDocs.has(doc.id)}
                          onCheckedChange={() => handleSelectDoc(doc.id)}
                        />
                      </TableCell>
                      <TableCell className="font-medium max-w-[200px] truncate">
                        {doc.original_filename}
                      </TableCell>
                      <TableCell>
                        {doc.category ? (
                          <Badge variant="outline">{doc.category}</Badge>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={doc.status} />
                      </TableCell>
                      <TableCell>
                        {doc.confidence !== null ? (
                          <Badge variant={doc.confidence > 0.8 ? 'default' : doc.confidence > 0.6 ? 'secondary' : 'destructive'}>
                            {(doc.confidence * 100).toFixed(0)}%
                          </Badge>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-slate-600 dark:text-slate-400">
                        {formatFileSize(doc.file_size)}
                      </TableCell>
                      <TableCell className="text-slate-600 dark:text-slate-400">
                        {formatDate(doc.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            onClick={() => navigate(`/documents/${doc.id}`)}
                            size="sm"
                            variant="ghost"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            onClick={() => handleDelete(doc.id)}
                            size="sm"
                            variant="ghost"
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center mt-4">
              <span className="text-sm text-slate-500">
                Page {currentPage} of {totalPages} ({totalCount} total)
              </span>
              <div className="flex gap-2">
                <Button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  size="sm"
                  variant="outline"
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  size="sm"
                  variant="outline"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
