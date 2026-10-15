import { useCallback, useEffect, useState } from 'react';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Search,
  Filter,
  Eye,
  Trash2,
  Lock,
  Unlock,
  CheckCircle,
  XCircle,
  FileText,
  User,
  HardDrive,
  Calendar,
  AlertTriangle
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import DocumentUpload from '@/components/DocumentUpload';
import AdvancedSearch, { type SearchFilters } from '@/components/AdvancedSearch';

const API_BASE = '/api';

interface Document {
  id: number;
  original_filename: string;
  status: string;
  category: string | null;
  confidence: number | null;
  file_size: number;
  file_type: string;
  uploader: string;
  created_at: string;
  is_locked: boolean;
  locked_by: string | null;
  locked_at: string | null;
  function_type: string | null;
  function_confidence: number | null;
  quality_level: string | null;
  has_damage: boolean;
  damage_type: string | null;
  damage_severity: string | null;
}

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

const STATUSES = ['all', 'pending', 'processing', 'completed', 'approved', 'rejected', 'review', 'duplicate'];
const CATEGORIES = ['all', 'Invoice', 'Bill of Lading', 'NRC', 'FDA', 'Customs', 'Contract', 'Receipt', 'Purchase Order', 'Shipping Label', 'Other'];

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

function formatDate(iso: string | null) {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric',
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] || STATUS_COLORS.unknown;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>{(status || 'UNKNOWN').toUpperCase()}</span>;
}

