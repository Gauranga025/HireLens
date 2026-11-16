"use client";

import { useState } from 'react';
import { Briefcase, Sparkles } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { AnalyzedJobDescription } from '@/lib/types';

interface JobDescriptionFormProps {
  onJobAnalyzed: (jobId: string, analysis: AnalyzedJobDescription) => void;
  disabled?: boolean;
  jobTitle: string;
  setJobTitle: (title: string) => void;
}

export function JobDescriptionForm({ onJobAnalyzed, disabled, jobTitle, setJobTitle }: JobDescriptionFormProps) {
  const [description, setDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalyzedJobDescription | null>(null);
  const [error, setError] = useState('');

  const handleAnalyze = async () => {
    if (!jobTitle.trim() || !description.trim()) {
      setError('Please provide both job title and description');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    setAnalysis(null);

    try {
      const response = await apiClient.analyzeJob({ job_description: description });
      setAnalysis(response.analysis);
      onJobAnalyzed(response.job_id, response.analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze job description');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <section className="border-b bg-card">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl">
          <h2 className="text-lg font-semibold mb-1">Job Description</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Enter the job title and description to begin screening candidates
          </p>

          <div className="space-y-4">
            <div>
              <label htmlFor="job-title" className="block text-sm font-medium mb-2">
                Job Title <span className="text-destructive">*</span>
              </label>
              <input
                id="job-title"
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                disabled={disabled || isAnalyzing}
                placeholder="e.g., Senior Python Developer"
                className="w-full px-3 py-2 border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
            </div>

            <div>
              <label htmlFor="job-description" className="block text-sm font-medium mb-2">
                Job Description <span className="text-destructive">*</span>
              </label>
              <textarea
                id="job-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={disabled || isAnalyzing}
                placeholder="Paste the full job description here..."
                rows={8}
                className="w-full px-3 py-2 border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 resize-none"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Include required skills, qualifications, and experience requirements
              </p>
            </div>

            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={disabled || isAnalyzing || !jobTitle.trim() || !description.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isAnalyzing ? (
                <>
                  <Sparkles className="h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Analyze Job Description
                </>
              )}
            </button>

            {analysis && (
              <div className="mt-6 p-4 bg-muted/50 border border-border rounded-md">
                <h3 className="font-medium mb-3 flex items-center gap-2">
                  <Briefcase className="h-4 w-4" />
                  Extracted Requirements
                </h3>
                <div className="space-y-3 text-sm">
                  <div>
                    <span className="font-medium">Required Skills:</span>
                    <span className="ml-2 text-muted-foreground">
                      {analysis.required_skills.length > 0
                        ? analysis.required_skills.join(', ')
                        : 'None detected'}
                    </span>
                  </div>
                  {analysis.preferred_skills.length > 0 && (
                    <div>
                      <span className="font-medium">Preferred Skills:</span>
                      <span className="ml-2 text-muted-foreground">
                        {analysis.preferred_skills.join(', ')}
                      </span>
                    </div>
                  )}
                  {analysis.qualifications.length > 0 && (
                    <div>
                      <span className="font-medium">Qualifications:</span>
                      <span className="ml-2 text-muted-foreground">
                        {analysis.qualifications.join(', ')}
                      </span>
                    </div>
                  )}
                  {analysis.experience_required !== 'Not specified' && (
                    <div>
                      <span className="font-medium">Experience Required:</span>
                      <span className="ml-2 text-muted-foreground">
                        {analysis.experience_required}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
