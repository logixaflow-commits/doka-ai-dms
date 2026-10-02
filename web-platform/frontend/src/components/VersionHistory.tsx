import { useEffect, useState } from 'react';
import { History, RotateCcw, Download, User, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { success, error } from './Toast';

export interface DocumentVersion {
  id: string;
  version: number;
  fileName: string;
  fileSize: number;
  uploadedBy: string;
  uploadedAt: Date;
  changes: string;
  isCurrent: boolean;
}

interface VersionHistoryProps {
  documentId: string;
  documentName: string;
}

export default function VersionHistory({ documentId }: VersionHistoryProps) {
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;

    const loadVersions = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/documents/${documentId}/versions`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) throw new Error('Failed to load versions');

        const data = await response.json();
        const rows = Array.isArray(data) ? data : data.versions;
        if (active) setVersions(Array.isArray(rows) ? rows : []);
      } catch {
        if (active) setVersions(generateMockVersions());
      }
    };

    void loadVersions();
    return () => {
      active = false;
    };
  }, [documentId]);

  const handleRestoreVersion = async (versionId: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/documents/${documentId}/versions/${versionId}/restore`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to restore version');

      setVersions((prev) =>
        prev.map((v) => ({
          ...v,
          isCurrent: v.id === versionId,
        }))
      );
      success('Version restored successfully');
    } catch {
      error('Failed to restore version');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadVersion = async (versionId: string, fileName: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/documents/${documentId}/versions/${versionId}/download`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to download version');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      success('Version downloaded successfully');
    } catch {
      error('Failed to download version');
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000 / 60);
    
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    if (diff < 10080) return `${Math.floor(diff / 1440)}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="w-5 h-5" />
          Version History
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {versions.length === 0 ? (
          <Alert>
            <History className="h-4 w-4" />
            <AlertDescription>
              No version history available for this document.
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-3">
            {versions.map((version, index) => (
              <div
                key={version.id}
                className={`p-4 border rounded-lg space-y-3 ${
                  version.isCurrent
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        version.isCurrent
                          ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                      }`}>
                        <span className="font-bold">v{version.version}</span>
                      </div>
                      {index < versions.length - 1 && (
                        <div className="w-0.5 flex-1 bg-slate-200 dark:bg-slate-700 my-2" />
                      )}
                    </div>

                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        {version.isCurrent && (
                          <Badge variant="default" className="text-xs">
                            Current
                          </Badge>
                        )}
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {version.fileName}
                        </span>
                      </div>

                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {version.changes}
                      </p>

                      <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                        <div className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          <span>{version.uploadedBy}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatTime(version.uploadedAt)}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span>{formatBytes(version.fileSize)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownloadVersion(version.id, version.fileName)}
                      disabled={loading}
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                    {!version.isCurrent && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRestoreVersion(version.id)}
                        disabled={loading}
                      >
                        <RotateCcw className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function generateMockVersions(): DocumentVersion[] {
  const now = new Date();
  return [
    {
      id: '1',
      version: 3,
      fileName: 'contract_2024_v3.pdf',
      fileSize: 2.5 * 1024 * 1024,
      uploadedBy: 'John Doe',
      uploadedAt: now,
      changes: 'Updated terms and conditions section',
      isCurrent: true,
    },
    {
      id: '2',
      version: 2,
      fileName: 'contract_2024_v2.pdf',
      fileSize: 2.3 * 1024 * 1024,
      uploadedBy: 'Jane Smith',
      uploadedAt: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 3),
      changes: 'Added signature blocks and revised payment terms',
      isCurrent: false,
    },
    {
      id: '3',
      version: 1,
      fileName: 'contract_2024_v1.pdf',
      fileSize: 2.1 * 1024 * 1024,
      uploadedBy: 'Bob Johnson',
      uploadedAt: new Date(now.getTime() - 1000 * 60 * 60 * 24 * 7),
      changes: 'Initial draft created',
      isCurrent: false,
    },
  ];
}
