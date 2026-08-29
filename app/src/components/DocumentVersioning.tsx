import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  History, 
  RefreshCw, 
  ArrowLeft, 
  Download, 
  Restore, 
  Eye,
  FileText,
  Calendar,
  HardDrive,
  Hash,
  AlertCircle,
  CheckCircle,
  Trash2
} from 'lucide-react';

const API_BASE = '/api';

interface DocumentVersion {
  id: number;
  document_id: number;
  version_number: number;
  file_path: string;
  file_size: number;
  file_hash: string;
  created_at: string;
  created_by: string;
  is_current: boolean;
  archived: boolean;
  archived_at: string | null;
}

interface Document {
  id: number;
  original_filename: string;
  current_version: number;
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
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

export default function DocumentVersioning() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      const response = await apiFetch(`${API_BASE}/documents?page_size=50`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.items || []);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }

  async function loadVersions(docId: number) {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/documents/${docId}/versions`);
      
      if (response.ok) {
        const data = await response.json();
        setVersions(data.versions || []);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to load versions');
      }
    } catch (err) {
      setError('Error loading versions');
      console.error('Failed to load versions:', err);
    } finally {
      setLoading(false);
    }
  }

  async function restoreVersion(versionId: number) {
    if (!confirm('Are you sure you want to restore this version? This will replace the current version.')) return;

    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/documents/versions/${versionId}/restore`, {
        method: 'POST',
      });

      if (response.ok) {
        setSuccess('Version restored successfully');
        if (selectedDocument) {
          loadVersions(selectedDocument.id);
          loadDocuments();
        }
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to restore version');
      }
    } catch (err) {
      setError('Error restoring version');
      console.error('Failed to restore version:', err);
    }
  }

  async function downloadVersion(versionId: number) {
    try {
      const response = await apiFetch(`${API_BASE}/documents/versions/${versionId}/download`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `version-${versionId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      setError('Failed to download version');
      console.error('Failed to download version:', err);
    }
  }

  async function deleteVersion(versionId: number) {
    if (!confirm('Are you sure you want to delete this version?')) return;

    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/documents/versions/${versionId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setSuccess('Version deleted successfully');
        if (selectedDocument) {
          loadVersions(selectedDocument.id);
        }
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete version');
      }
    } catch (err) {
      setError('Error deleting version');
      console.error('Failed to delete version:', err);
    }
  }

  function compareVersions(v1: DocumentVersion, v2: DocumentVersion) {
    const sizeDiff = v2.file_size - v1.file_size;
    const hashSame = v1.file_hash === v2.file_hash;
    
    return {
      sizeChanged: sizeDiff !== 0,
      sizeDiff: formatFileSize(Math.abs(sizeDiff)),
      sizeIncreased: sizeDiff > 0,
      contentChanged: !hashSame,
    };
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Document Versioning</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Track and manage document versions with automatic archiving
          </p>
        </div>
        <Button onClick={loadDocuments} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
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

      {/* Document Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Select Document
          </CardTitle>
          <CardDescription>
            Choose a document to view its version history
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {documents.map(doc => (
              <div
                key={doc.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedDocument?.id === doc.id
                    ? 'bg-blue-50 dark:bg-blue-950 border-blue-500'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-900'
                }`}
                onClick={() => {
                  setSelectedDocument(doc);
                  loadVersions(doc.id);
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-slate-400" />
                    <div>
                      <div className="font-medium">{doc.original_filename}</div>
                      <div className="text-sm text-slate-500">Current Version: {doc.current_version}</div>
                    </div>
                  </div>
                  <Badge variant="outline">v{doc.current_version}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Version History */}
      {selectedDocument && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <History className="w-5 h-5" />
                  Version History
                </CardTitle>
                <CardDescription>
                  {selectedDocument.original_filename} - {versions.length} versions
                </CardDescription>
              </div>
              {selectedDocument && (
                <Button onClick={() => setSelectedDocument(null)} variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Loading versions...</div>
            ) : versions.length === 0 ? (
              <div className="text-center py-8 text-slate-500">No versions found</div>
            ) : (
              <div className="space-y-3">
                {versions.map((version, index) => {
                  const prevVersion = versions[index + 1];
                  const comparison = prevVersion ? compareVersions(version, prevVersion) : null;
                  
                  return (
                    <div
                      key={version.id}
                      className={`p-4 border rounded-lg ${
                        version.is_current ? 'bg-green-50 dark:bg-green-950 border-green-500' : 
                        version.archived ? 'bg-slate-50 dark:bg-slate-900 opacity-60' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="flex flex-col items-center">
                            <Badge 
                              variant={version.is_current ? 'default' : 'outline'}
                              className="mb-1"
                            >
                              v{version.version_number}
                            </Badge>
                            {version.is_current && (
                              <span className="text-xs text-green-600 font-medium">Current</span>
                            )}
                            {version.archived && (
                              <span className="text-xs text-slate-500">Archived</span>
                            )}
                          </div>
                          <div>
                            <div className="font-medium">Created by {version.created_by}</div>
                            <div className="text-sm text-slate-500 flex items-center gap-2">
                              <Calendar className="w-3 h-3" />
                              {formatDate(version.created_at)}
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => downloadVersion(version.id)}
                            variant="ghost"
                            size="icon"
                            title="Download"
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                          {!version.is_current && (
                            <Button
                              onClick={() => restoreVersion(version.id)}
                              variant="ghost"
                              size="icon"
                              title="Restore"
                            >
                              <Restore className="w-4 h-4" />
                            </Button>
                          )}
                          {!version.is_current && (
                            <Button
                              onClick={() => deleteVersion(version.id)}
                              variant="ghost"
                              size="icon"
                              className="text-red-600"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-4 h-4 text-slate-400" />
                          <span className="text-slate-600 dark:text-slate-400">
                            {formatFileSize(version.file_size)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Hash className="w-4 h-4 text-slate-400" />
                          <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                            {version.file_hash.slice(0, 12)}...
                          </span>
                        </div>
                        {version.archived_at && (
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-slate-400" />
                            <span className="text-slate-600 dark:text-slate-400">
                              Archived: {formatDate(version.archived_at)}
                            </span>
                          </div>
                        )}
                      </div>

                      {comparison && (
                        <div className="mt-3 pt-3 border-t">
                          <div className="flex flex-wrap gap-2 text-xs">
                            {comparison.sizeChanged && (
                              <Badge variant={comparison.sizeIncreased ? 'default' : 'secondary'}>
                                Size {comparison.sizeIncreased ? '+' : '-'}{comparison.sizeDiff}
                              </Badge>
                            )}
                            {comparison.contentChanged && (
                              <Badge variant="destructive">
                                Content Changed
                              </Badge>
                            )}
                            {!comparison.contentChanged && (
                              <Badge variant="outline">
                                Content Identical
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Version Comparison */}
      {selectedDocument && versions.length >= 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Version Comparison</CardTitle>
            <CardDescription>
              Compare file hashes and sizes between versions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="hash" className="w-full">
              <TabsList>
                <TabsTrigger value="hash">Hash Comparison</TabsTrigger>
                <TabsTrigger value="size">Size Comparison</TabsTrigger>
              </TabsList>

              <TabsContent value="hash" className="mt-4">
                <div className="space-y-2">
                  {versions.map((version, index) => {
                    const prevVersion = versions[index + 1];
                    const hashChanged = prevVersion ? version.file_hash !== prevVersion.file_hash : false;
                    
                    return (
                      <div key={version.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline">v{version.version_number}</Badge>
                          <span className="font-mono text-sm">{version.file_hash}</span>
                        </div>
                        {hashChanged && (
                          <Badge variant="destructive">Changed</Badge>
                        )}
                      </div>
                    );
                  })}
                </div>
              </TabsContent>

              <TabsContent value="size" className="mt-4">
                <div className="space-y-2">
                  {versions.map((version, index) => {
                    const prevVersion = versions[index + 1];
                    const sizeDiff = prevVersion ? version.file_size - prevVersion.file_size : 0;
                    
                    return (
                      <div key={version.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 rounded">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline">v{version.version_number}</Badge>
                          <span className="text-sm">{formatFileSize(version.file_size)}</span>
                        </div>
                        {sizeDiff !== 0 && (
                          <Badge variant={sizeDiff > 0 ? 'default' : 'secondary'}>
                            {sizeDiff > 0 ? '+' : ''}{formatFileSize(sizeDiff)}
                          </Badge>
                        )}
                      </div>
                    );
                  })}
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
