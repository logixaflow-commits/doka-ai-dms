import { useState } from 'react';
import { Share2, Clock, Copy, Check, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { success, error } from './Toast';

interface SharedLink {
  id: string;
  url: string;
  expiresAt: Date;
  createdAt: Date;
  accessCount: number;
}

interface DocumentSharingProps {
  documentId: string;
  documentName: string;
}

export default function DocumentSharing({ documentId }: DocumentSharingProps) {
  const [sharedLinks, setSharedLinks] = useState<SharedLink[]>([]);
  const [newLinkExpiry, setNewLinkExpiry] = useState('24h');
  const [customExpiryDate, setCustomExpiryDate] = useState('');
  const [copiedLinkId, setCopiedLinkId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const expiryOptions = [
    { value: '1h', label: '1 hour' },
    { value: '24h', label: '24 hours' },
    { value: '7d', label: '7 days' },
    { value: '30d', label: '30 days' },
    { value: 'custom', label: 'Custom date' },
  ];

  const generateShareLink = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      let expiresAt: Date;

      if (newLinkExpiry === 'custom') {
        expiresAt = new Date(customExpiryDate);
      } else {
        const now = new Date();
        const value = parseInt(newLinkExpiry);
        const unit = newLinkExpiry.slice(-1);
        
        if (unit === 'h') {
          expiresAt = new Date(now.getTime() + value * 60 * 60 * 1000);
        } else if (unit === 'd') {
          expiresAt = new Date(now.getTime() + value * 24 * 60 * 60 * 1000);
        } else {
          expiresAt = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        }
      }

      const response = await fetch('/api/documents/share', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          document_id: documentId,
          expires_at: expiresAt.toISOString(),
        }),
      });

      if (!response.ok) throw new Error('Failed to generate share link');

      const data = await response.json();
      const newLink: SharedLink = {
        id: data.id,
        url: data.url,
        expiresAt: new Date(expiresAt),
        createdAt: new Date(),
        accessCount: 0,
      };

      setSharedLinks((prev) => [newLink, ...prev]);
      success('Share link generated successfully');
    } catch {
      error('Failed to generate share link');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (link: SharedLink) => {
    try {
      await navigator.clipboard.writeText(link.url);
      setCopiedLinkId(link.id);
      success('Link copied to clipboard');
      setTimeout(() => setCopiedLinkId(null), 2000);
    } catch {
      error('Failed to copy link');
    }
  };

  const revokeLink = async (linkId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/documents/share/${linkId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to revoke link');

      setSharedLinks((prev) => prev.filter((link) => link.id !== linkId));
      success('Share link revoked');
    } catch {
      error('Failed to revoke link');
    }
  };

  const formatExpiry = (date: Date) => {
    const now = new Date();
    const diff = date.getTime() - now.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
    return 'Less than 1 hour';
  };

  const isExpired = (date: Date) => new Date() > date;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Share2 className="w-5 h-5" />
          Share Document
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Generate New Link */}
        <div className="space-y-4 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Generate New Share Link</h3>
          
          <div className="space-y-2">
            <Label>Expiration Time</Label>
            <Select value={newLinkExpiry} onValueChange={setNewLinkExpiry}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {expiryOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {newLinkExpiry === 'custom' && (
            <div className="space-y-2">
              <Label>Custom Expiration Date</Label>
              <Input
                type="datetime-local"
                value={customExpiryDate}
                onChange={(e) => setCustomExpiryDate(e.target.value)}
                className="w-full"
              />
            </div>
          )}

          <Button onClick={generateShareLink} disabled={loading} className="w-full">
            <Share2 className="w-4 h-4 mr-2" />
            {loading ? 'Generating...' : 'Generate Share Link'}
          </Button>
        </div>

        {/* Active Share Links */}
        {sharedLinks.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-medium text-slate-900 dark:text-slate-100">Active Share Links</h3>
            
            {sharedLinks.map((link) => (
              <div
                key={link.id}
                className={`p-4 border rounded-lg space-y-3 ${
                  isExpired(link.expiresAt)
                    ? 'border-slate-200 dark:border-slate-700 opacity-60'
                    : 'border-slate-300 dark:border-slate-600'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Clock className="w-4 h-4 text-slate-500" />
                      <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {isExpired(link.expiresAt) ? 'Expired' : 'Active'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Expires in {formatExpiry(link.expiresAt)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Accessed {link.accessCount} time{link.accessCount !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <Button
                    onClick={() => revokeLink(link.id)}
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <div className="flex gap-2">
                  <Input
                    value={link.url}
                    readOnly
                    className="flex-1 text-sm"
                  />
                  <Button
                    onClick={() => copyToClipboard(link)}
                    variant="outline"
                    size="sm"
                  >
                    {copiedLinkId === link.id ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {sharedLinks.length === 0 && (
          <Alert>
            <Share2 className="h-4 w-4" />
            <AlertDescription>
              No active share links for this document. Generate one to share with others.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
