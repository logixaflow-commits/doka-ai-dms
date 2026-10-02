import { useState, useRef } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload, X, CheckCircle, AlertCircle, FileText } from 'lucide-react';

const API_BASE = '/api';

interface UploadFile {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

function getToken() {
  return localStorage.getItem('access_token');
}

export default function DocumentUpload() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles: UploadFile[] = selectedFiles.map(file => ({
      file,
      progress: 0,
      status: 'pending',
    }));
    setFiles(prev => [...prev, ...newFiles]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFiles = Array.from(e.dataTransfer.files || []);
    const newFiles: UploadFile[] = droppedFiles.map(file => ({
      file,
      progress: 0,
      status: 'pending',
    }));
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFile = async (uploadFile: UploadFile, index: number) => {
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, status: 'uploading', progress: 0 } : f
    ));

    const formData = new FormData();
    formData.append('file', uploadFile.file);

    try {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const progress = (e.loaded / e.total) * 100;
          setFiles(prev => prev.map((f, i) => 
            i === index ? { ...f, progress } : f
          ));
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          setFiles(prev => prev.map((f, i) => 
            i === index ? { ...f, status: 'success', progress: 100 } : f
          ));
        } else {
          setFiles(prev => prev.map((f, i) => 
            i === index ? { ...f, status: 'error', error: 'Upload failed' } : f
          ));
        }
      };

      xhr.onerror = () => {
        setFiles(prev => prev.map((f, i) => 
          i === index ? { ...f, status: 'error', error: 'Network error' } : f
        ));
      };

      xhr.open('POST', `${API_BASE}/documents/upload`);
      const token = getToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      xhr.send(formData);

    } catch {
      setFiles(prev => prev.map((f, i) => 
        i === index ? { ...f, status: 'error', error: 'Upload error' } : f
      ));
    }
  };

  const handleUploadAll = async () => {
    setUploading(true);
    
    for (let i = 0; i < files.length; i++) {
      if (files[i].status === 'pending') {
        await uploadFile(files[i], i);
      }
    }
    
    setUploading(false);
  };

  const handleDone = () => {
    navigate('/documents');
  };

  const pendingCount = files.filter(f => f.status === 'pending').length;
  const successCount = files.filter(f => f.status === 'success').length;
  const errorCount = files.filter(f => f.status === 'error').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Upload Documents</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Upload and process your documents</p>
        </div>
        <Button onClick={() => navigate('/documents')} variant="outline">
          Cancel
        </Button>
      </div>

      {/* Upload Area */}
      <Card>
        <CardContent className="p-6">
          <div
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center cursor-pointer hover:border-blue-400 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
            <p className="text-slate-600 dark:text-slate-400 mb-2">
              Drag and drop files here, or click to select
            </p>
            <p className="text-sm text-slate-400">
              Supports PDF, images, and other document formats
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp"
            />
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>Files ({files.length})</CardTitle>
              <div className="flex gap-2">
                {!uploading && pendingCount > 0 && (
                  <Button onClick={handleUploadAll} size="sm">
                    Upload All ({pendingCount})
                  </Button>
                )}
                {uploading && (
                  <Button disabled size="sm">
                    Uploading...
                  </Button>
                )}
                {!uploading && successCount > 0 && errorCount === 0 && (
                  <Button onClick={handleDone} size="sm">
                    Done
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {files.map((uploadFile, index) => (
                <div key={index} className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
                  <FileText className="w-8 h-8 text-slate-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium truncate">{uploadFile.file.name}</p>
                      <div className="flex items-center gap-2">
                        {uploadFile.status === 'success' && (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        )}
                        {uploadFile.status === 'error' && (
                          <AlertCircle className="w-5 h-5 text-red-500" />
                        )}
                        <Button
                          onClick={() => removeFile(index)}
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="text-sm text-slate-500">
                        {(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      {uploadFile.status === 'uploading' && (
                        <div className="flex-1">
                          <Progress value={uploadFile.progress} className="h-2" />
                        </div>
                      )}
                      {uploadFile.status === 'uploading' && (
                        <span className="text-sm text-slate-500">{uploadFile.progress.toFixed(0)}%</span>
                      )}
                    </div>
                    {uploadFile.status === 'error' && uploadFile.error && (
                      <Alert className="mt-2" variant="destructive">
                        <AlertDescription>{uploadFile.error}</AlertDescription>
                      </Alert>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Summary */}
            {files.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Pending: {pendingCount}</span>
                  <span className="text-green-600">Success: {successCount}</span>
                  <span className="text-red-600">Errors: {errorCount}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
