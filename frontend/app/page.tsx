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
  const [jobDescription, setJobDescription] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobAnalysis, setJobAnalysis] = useState<AnalyzedJobDescription | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isScreening, setIsScreening] = useState(false);
  const [screeningResults, setScreeningResults] = useState<MatchingResponse | null>(null);

  const handleJobAnalyzed = (id: string, analysis: AnalyzedJobDescription) => {
    setJobId(id);
    setJobAnalysis(analysis);
  };

  const handleFilesUploaded = (files: UploadedFile[]) => {
    setUploadedFiles(files);
  };

  const handleAnalyze = async () => {
    if (!jobId || uploadedFiles.length === 0) {
      return;
    }

    setIsScreening(true);
    setScreeningResults(null);

    try {
      // Upload all resumes
      const formData = new FormData();
      uploadedFiles.forEach((uploadedFile) => {
        formData.append('files', uploadedFile.file);
      });

      const uploadResponse = await apiClient.uploadResumes(formData);

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
      alert(errorMessage);
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
        {screeningResults && jobId && (
          <ScreeningResults results={screeningResults} jobId={jobId} />
        )}
      </main>
    </div>
  );
}
