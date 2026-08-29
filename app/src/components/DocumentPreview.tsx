import { useState, useRef, useEffect } from 'react';
import { 
  FileText, 
  ZoomIn, 
  ZoomOut, 
  RotateCw, 
  Download, 
  Share2, 
  Maximize2, 
  Minimize2,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface DocumentPreviewProps {
  documentId: string;
  documentName: string;
  documentUrl: string;
  fileType: string;
  onClose?: () => void;
}

export default function DocumentPreview({ 
  documentId, 
  documentName, 
  documentUrl, 
  fileType,
  onClose 
}: DocumentPreviewProps) {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      setLoading(false);
    };
    img.onerror = () => {
      setLoading(false);
      setError(true);
    };
    
    if (fileType.startsWith('image/')) {
      img.src = documentUrl;
    } else {
      setLoading(false);
    }
  }, [documentUrl, fileType]);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 25));
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);
  const handleReset = () => {
    setZoom(100);
    setRotation(0);
  };

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = documentUrl;
    a.download = documentName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };


  const toggleFullscreen = () => {
    if (!isFullscreen) {
      containerRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
    setIsFullscreen(!isFullscreen);
  };

  const renderPreview = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-full min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-slate-500">
          <FileText className="w-12 h-12 mb-2" />
          <p>Preview not available</p>
          <Button onClick={handleDownload} variant="outline" size="sm" className="mt-4">
            <Download className="w-4 h-4 mr-2" />
            Download File
          </Button>
        </div>
      );
    }

    if (fileType === 'application/pdf') {
      return (
        <iframe
          src={documentUrl}
          className="w-full h-full min-h-[600px] border-0"
          title={documentName}
        />
      );
    }

    if (fileType.startsWith('image/')) {
      return (
        <div className="flex items-center justify-center h-full min-h-[400px] bg-slate-100 dark:bg-slate-800 rounded-lg overflow-hidden">
          <img
            src={documentUrl}
            alt={documentName}
            className="max-w-full max-h-full object-contain transition-transform"
            style={{
              transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
            }}
          />
        </div>
      );
    }

    if (fileType.includes('word') || fileType.includes('document')) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-slate-500">
          <FileText className="w-12 h-12 mb-2" />
          <p>Word document preview</p>
          <p className="text-sm mt-1">Download to view full content</p>
          <Button onClick={handleDownload} variant="outline" size="sm" className="mt-4">
            <Download className="w-4 h-4 mr-2" />
            Download File
          </Button>
        </div>
      );
    }

    if (fileType.includes('excel') || fileType.includes('spreadsheet')) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-slate-500">
          <FileText className="w-12 h-12 mb-2" />
          <p>Excel spreadsheet preview</p>
          <p className="text-sm mt-1">Download to view full content</p>
          <Button onClick={handleDownload} variant="outline" size="sm" className="mt-4">
            <Download className="w-4 h-4 mr-2" />
            Download File
          </Button>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-slate-500">
        <FileText className="w-12 h-12 mb-2" />
        <p>Preview not available for this file type</p>
        <Button onClick={handleDownload} variant="outline" size="sm" className="mt-4">
          <Download className="w-4 h-4 mr-2" />
          Download File
        </Button>
      </div>
    );
  };

  return (
    <Card className={cn("w-full", isFullscreen && "fixed inset-0 z-50 m-0 rounded-none")}>
      <CardContent className="p-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2 flex-1">
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            )}
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400" />
              <Input
                placeholder="Search in document..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              Page {currentPage} of {totalPages}
            </Badge>
            <Button variant="ghost" size="sm" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleZoomOut} disabled={zoom <= 25}>
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
            <Button variant="ghost" size="sm" onClick={handleZoomIn} disabled={zoom >= 200}>
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleRotate}>
              <RotateCw className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleReset}>
              Reset
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleDownload}>
              <Download className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Share2 className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={toggleFullscreen}>
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Preview Area */}
        <div ref={containerRef} className="relative bg-slate-50 dark:bg-slate-900">
          {renderPreview()}
        </div>

        {/* Footer Info */}
        <div className="flex items-center justify-between p-3 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
          <span>{documentName}</span>
          <span>{fileType}</span>
        </div>
      </CardContent>
    </Card>
  );
}
