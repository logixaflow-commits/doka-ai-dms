import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Brain, 
  Tag, 
  Sparkles, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle,
  Calendar,
  FileText,
  Hash,
  DollarSign,
  Ship,
  Shield,
  Clock
} from 'lucide-react';

const API_BASE = '/api';

interface AITagResult {
  document_id: number;
  entities: {
    suppliers?: string[];
    dates?: string[];
    amounts?: string[];
    bl_numbers?: string[];
    nrcs?: string[];
    customs_codes?: string[];
    container_numbers?: string[];
  };
  tags: string[];
  urgency: 'urgent' | 'normal' | 'low';
  confidence: number;
  processing_time: number;
}

interface Document {
  id: number;
  original_filename: string;
  category: string | null;
  ocr_text?: string;
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

const URGENCY_COLORS = {
  urgent: 'bg-red-100 text-red-800',
  normal: 'bg-blue-100 text-blue-800',
  low: 'bg-green-100 text-green-800',
};

export default function AITagging() {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [tagResult, setTagResult] = useState<AITagResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [autoTaggingEnabled, setAutoTaggingEnabled] = useState(false);

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

  async function tagDocument(docId: number) {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/tags/auto-tag/${docId}`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        setTagResult(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to tag document');
      }
    } catch (err) {
      setError('Error tagging document');
      console.error('Failed to tag document:', err);
    } finally {
      setLoading(false);
    }
  }

  async function batchTagDocuments() {
    if (documents.length === 0) return;
    
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/tags/batch-tag`, {
        method: 'POST',
        body: JSON.stringify({ document_ids: documents.map(d => d.id) }),
      });

      if (response.ok) {
        const data = await response.json();
        setTagResult(data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to batch tag documents');
      }
    } catch (err) {
      setError('Error batch tagging documents');
      console.error('Failed to batch tag documents:', err);
    } finally {
      setLoading(false);
    }
  }

  async function toggleAutoTagging() {
    try {
      const response = await apiFetch(`${API_BASE}/tags/settings`, {
        method: 'PUT',
        body: JSON.stringify({ auto_tagging_enabled: !autoTaggingEnabled }),
      });

      if (response.ok) {
        setAutoTaggingEnabled(!autoTaggingEnabled);
      }
    } catch (err) {
      console.error('Failed to toggle auto-tagging:', err);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">AI Tagging</h2>
          <p className="text-slate-500 dark:text-slate-400">
            AI-powered automatic document tagging and entity extraction
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadDocuments} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button
            onClick={toggleAutoTagging}
            variant={autoTaggingEnabled ? "default" : "outline"}
            size="sm"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            {autoTaggingEnabled ? 'Auto-Tagging ON' : 'Auto-Tagging OFF'}
          </Button>
        </div>
      </div>

      {/* Auto-Tagging Status */}
      {autoTaggingEnabled && (
        <Alert>
          <Brain className="h-4 w-4" />
          <AlertDescription>
            Auto-tagging is enabled. New documents will be automatically tagged during upload.
          </AlertDescription>
        </Alert>
      )}

      {/* Document Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Select Document to Tag
          </CardTitle>
          <CardDescription>
            Choose a document to analyze with AI tagging
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Input
              placeholder="Search documents..."
              onChange={(e) => {
                const query = e.target.value.toLowerCase();
                const filtered = documents.filter(doc => 
                  doc.original_filename.toLowerCase().includes(query)
                );
                setDocuments(filtered);
              }}
            />
            <div className="max-h-64 overflow-y-auto space-y-2">
              {documents.map(doc => (
                <div
                  key={doc.id}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedDocument?.id === doc.id
                      ? 'bg-blue-50 dark:bg-blue-950 border-blue-500'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-900'
                  }`}
                  onClick={() => setSelectedDocument(doc)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-slate-400" />
                      <span className="font-medium">{doc.original_filename}</span>
                    </div>
                    {doc.category && (
                      <Badge variant="outline">{doc.category}</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-4">
              <Button
                onClick={() => selectedDocument && tagDocument(selectedDocument.id)}
                disabled={!selectedDocument || loading}
              >
                <Tag className="w-4 h-4 mr-2" />
                Tag Document
              </Button>
              <Button
                onClick={batchTagDocuments}
                disabled={loading}
                variant="outline"
              >
                <Sparkles className="w-4 h-4 mr-2" />
                Batch Tag All
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Tagging Results */}
      {tagResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5" />
              AI Tagging Results
            </CardTitle>
            <CardDescription>
              Entity extraction and automatic classification results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="entities" className="w-full">
              <TabsList>
                <TabsTrigger value="entities">Extracted Entities</TabsTrigger>
                <TabsTrigger value="tags">Generated Tags</TabsTrigger>
                <TabsTrigger value="metadata">Metadata</TabsTrigger>
              </TabsList>

              {/* Entities Tab */}
              <TabsContent value="entities" className="mt-4">
                <div className="space-y-4">
                  {tagResult.entities.suppliers && tagResult.entities.suppliers.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Ship className="w-4 h-4 text-blue-500" />
                        Suppliers
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.suppliers.map((supplier, index) => (
                          <Badge key={index} variant="secondary">
                            {supplier}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagResult.entities.dates && tagResult.entities.dates.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-green-500" />
                        Dates
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.dates.map((date, index) => (
                          <Badge key={index} variant="outline">
                            {date}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagResult.entities.amounts && tagResult.entities.amounts.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-amber-500" />
                        Amounts
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.amounts.map((amount, index) => (
                          <Badge key={index} variant="outline">
                            {amount}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagResult.entities.bl_numbers && tagResult.entities.bl_numbers.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Hash className="w-4 h-4 text-purple-500" />
                        Bill of Lading Numbers
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.bl_numbers.map((bl, index) => (
                          <Badge key={index} variant="outline">
                            {bl}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagResult.entities.nrcs && tagResult.entities.nrcs.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-red-500" />
                        NRC Numbers
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.nrcs.map((nrc, index) => (
                          <Badge key={index} variant="outline">
                            {nrc}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagResult.entities.customs_codes && tagResult.entities.customs_codes.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-indigo-500" />
                        Customs Codes
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.customs_codes.map((code, index) => (
                          <Badge key={index} variant="outline">
                            {code}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {tagResult.entities.container_numbers && tagResult.entities.container_numbers.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2 flex items-center gap-2">
                        <Ship className="w-4 h-4 text-teal-500" />
                        Container Numbers
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {tagResult.entities.container_numbers.map((container, index) => (
                          <Badge key={index} variant="outline">
                            {container}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Tags Tab */}
              <TabsContent value="tags" className="mt-4">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <Tag className="w-4 h-4 text-slate-500" />
                      Generated Tags
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {tagResult.tags.map((tag, index) => (
                        <Badge key={index} variant="secondary">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-slate-500" />
                      Urgency Classification
                    </h4>
                    <Badge className={URGENCY_COLORS[tagResult.urgency]}>
                      {tagResult.urgency.charAt(0).toUpperCase() + tagResult.urgency.slice(1)}
                    </Badge>
                  </div>
                </div>
              </TabsContent>

              {/* Metadata Tab */}
              <TabsContent value="metadata" className="mt-4">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="font-medium mb-2">Confidence Score</h4>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-slate-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${tagResult.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">
                          {(tagResult.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium mb-2">Processing Time</h4>
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        {tagResult.processing_time.toFixed(2)}s
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Success Display */}
      {tagResult && !error && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            Document tagged successfully with {tagResult.tags.length} tags and {Object.keys(tagResult.entities).length} entity types extracted.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
