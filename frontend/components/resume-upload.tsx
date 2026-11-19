"use client";

import { useState, useCallback } from 'react';
import { Upload, X, FileText, AlertCircle } from 'lucide-react';
import type { UploadedFile } from '@/lib/types';

interface ResumeUploadProps {
  files: UploadedFile[];
  onFilesUploaded: (files: UploadedFile[]) => void;
  disabled?: boolean;
}

const MAX_FILES = 10;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

export function ResumeUpload({ files, onFilesUploaded, disabled }: ResumeUploadProps) {
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Only PDF and DOCX files are allowed';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size exceeds 10MB limit';
    }
    return null;
  };

  const handleFileSelect = useCallback((selectedFiles: FileList | null) => {
    if (!selectedFiles || disabled) return;

    const newFiles: UploadedFile[] = [];
    const errors: string[] = [];

    Array.from(selectedFiles).forEach((file) => {
      if (files.length + newFiles.length >= MAX_FILES) {
        errors.push(`Maximum ${MAX_FILES} files allowed`);
        return;
      }

      const error = validateFile(file);
      if (error) {
        errors.push(`${file.name}: ${error}`);
        return;
      }

      // Check for duplicates
      if (files.some((f) => f.file.name === file.name && f.file.size === file.size)) {
        errors.push(`${file.name}: Already uploaded`);
        return;
      }

      newFiles.push({
        file,
        status: 'pending',
      });
    });

    if (errors.length > 0) {
      alert(errors.join('\n'));
    }

    if (newFiles.length > 0) {
      const updatedFiles = [...files, ...newFiles];
      onFilesUploaded(updatedFiles);
    }
  }, [files, disabled, onFilesUploaded]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleRemoveFile = (index: number) => {
    const updatedFiles = files.filter((_, i) => i !== index);
    onFilesUploaded(updatedFiles);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <section className="border-b bg-card">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl">
          <h2 className="text-lg font-semibold mb-1">Upload Resumes</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Upload up to 10 resume files (PDF or DOCX, max 10MB each)
          </p>

          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            onClick={() => !disabled && document.getElementById('file-input')?.click()}
          >
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pdf,.docx"
              onChange={(e) => handleFileSelect(e.target.files)}
              disabled={disabled}
              className="hidden"
            />
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-sm font-medium mb-1">
              {isDragging ? 'Drop files here' : 'Drag and drop resumes here'}
            </p>
            <p className="text-xs text-muted-foreground mb-2">or click to browse</p>
            <p className="text-xs text-muted-foreground">
              PDF and DOCX only • Max 10MB per file • Max {MAX_FILES} files
            </p>
          </div>

          {files.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">
                  {files.length} / {MAX_FILES} resumes uploaded
                </span>
              </div>
              <div className="space-y-2">
                {files.map((uploadedFile, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-muted/50 border border-border rounded-md"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{uploadedFile.file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(uploadedFile.file.size)}
                        </p>
                      </div>
                    </div>
                    {uploadedFile.status === 'error' && (
                      <div className="flex items-center gap-2 text-destructive">
                        <AlertCircle className="h-4 w-4" />
                        <span className="text-xs">{uploadedFile.error}</span>
                      </div>
                    )}
                    {uploadedFile.status === 'success' && (
                      <span className="ml-2 text-xs text-green-600">Uploaded</span>
                    )}
                    <button
                      onClick={() => handleRemoveFile(index)}
                      disabled={disabled}
                      className="ml-2 p-1 hover:bg-destructive/10 rounded transition-colors disabled:opacity-50"
                    >
                      <X className="h-4 w-4 text-muted-foreground" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
