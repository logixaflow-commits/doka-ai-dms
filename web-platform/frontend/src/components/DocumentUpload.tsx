import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload, FileText, X, CheckCircle, AlertCircle, CloudUpload } from 'lucide-react';

const API_BASE = '/api';

interface FileWithProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

interface DocumentUploadProps {
  onUploadComplete?: () => void;
}

export default function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const [files, setFiles] = useState<FileWithProgress[]>([]);
  const [uploading, setUploading] = useState(false);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      processFiles(selectedFiles);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const processFiles = (selectedFiles: File[]) => {
    const validFiles: FileWithProgress[] = [];
    const errors: string[] = [];

    selectedFiles.forEach((file) => {
      const validationErrors = validateFile(file);
      if (validationErrors.length > 0) {
        errors.push(`${file.name}: ${validationErrors.join(', ')}`);
      } else {
        validFiles.push({
          file,
          progress: 0,
          status: 'pending',
        });
      }
    });

    if (errors.length > 0) {
      setError(errors.join('; '));
    }

    if (validFiles.length > 0) {
      setFiles((prev) => [...prev, ...validFiles]);
      setError('');
      setSuccess(false);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const validateFile = (file: File): string[] => {
    const errors: string[] = [];
    const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
    const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.doc', '.docx', '.xls', '.xlsx', '.txt'];
    const ALLOWED_MIME_TYPES = [
      'application/pdf',
      'image/png',
      'image/jpeg',
      'image/tiff',
      'image/bmp',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/plain'
    ];

    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);

    // Check if file is empty
    if (file.size === 0) {
      errors.push('File is empty');
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      errors.push(`File size (${fileSizeMB}MB) exceeds limit of 100MB`);
    }

    // Check file extension
    if (!ALLOWED_EXTENSIONS.includes(fileExt)) {
      errors.push(`File type (${fileExt}) is not allowed`);
    }

    // Check MIME type
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      errors.push(`Invalid file type (${file.type})`);
    }

    // Check for reserved filename characters and ASCII control characters.
    const hasControlCharacter = Array.from(file.name).some((character) => {
      const code = character.charCodeAt(0);
      return code < 32 || code === 127;
    });
    if (/[<>:"/\\|?*]/.test(file.name) || hasControlCharacter) {
      errors.push('Filename contains invalid characters');
    }

    return errors;
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setOverallProgress(0);
    setError('');

    const token = localStorage.getItem('access_token');
    const pendingFiles = files.filter(f => f.status === 'pending');
    let completedCount = 0;

    const uploadFile = (fileWithProgress: FileWithProgress): Promise<void> => {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', fileWithProgress.file);

        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            setFiles((prev) =>
              prev.map((f) =>
                f.file === fileWithProgress.file
                  ? { ...f, progress: percentComplete, status: 'uploading' }
                  : f
              )
            );
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200) {
            setFiles((prev) =>
              prev.map((f) =>
                f.file === fileWithProgress.file
                  ? { ...f, progress: 100, status: 'success' }
                  : f
              )
            );
            completedCount++;
            setOverallProgress((completedCount / pendingFiles.length) * 100);
            resolve();
          } else {
            const errorData = JSON.parse(xhr.responseText);
            setFiles((prev) =>
              prev.map((f) =>
                f.file === fileWithProgress.file
                  ? { ...f, status: 'error', error: errorData.detail || 'Upload failed' }
                  : f
              )
            );
            completedCount++;
            setOverallProgress((completedCount / pendingFiles.length) * 100);
            reject(errorData.detail || 'Upload failed');
          }
        };

        xhr.onerror = () => {
          setFiles((prev) =>
            prev.map((f) =>
              f.file === fileWithProgress.file
                ? { ...f, status: 'error', error: 'Connection error' }
                : f
            )
          );
          completedCount++;
          setOverallProgress((completedCount / pendingFiles.length) * 100);
          reject('Connection error');
        };

        xhr.open('POST', `${API_BASE}/documents/upload`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.send(formData);
      });
    };

    try {
      await Promise.allSettled(pendingFiles.map(uploadFile));
      setSuccess(true);
      if (onUploadComplete) onUploadComplete();
    } catch {
      setError('Some files failed to upload');
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setOverallProgress(0);
    setError('');
    setSuccess(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (fileToRemove: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== fileToRemove));
  };

  return (
    <Card className="hover-lift">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <CloudUpload className="w-5 h-5" />
          Upload Document
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drag and Drop Zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            dragActive
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-slate-300 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-500'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.doc,.docx,.xls,.xlsx,.txt"
            multiple
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <div className="flex flex-col items-center gap-3">
              <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
                dragActive ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-slate-100 dark:bg-slate-800'
              }`}>
                <Upload className={`w-8 h-8 ${dragActive ? 'text-blue-500' : 'text-slate-400'}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {dragActive ? 'Drop files here' : 'Drag & drop files here or click to browse'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Accepted formats: PDF, PNG, JPG, TIFF, BMP, DOC, DOCX, XLS, XLSX, TXT (Max 100MB each)
                </p>
              </div>
            </div>
          </label>
        </div>

        {files.length > 0 && !success && (
          <div className="space-y-3 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg fade-in">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {files.length} file{files.length > 1 ? 's' : ''} selected
              </p>
              <Button
                onClick={handleReset}
                disabled={uploading}
                variant="ghost"
                size="sm"
              >
                Clear all
              </Button>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {files.map((fileWithProgress, index) => (
                <div key={index} className="flex items-center gap-3 p-2 bg-white dark:bg-slate-700 rounded-lg">
                  <FileText className="w-5 h-5 text-slate-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
                      {fileWithProgress.file.name}
                    </p>
                    <p className="text-xs text-slate-500">
                      {(fileWithProgress.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                    {fileWithProgress.status === 'uploading' && (
                      <Progress value={fileWithProgress.progress} className="h-1 mt-1" />
                    )}
                    {fileWithProgress.status === 'error' && (
                      <p className="text-xs text-red-500 mt-1">{fileWithProgress.error}</p>
                    )}
                  </div>
                  {fileWithProgress.status === 'success' && (
                    <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                  )}
                  {fileWithProgress.status === 'error' && (
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  )}
                  {!uploading && fileWithProgress.status === 'pending' && (
                    <Button
                      onClick={() => removeFile(fileWithProgress.file)}
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {uploading && (
              <div className="space-y-2">
                <Progress value={overallProgress} className="w-full" />
                <p className="text-xs text-slate-500 text-center">
                  Overall progress: {Math.round(overallProgress)}%
                </p>
              </div>
            )}

            <Button
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
              className="w-full"
            >
              {uploading ? 'Uploading...' : `Upload ${files.length} file${files.length > 1 ? 's' : ''}`}
            </Button>
          </div>
        )}

        {error && (
          <Alert variant="destructive" className="fade-in">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert className="bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800 fade-in">
            <CheckCircle className="h-4 w-4 text-emerald-600" />
            <AlertDescription className="text-emerald-800 dark:text-emerald-300">
              Document uploaded successfully! AI processing has started.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}