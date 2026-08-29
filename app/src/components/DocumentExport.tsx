import { useState } from 'react';
import { Download, FileText, Share2, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { success, error } from './Toast';

interface DocumentExportProps {
  documentId: string;
  documentName: string;
  documentUrl: string;
}

export function DocumentDownload({ documentId, documentName, documentUrl }: DocumentExportProps) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(documentUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = documentName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      success('Document downloaded successfully');
    } catch (err) {
      error('Failed to download document');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Button
      onClick={handleDownload}
      disabled={downloading}
      variant="outline"
      size="sm"
    >
      <Download className="w-4 h-4 mr-2" />
      {downloading ? 'Downloading...' : 'Download'}
    </Button>
  );
}

export function DocumentShare({ documentId, documentName }: DocumentExportProps) {
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState('');

  const generateShareLink = () => {
    const url = `${window.location.origin}/documents/${documentId}`;
    setShareUrl(url);
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      success('Link copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      error('Failed to copy link');
    }
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Share2 className="w-5 h-5 text-slate-600 dark:text-slate-400" />
          <h4 className="font-medium text-slate-900 dark:text-slate-100">Share Document</h4>
        </div>

        {!shareUrl ? (
          <Button onClick={generateShareLink} className="w-full" variant="outline">
            <Share2 className="w-4 h-4 mr-2" />
            Generate Share Link
          </Button>
        ) : (
          <div className="space-y-3">
            <Alert>
              <FileText className="h-4 w-4" />
              <AlertDescription className="text-sm">
                Share link for <strong>{documentName}</strong>
              </AlertDescription>
            </Alert>

            <div className="flex gap-2">
              <input
                type="text"
                value={shareUrl}
                readOnly
                className="flex-1 px-3 py-2 text-sm border rounded-md bg-slate-50 dark:bg-slate-800 border-slate-300 dark:border-slate-600"
              />
              <Button onClick={copyToClipboard} size="sm">
                {copied ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400">
              This link provides access to the document. Share it responsibly.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DocumentExportMenu({ documentId, documentName, documentUrl }: DocumentExportProps) {
  const [showShare, setShowShare] = useState(false);

  return (
    <div className="relative">
      <div className="flex gap-2">
        <DocumentDownload
          documentId={documentId}
          documentName={documentName}
          documentUrl={documentUrl}
        />
        <Button
          onClick={() => setShowShare(!showShare)}
          variant="outline"
          size="sm"
        >
          <Share2 className="w-4 h-4" />
        </Button>
      </div>

      {showShare && (
        <div className="absolute right-0 top-12 z-50">
          <DocumentShare
            documentId={documentId}
            documentName={documentName}
            documentUrl={documentUrl}
          />
        </div>
      )}
    </div>
  );
}
