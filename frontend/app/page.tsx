"use client";

import { useState } from 'react';
import { Header } from '@/components/header';
import { JobDescriptionForm } from '@/components/job-description-form';
import { ResumeUpload } from '@/components/resume-upload';
import { UploadReview } from '@/components/upload-review';
import { ScreeningProgress } from '@/components/screening-progress';
import { ScreeningResults } from '@/components/screening-results';
import { apiClient } from '@/lib/api-client';
import type { UploadedFile, AnalyzedJobDescription, MatchingResponse } from '@/lib/types';

export default function Home() {
  const [jobTitle, setJobTitle] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobAnalysis, setJobAnalysis] = useState<AnalyzedJobDescription | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isScreening, setIsScreening] = useState(false);
  const [screeningResults, setScreeningResults] = useState<MatchingResponse | null>(null);
  const [screeningError, setScreeningError] = useState<string | null>(null);

  const handleJobAnalyzed = (id: string, analysis: AnalyzedJobDescription) => {
    setJobId(id);
    setJobAnalysis(analysis);
    setScreeningResults(null);
    setScreeningError(null);
  };

  const handleFilesUploaded = (files: UploadedFile[]) => {
    setUploadedFiles(files);
    setScreeningResults(null);
    setScreeningError(null);
  };

  const handleAnalyze = async () => {
    if (!jobId || uploadedFiles.length === 0) {
      return;
    }

    setIsScreening(true);
    setScreeningResults(null);
    setScreeningError(null);

    try {
      // Upload all resumes
      const formData = new FormData();
      uploadedFiles.forEach((uploadedFile) => {
        formData.append('files', uploadedFile.file);
      });

      const uploadResponse = await apiClient.uploadResumes(formData);

      // Keep per-file status so failed uploads remain visible instead of being
      // silently dropped from the UI.
      const updatedFiles = uploadedFiles.map((uploadedFile, index) => {
        const result = uploadResponse.results[index];
        if (!result) {
          return {
            ...uploadedFile,
            status: 'error' as const,
            error: 'No upload result returned by the server',
          };
        }
        if (result.status === 'success') {
          return {
            ...uploadedFile,
            status: 'success' as const,
            resumeId: result.resume_id,
            error: undefined,
          };
        }
        return {
          ...uploadedFile,
          status: 'error' as const,
          error: result.error || result.message || 'Upload failed',
        };
      });
      setUploadedFiles(updatedFiles);

      // Extract resume IDs from successful uploads
      const successfulUploads = uploadResponse.results.filter((r) => r.status === 'success');
      const resumeIds = successfulUploads.map((r) => r.resume_id);

      if (resumeIds.length === 0) {
        throw new Error('No resumes were successfully uploaded');
      }

      // Run matching
      const matchingResponse = await apiClient.evaluateMatching({
        job_id: jobId,
        resume_ids: resumeIds,
        use_semantic: true,
      });

      setScreeningResults(matchingResponse);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Screening failed';
      setScreeningError(errorMessage);
    } finally {
      setIsScreening(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main>
        <JobDescriptionForm
          onJobAnalyzed={handleJobAnalyzed}
          disabled={isScreening}
          jobTitle={jobTitle}
          setJobTitle={setJobTitle}
        />
        <ResumeUpload
          files={uploadedFiles}
          onFilesUploaded={handleFilesUploaded}
          disabled={isScreening}
        />
        <UploadReview
          jobTitle={jobTitle}
          hasJobDescription={!!jobAnalysis}
          files={uploadedFiles}
          onAnalyze={handleAnalyze}
          disabled={isScreening}
        />
        {isScreening && <ScreeningProgress isScreening={isScreening} />}
        {screeningError && (
          <section className="border-b bg-card">
            <div className="container mx-auto px-4 py-4">
              <div className="max-w-3xl p-3 text-sm text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/40 rounded-md">
                {screeningError}
              </div>
            </div>
          </section>
        )}
        {screeningResults && jobId && (
          <ScreeningResults results={screeningResults} jobId={jobId} />
        )}
      </main>
    </div>
  );
}
