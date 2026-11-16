"use client";

import { FileText, Check } from 'lucide-react';
import type { UploadedFile } from '@/lib/types';

interface UploadReviewProps {
  jobTitle: string;
  hasJobDescription: boolean;
  files: UploadedFile[];
  onAnalyze: () => void;
  disabled?: boolean;
}

export function UploadReview({ jobTitle, hasJobDescription, files, onAnalyze, disabled }: UploadReviewProps) {
  const canAnalyze = jobTitle.trim() !== '' && hasJobDescription && files.length > 0 && !disabled;

  return (
    <section className="border-b bg-card">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl">
          <h2 className="text-lg font-semibold mb-6">Review Before Screening</h2>

          <div className="space-y-4">
            <div className="p-4 bg-muted/50 border border-border rounded-md">
              <h3 className="font-medium mb-3">Job Information</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground w-24">Title:</span>
                  <span className={jobTitle ? 'font-medium' : 'text-muted-foreground'}>
                    {jobTitle || 'Not provided'}
                  </span>
                  {jobTitle && <Check className="h-4 w-4 text-green-500" />}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground w-24">Description:</span>
                  <span className={hasJobDescription ? 'font-medium' : 'text-muted-foreground'}>
                    {hasJobDescription ? 'Provided' : 'Not provided'}
                  </span>
                  {hasJobDescription && <Check className="h-4 w-4 text-green-500" />}
                </div>
              </div>
            </div>

            <div className="p-4 bg-muted/50 border border-border rounded-md">
              <h3 className="font-medium mb-3">Resumes to Screen ({files.length})</h3>
              {files.length === 0 ? (
                <p className="text-sm text-muted-foreground">No resumes uploaded</p>
              ) : (
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1 truncate">{file.file.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {(file.file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={onAnalyze}
              disabled={!canAnalyze}
              className="w-full py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              Analyze All Candidates
            </button>

            {!canAnalyze && (
              <p className="text-xs text-center text-muted-foreground">
                {files.length === 0
                  ? 'Upload resumes to begin'
                  : !jobTitle || !hasJobDescription
                  ? 'Provide job title and description to begin'
                  : 'Screening in progress'}
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
