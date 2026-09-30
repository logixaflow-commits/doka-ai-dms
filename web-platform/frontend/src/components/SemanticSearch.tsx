import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { 
  Search, 
  Brain, 
  FileText, 
  Star, 
  Sparkles,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Filter
} from 'lucide-react';

const API_BASE = '/api';

interface SearchResult {
  document_id: number;
  filename: string;
  category: string | null;
  similarity_score: number;
  snippet: string;
  metadata?: {
    supplier?: string;
    amount?: string;
    date?: string;
  };
}

interface SemanticSearchResponse {
  results: SearchResult[];
  query_embedding_size: number;
  search_time: number;
  total_results: number;
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

export default function SemanticSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<'semantic' | 'keyword'>('semantic');
  const [useHybrid, setUseHybrid] = useState(true);
  const [minSimilarity, setMinSimilarity] = useState(0.5);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [totalResults, setTotalResults] = useState(0);

  async function performSearch() {
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError(null);
      setResults([]);

      const params = new URLSearchParams({
        query: query,
        mode: searchMode,
        min_similarity: minSimilarity.toString(),
        hybrid: useHybrid.toString(),
      });

      const response = await apiFetch(`${API_BASE}/search/semantic?${params.toString()}`);

      if (response.ok) {
        const data: SemanticSearchResponse = await response.json();
        setResults(data.results || []);
        setSearchTime(data.search_time);
        setTotalResults(data.total_results);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Search failed');
      }
    } catch (err) {
      setError('Error performing search');
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyPress(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      performSearch();
    }
  }

  function getSimilarityColor(score: number) {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-blue-100 text-blue-800';
    if (score >= 0.4) return 'bg-amber-100 text-amber-800';
    return 'bg-gray-100 text-gray-800';
  }

  function getSimilarityLabel(score: number) {
    if (score >= 0.8) return 'Very High';
    if (score >= 0.6) return 'High';
    if (score >= 0.4) return 'Medium';
    return 'Low';
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Semantic Search</h2>
          <p className="text-slate-500 dark:text-slate-400">
            AI-powered intelligent document search using vector embeddings
          </p>
        </div>
        <Button onClick={performSearch} variant="outline" size="sm" disabled={loading}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Search Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Search Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="search" className="w-full">
            <TabsList>
              <TabsTrigger value="search">Search</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>

            <TabsContent value="search" className="mt-4">
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
                  <Input
                    placeholder="Enter your search query... (e.g., 'invoice from Myanmar Logistics', 'FDA approval documents')"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="pl-10 text-lg"
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={performSearch} disabled={loading || !query.trim()} className="flex-1">
                    {searchMode === 'semantic' ? (
                      <>
                        <Brain className="w-4 h-4 mr-2" />
                        Semantic Search
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4 mr-2" />
                        Keyword Search
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => setSearchMode(searchMode === 'semantic' ? 'keyword' : 'semantic')}
                    variant="outline"
                  >
                    {searchMode === 'semantic' ? 'Switch to Keyword' : 'Switch to Semantic'}
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="settings" className="mt-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Hybrid Search</div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      Combine semantic and keyword search for better results
                    </div>
                  </div>
                  <Switch
                    checked={useHybrid}
                    onCheckedChange={setUseHybrid}
                  />
                </div>
                <div className="space-y-2">
                  <div className="font-medium">Minimum Similarity Score</div>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={minSimilarity}
                      onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-sm font-medium w-16 text-right">
                      {(minSimilarity * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-sm text-slate-500 dark:text-slate-400">
                    Only show documents with similarity above this threshold
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Search Results */}
      {results.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Search Results
              </CardTitle>
              <div className="flex items-center gap-4 text-sm text-slate-500">
                {searchTime !== null && (
                  <span>Search time: {searchTime.toFixed(2)}s</span>
                )}
                <span>Total results: {totalResults}</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {results.map((result, index) => (
                <div
                  key={result.document_id}
                  className="p-4 border rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-slate-400" />
                      <div>
                        <div className="font-medium">{result.filename}</div>
                        {result.category && (
                          <Badge variant="outline" className="mt-1">
                            {result.category}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4 text-amber-500" />
                      <span className="font-medium">
                        {(result.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={getSimilarityColor(result.similarity_score)}>
                      {getSimilarityLabel(result.similarity_score)}
                    </Badge>
                    <Badge variant="outline">
                      Rank #{index + 1}
                    </Badge>
                  </div>

                  {result.snippet && (
                    <div className="bg-slate-50 dark:bg-slate-900 p-3 rounded-lg mt-2">
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {result.snippet}
                      </p>
                    </div>
                  )}

                  {result.metadata && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {result.metadata.supplier && (
                        <Badge variant="secondary">
                          Supplier: {result.metadata.supplier}
                        </Badge>
                      )}
                      {result.metadata.amount && (
                        <Badge variant="secondary">
                          Amount: {result.metadata.amount}
                        </Badge>
                      )}
                      {result.metadata.date && (
                        <Badge variant="secondary">
                          Date: {result.metadata.date}
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && query && (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">
              No Results Found
            </h3>
            <p className="text-slate-500 dark:text-slate-400">
              Try adjusting your search query or lowering the similarity threshold
            </p>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {loading && (
        <Card>
          <CardContent className="py-12 text-center">
            <div className="flex items-center justify-center gap-3">
              <Sparkles className="w-5 h-5 text-blue-500 animate-spin" />
              <span className="text-slate-500">Searching documents...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50 dark:bg-red-950">
          <CardContent className="py-6">
            <div className="flex items-center gap-3 text-red-700 dark:text-red-400">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Initial State */}
      {!query && !loading && (
        <Card>
          <CardContent className="py-12 text-center">
            <Brain className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-2">
              Semantic Search Ready
            </h3>
            <p className="text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Enter a natural language query to find similar documents using AI-powered vector embeddings.
              Try searching for concepts like "FDA approval", "logistics invoices", or "Myanmar customs".
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