export default function DocumentManagement() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState<number[]>([]);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [uploadComplete, setUploadComplete] = useState(false);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (categoryFilter !== 'all') params.append('category', categoryFilter);
      
      const response = await apiFetch(`${API_BASE}/documents?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.items || []);
      }
    } catch (e) {
      console.error('Failed to load documents:', e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, categoryFilter]);

  useEffect(() => {
    void Promise.resolve().then(loadDocuments);
  }, [loadDocuments, uploadComplete]);

  async function handleBulkApprove() {
    if (selectedDocuments.length === 0) return;

    try {
      const response = await apiFetch(`${API_BASE}/documents/bulk-approve`, {
        method: 'POST',
        body: JSON.stringify({ document_ids: selectedDocuments }),
      });

      if (response.ok) {
        setSelectedDocuments([]);
        loadDocuments();
      } else {
        alert('Failed to approve documents');
      }
    } catch (e) {
      console.error('Failed to approve documents:', e);
      alert('Failed to approve documents');
    }
  }

  async function handleBulkReject() {
    if (selectedDocuments.length === 0) return;

    try {
      const response = await apiFetch(`${API_BASE}/documents/bulk-reject`, {
        method: 'POST',
        body: JSON.stringify({ document_ids: selectedDocuments }),
      });

      if (response.ok) {
        setSelectedDocuments([]);
        loadDocuments();
      } else {
        alert('Failed to reject documents');
      }
    } catch (e) {
      console.error('Failed to reject documents:', e);
      alert('Failed to reject documents');
    }
  }

  async function handleDeleteDocument(docId: number) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      const response = await apiFetch(`${API_BASE}/documents/${docId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadDocuments();
      } else {
        alert('Failed to delete document');
      }
    } catch (e) {
      console.error('Failed to delete document:', e);
      alert('Failed to delete document');
    }
  }

  async function handleLockDocument(doc: Document) {
    try {
      const response = await apiFetch(`${API_BASE}/documents/${doc.id}/lock`, {
        method: doc.is_locked ? 'DELETE' : 'POST',
      });

      if (response.ok) {
        loadDocuments();
      } else {
        alert('Failed to update document lock');
      }
    } catch (e) {
      console.error('Failed to update document lock:', e);
      alert('Failed to update document lock');
    }
  }

  async function handleAdvancedSearch(filters: SearchFilters) {
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
        setDocuments(searchData.results || []);
      }
    } catch (e) {
      console.error('Advanced search error:', e);
    }
  }

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = 
      doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.category && doc.category.toLowerCase().includes(searchQuery.toLowerCase()));
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
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Document Management</h2>
          <p className="text-slate-500 dark:text-slate-400">Manage and process documents</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
          >
            <Filter className="w-4 h-4 mr-2" />
            Advanced Search
          </Button>
        </div>
      </div>

      {/* Upload Section */}
      <DocumentUpload onUploadComplete={() => setUploadComplete(!uploadComplete)} />

      {/* Advanced Search */}
      {showAdvancedSearch && (
        <AdvancedSearch onSearch={handleAdvancedSearch} />
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
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
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedDocuments.length > 0 && (
        <Card className="bg-blue-50 dark:bg-blue-900 border-blue-200 dark:border-blue-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                {selectedDocuments.length} documents selected
              </span>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleBulkApprove}>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve All
                </Button>
                <Button size="sm" variant="destructive" onClick={handleBulkReject}>
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject All
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Documents Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={selectedDocuments.length === filteredDocuments.length && filteredDocuments.length > 0}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDocuments(filteredDocuments.map(d => d.id));
                      } else {
                        setSelectedDocuments([]);
                      }
                    }}
                  />
                </TableHead>
                <TableHead>Document</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Function</TableHead>
                <TableHead>Quality</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Uploader</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDocuments.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedDocuments.includes(doc.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedDocuments([...selectedDocuments, doc.id]);
                        } else {
                          setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id));
                        }
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                        <FileText className="w-4 h-4 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900 dark:text-slate-100 max-w-xs truncate">
                          {doc.original_filename}
                        </p>
                        {doc.is_locked && (
                          <div className="flex items-center gap-1 text-xs text-amber-600">
                            <Lock className="w-3 h-3" />
                            <span>Locked by {doc.locked_by}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{doc.category || 'Uncategorized'}</Badge>
                  </TableCell>
                  <TableCell>
                    {doc.function_type ? (
                      <Badge variant="secondary" className="capitalize">
                        {doc.function_type.replace(/_/g, ' ')}
                      </Badge>
                    ) : (
                      <span className="text-slate-400 text-sm">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {doc.quality_level ? (
                      <Badge 
                        variant="outline" 
                        className={
                          doc.has_damage 
                            ? 'bg-red-50 text-red-700 border-red-200' 
                            : doc.quality_level === 'excellent' || doc.quality_level === 'good'
                            ? 'bg-green-50 text-green-700 border-green-200'
                            : 'bg-yellow-50 text-yellow-700 border-yellow-200'
                        }
                      >
                        {doc.quality_level.replace(/_/g, ' ')}
                      </Badge>
                    ) : (
                      <span className="text-slate-400 text-sm">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={doc.status} />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                      <User className="w-4 h-4" />
                      {doc.uploader}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                      <HardDrive className="w-4 h-4" />
                      {formatFileSize(doc.file_size)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                      <Calendar className="w-4 h-4" />
                      {formatDate(doc.created_at)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setSelectedDocument(doc);
                          setShowDetailDialog(true);
                        }}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleLockDocument(doc)}
                      >
                        {doc.is_locked ? (
                          <Lock className="w-4 h-4 text-amber-500" />
                        ) : (
                          <Unlock className="w-4 h-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteDocument(doc.id)}
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {filteredDocuments.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} className="text-center py-8 text-slate-500 dark:text-slate-400">
                    No documents found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Document Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Document Details</DialogTitle>
          </DialogHeader>
          {selectedDocument && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Filename</p>
                  <p className="font-medium">{selectedDocument.original_filename}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Status</p>
                  <StatusBadge status={selectedDocument.status} />
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Category</p>
                  <p className="font-medium">{selectedDocument.category || 'Uncategorized'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Confidence</p>
                  <p className="font-medium">{selectedDocument.confidence ? `${(selectedDocument.confidence * 100).toFixed(1)}%` : 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Function Type</p>
                  <p className="font-medium capitalize">{selectedDocument.function_type?.replace(/_/g, ' ') || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Function Confidence</p>
                  <p className="font-medium">{selectedDocument.function_confidence ? `${(selectedDocument.function_confidence * 100).toFixed(1)}%` : 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Quality Level</p>
                  <p className="font-medium capitalize">{selectedDocument.quality_level?.replace(/_/g, ' ') || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Damage Detected</p>
                  <p className="font-medium">{selectedDocument.has_damage ? 'Yes' : 'No'}</p>
                </div>
                {selectedDocument.has_damage && (
                  <>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Damage Type</p>
                      <p className="font-medium capitalize">{selectedDocument.damage_type?.replace(/_/g, ' ') || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Damage Severity</p>
                      <p className="font-medium capitalize">{selectedDocument.damage_severity || 'N/A'}</p>
                    </div>
                  </>
                )}
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">File Size</p>
                  <p className="font-medium">{formatFileSize(selectedDocument.file_size)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">File Type</p>
                  <p className="font-medium">{selectedDocument.file_type}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Uploader</p>
                  <p className="font-medium">{selectedDocument.uploader}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Created</p>
                  <p className="font-medium">{formatDate(selectedDocument.created_at)}</p>
                </div>
              </div>
              {selectedDocument.is_locked && (
                <div className="bg-amber-50 dark:bg-amber-900 p-3 rounded-lg">
                  <p className="text-sm text-amber-800 dark:text-amber-200">
                    <Lock className="w-4 h-4 inline mr-2" />
                    Document is locked by {selectedDocument.locked_by} since {formatDate(selectedDocument.locked_at)}
                  </p>
                </div>
              )}
              {selectedDocument.has_damage && (
                <div className="bg-red-50 dark:bg-red-900 p-3 rounded-lg">
                  <p className="text-sm text-red-800 dark:text-red-200">
                    <AlertTriangle className="w-4 h-4 inline mr-2" />
                    Document has {selectedDocument.damage_severity} {selectedDocument.damage_type?.replace(/_/g, ' ')} damage
                  </p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}