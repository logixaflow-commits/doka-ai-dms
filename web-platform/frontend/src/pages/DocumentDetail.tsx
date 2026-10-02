import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { Slider } from '@/components/ui/slider';
import { ArrowLeft, Eye, Download, Trash2, Lock, Unlock, Clock, FileText, Tag, Calendar, HardDrive, CheckCircle, XCircle, ZoomIn, ZoomOut, RotateCw, ChevronLeft, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';

const API_BASE = '/api';

interface Document {
  id: number;
  original_filename: string;
  status: string;
  category: string | null;
  confidence: number | null;
  created_at: string;
  updated_at: string;
  file_size: number;
  file_path: string;
  mime_type: string;
  ocr_text?: string;
  tags?: string[];
  metadata?: {
    supplier?: string;
    invoice_number?: string;
    bl_number?: string;
    eta?: string;
    etd?: string;
    amount?: string;
    [key: string]: any;
  };
  locked_by?: number;
  locked_at?: string;
  expiry_date?: string;
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

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Preview state
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (id) {
      loadDocument(parseInt(id));
    }
  }, [id]);

  async function loadDocument(docId: number) {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/documents/${docId}`);
      if (response.ok) {
        const data = await response.json();
        setDocument(data);
      } else {
        setError('Failed to load document');
      }
    } catch (err) {
      setError('Error loading document');
      console.error('Failed to load document:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!document) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/${document.id}/approve`, {
        method: 'POST',
      });
      if (response.ok) {
        loadDocument(document.id);
      }
    } catch (error) {
      console.error('Approve failed:', error);
    }
  }

  async function handleReject() {
    if (!document) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/${document.id}/reject`, {
        method: 'POST',
      });
      if (response.ok) {
        loadDocument(document.id);
      }
    } catch (error) {
      console.error('Reject failed:', error);
    }
  }

  async function handleLock() {
    if (!document) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/${document.id}/lock`, {
        method: 'POST',
      });
      if (response.ok) {
        loadDocument(document.id);
      }
    } catch (error) {
      console.error('Lock failed:', error);
    }
  }

  async function handleUnlock() {
    if (!document) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/${document.id}/unlock`, {
        method: 'POST',
      });
      if (response.ok) {
        loadDocument(document.id);
      }
    } catch (error) {
      console.error('Unlock failed:', error);
    }
  }

  async function handleDelete() {
    if (!document || !confirm('Are you sure you want to delete this document?')) return;
    try {
      const response = await apiFetch(`${API_BASE}/documents/${document.id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        navigate('/documents');
      }
    } catch (error) {
      console.error('Delete failed:', error);
    }
  }

  // Preview controls
  const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 50));
  const handleZoomReset = () => setZoom(100);
  const handleRotate = () => setRotation(prev => (prev + 90) % 360);
  const handlePreviousPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
  const handleNextPage = () => setCurrentPage(prev => Math.min(prev + 1, totalPages));
  const toggleFullscreen = () => setIsFullscreen(!isFullscreen);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading document...</div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">{error || 'Document not found'}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-4">
          <Button onClick={() => navigate('/documents')} variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              {document.original_filename}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={document.status} />
              {document.category && (
                <Badge variant="outline">{document.category}</Badge>
              )}
              {document.locked_by && (
                <Badge variant="destructive">
                  <Lock className="w-3 h-3 mr-1" />
                  Locked
                </Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleApprove} size="sm" variant="default" disabled={document.status === 'approved'}>
            <CheckCircle className="w-4 h-4 mr-2" />
            Approve
          </Button>
          <Button onClick={handleReject} size="sm" variant="destructive" disabled={document.status === 'rejected'}>
            <XCircle className="w-4 h-4 mr-2" />
            Reject
          </Button>
          {document.locked_by ? (
            <Button onClick={handleUnlock} size="sm" variant="outline">
              <Unlock className="w-4 h-4 mr-2" />
              Unlock
            </Button>
          ) : (
            <Button onClick={handleLock} size="sm" variant="outline">
              <Lock className="w-4 h-4 mr-2" />
              Lock
            </Button>
          )}
          <Button onClick={handleDelete} size="sm" variant="destructive">
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Document Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Document Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-slate-400" />
              <div>
                <div className="text-sm text-slate-500">File Size</div>
                <div className="font-medium">{formatFileSize(document.file_size)}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <HardDrive className="w-5 h-5 text-slate-400" />
              <div>
                <div className="text-sm text-slate-500">Type</div>
                <div className="font-medium">{document.mime_type || 'Unknown'}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-slate-400" />
              <div>
                <div className="text-sm text-slate-500">Created</div>
                <div className="font-medium">{formatDate(document.created_at)}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-slate-400" />
              <div>
                <div className="text-sm text-slate-500">Updated</div>
                <div className="font-medium">{formatDate(document.updated_at)}</div>
              </div>
            </div>
            {document.expiry_date && (
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-slate-400" />
                <div>
                  <div className="text-sm text-slate-500">Expiry Date</div>
                  <div className="font-medium">{formatDate(document.expiry_date)}</div>
                </div>
              </div>
            )}
            {document.confidence !== null && (
              <div>
                <div className="text-sm text-slate-500 mb-1">Classification Confidence</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-slate-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${document.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{(document.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Extracted Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            {document.metadata && Object.keys(document.metadata).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(document.metadata).map(([key, value]) => (
                  value && (
                    <div key={key} className="flex justify-between">
                      <span className="text-sm text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="font-medium text-sm">{String(value)}</span>
                    </div>
                  )
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-400">No metadata extracted</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Tags</CardTitle>
          </CardHeader>
          <CardContent>
            {document.tags && document.tags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {document.tags.map((tag, index) => (
                  <Badge key={index} variant="secondary">
                    <Tag className="w-3 h-3 mr-1" />
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-400">No tags assigned</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* OCR Text and Preview */}
      <Tabs defaultValue="ocr" className="w-full">
        <TabsList>
          <TabsTrigger value="ocr">OCR Text</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="activity">Activity Log</TabsTrigger>
        </TabsList>
        
        <TabsContent value="ocr" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Extracted Text</CardTitle>
            </CardHeader>
            <CardContent>
              {document.ocr_text ? (
                <div className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
                    {document.ocr_text}
                  </pre>
                </div>
              ) : (
                <div className="text-sm text-slate-400">No OCR text available</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preview" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Document Preview</CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={toggleFullscreen}>
                    {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Preview Controls Toolbar */}
              <div className="flex items-center justify-between mb-4 p-2 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={handleZoomOut} disabled={zoom <= 50}>
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
                  <Button size="sm" variant="ghost" onClick={handleZoomIn} disabled={zoom >= 200}>
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={handleZoomReset}>
                    <span className="text-xs">Reset</span>
                  </Button>
                </div>
                
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost" onClick={handleRotate}>
                    <RotateCw className="w-4 h-4" />
                  </Button>
                </div>
                
                {totalPages > 1 && (
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="ghost" onClick={handlePreviousPage} disabled={currentPage <= 1}>
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="text-sm font-medium">
                      {currentPage} / {totalPages}
                    </span>
                    <Button size="sm" variant="ghost" onClick={handleNextPage} disabled={currentPage >= totalPages}>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>

              {/* Zoom Slider */}
              <div className="mb-4 px-2">
                <Slider
                  value={[zoom]}
                  onValueChange={(value) => setZoom(value[0])}
                  min={50}
                  max={200}
                  step={25}
                  className="w-full"
                />
              </div>

              {/* Preview Area */}
              <div 
                className={`flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg overflow-hidden transition-all ${
                  isFullscreen ? 'h-[70vh]' : 'h-96'
                }`}
                style={{ transform: `scale(${zoom / 100}) rotate(${rotation}deg)` }}
              >
                <Eye className="w-12 h-12 text-slate-400 mb-4" />
                <p className="text-slate-500">Document preview will be displayed here</p>
                <Button className="mt-4" variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Download File
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Activity Log</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-slate-400">Activity log will be displayed here</div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
