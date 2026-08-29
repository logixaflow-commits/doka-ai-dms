import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { X, Search, Filter, Calendar, FileText, User, Hash, Save, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';

interface AdvancedSearchProps {
  onSearch: (filters: SearchFilters) => void;
}

export interface SearchFilters {
  query: string;
  category: string;
  status: string;
  dateFrom: string;
  dateTo: string;
  uploader: string;
  minSize: number;
  maxSize: number;
  fileType: string;
}

const CATEGORIES = [
  'Invoice', 'Bill of Lading', 'NRC', 'FDA', 'Customs', 'Contract', 
  'Receipt', 'Purchase Order', 'Shipping Label', 'Other'
];

const STATUSES = [
  'pending', 'processing', 'completed', 'approved', 'rejected', 
  'duplicate', 'unknown', 'review', 'failed'
];

const FILE_TYPES = [
  'application/pdf', 'image/png', 'image/jpeg', 'image/tiff', 
  'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
];

export default function AdvancedSearch({ onSearch }: AdvancedSearchProps) {
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    category: '',
    status: '',
    dateFrom: '',
    dateTo: '',
    uploader: '',
    minSize: 0,
    maxSize: 0,
    fileType: '',
  });

  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [savedSearches, setSavedSearches] = useState<SearchFilters[]>([]);

  const updateFilter = (key: keyof SearchFilters, value: string | number) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    
    // Update active filters
    const active = Object.entries(newFilters)
      .filter(([k, v]) => v !== '' && v !== 0 && k !== 'query')
      .map(([k]) => k);
    setActiveFilters(active);
  };

  const clearFilter = (key: keyof SearchFilters) => {
    updateFilter(key, key === 'minSize' || key === 'maxSize' ? 0 : '');
  };

  const clearAllFilters = () => {
    setFilters({
      query: '',
      category: '',
      status: '',
      dateFrom: '',
      dateTo: '',
      uploader: '',
      minSize: 0,
      maxSize: 0,
      fileType: '',
    });
    setActiveFilters([]);
  };

  const saveSearch = () => {
    if (activeFilters.length > 0) {
      setSavedSearches([...savedSearches, filters]);
    }
  };

  const loadSavedSearch = (savedFilters: SearchFilters) => {
    setFilters(savedFilters);
    const active = Object.entries(savedFilters)
      .filter(([k, v]) => v !== '' && v !== 0 && k !== 'query')
      .map(([k]) => k);
    setActiveFilters(active);
  };

  const handleSearch = () => {
    onSearch(filters);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Advanced Search
          </CardTitle>
          <div className="flex gap-2">
            {activeFilters.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearAllFilters}>
                <RotateCcw className="w-4 h-4 mr-1" />
                Reset
              </Button>
            )}
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Saved Searches */}
        {savedSearches.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {savedSearches.map((search, index) => (
              <Badge key={index} variant="outline" className="cursor-pointer hover:bg-slate-100">
                <Save className="w-3 h-3 mr-1" />
                Saved Search {index + 1}
              </Badge>
            ))}
          </div>
        )}

        {/* Active Filters */}
        {activeFilters.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {activeFilters.map((filter) => (
              <Badge key={filter} variant="secondary" className="gap-1">
                {filter}
                <X 
                  className="w-3 h-3 cursor-pointer" 
                  onClick={() => clearFilter(filter as keyof SearchFilters)}
                />
              </Badge>
            ))}
          </div>
        )}

        {/* Main Search */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              placeholder="Search documents by filename, content, or metadata..."
              value={filters.query}
              onChange={(e) => updateFilter('query', e.target.value)}
              className="pl-10"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <Button onClick={handleSearch}>
            Search
          </Button>
          {activeFilters.length > 0 && (
            <Button variant="outline" onClick={saveSearch}>
              <Save className="w-4 h-4 mr-2" />
              Save
            </Button>
          )}
        </div>

        {/* Advanced Filters */}
        <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${!isExpanded ? 'hidden' : ''}`}>
          {/* Category */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Category
            </Label>
            <Select
              value={filters.category}
              onValueChange={(value) => updateFilter('category', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Categories</SelectItem>
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Hash className="w-4 h-4" />
              Status
            </Label>
            <Select
              value={filters.status}
              onValueChange={(value) => updateFilter('status', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Statuses</SelectItem>
                {STATUSES.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* File Type */}
          <div className="space-y-2">
            <Label>File Type</Label>
            <Select
              value={filters.fileType}
              onValueChange={(value) => updateFilter('fileType', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select file type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                {FILE_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.split('/')[1]?.toUpperCase() || type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Date Range */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Date Range
            </Label>
            <div className="flex gap-2">
              <Input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => updateFilter('dateFrom', e.target.value)}
                className="flex-1"
              />
              <Input
                type="date"
                value={filters.dateTo}
                onChange={(e) => updateFilter('dateTo', e.target.value)}
                className="flex-1"
              />
            </div>
          </div>

          {/* Uploader */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <User className="w-4 h-4" />
              Uploader
            </Label>
            <Input
              placeholder="Username"
              value={filters.uploader}
              onChange={(e) => updateFilter('uploader', e.target.value)}
            />
          </div>

          {/* File Size Range */}
          <div className="space-y-2">
            <Label>File Size Range (MB)</Label>
            <div className="flex gap-2 items-center">
              <Input
                type="number"
                placeholder="Min"
                value={filters.minSize || ''}
                onChange={(e) => updateFilter('minSize', parseFloat(e.target.value) || 0)}
                className="flex-1"
              />
              <span className="text-slate-400">-</span>
              <Input
                type="number"
                placeholder="Max"
                value={filters.maxSize || ''}
                onChange={(e) => updateFilter('maxSize', parseFloat(e.target.value) || 0)}
                className="flex-1"
              />
            </div>
          </div>
        </div>

        {/* Search Stats */}
        <div className="text-sm text-slate-500 dark:text-slate-400">
          {activeFilters.length > 0 ? (
            <span>{activeFilters.length} filter(s) applied</span>
          ) : (
            <span>No filters applied</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
