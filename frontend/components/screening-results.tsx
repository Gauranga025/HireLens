"use client";

import { Fragment, useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, Download } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { MatchingResponse, CandidateMatchResult } from '@/lib/types';
import { CandidateAnalysis } from './candidate-analysis';

interface ScreeningResultsProps {
  results: MatchingResponse;
  jobId: string;
}

export function ScreeningResults({ results, jobId }: ScreeningResultsProps) {
  const [expandedCandidate, setExpandedCandidate] = useState<string | null>(null);
  const [exportingCandidate, setExportingCandidate] = useState<string | null>(null);

  const handleExport = async (candidate: CandidateMatchResult, format: 'json' | 'csv' = 'json') => {
    setExportingCandidate(candidate.resume_id);
    try {
      const report = await apiClient.generateReport(jobId, candidate.resume_id, format);
      
      // Download the report
      const blob = new Blob([report.content], { type: format === 'json' ? 'application/json' : 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${candidate.filename.replace(/\.[^/.]+$/, '')}_report.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export report');
    } finally {
      setExportingCandidate(null);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBackground = (score: number): string => {
    if (score >= 80) return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400';
    if (score >= 60) return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400';
    return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400';
  };

  return (
    <section className="border-b bg-card">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-5xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Screening Results</h2>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>Total: {results.total_candidates}</span>
              <span className="text-green-600">Successful: {results.successful}</span>
              {results.failed > 0 && <span className="text-red-600">Failed: {results.failed}</span>}
            </div>
          </div>

          <div className="border border-border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">Rank</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Candidate</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Match Score</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Skills Matched</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {results.results.map((candidate, index) => {
                  const failed = Boolean(candidate.error);
                  const isExpanded = !failed && expandedCandidate === candidate.resume_id;

                  return (
                    <Fragment key={candidate.resume_id}>
                      <tr
                        className={`border-t border-border ${
                          failed ? 'bg-red-50/50 dark:bg-red-900/10' : 'hover:bg-muted/30 cursor-pointer'
                        }`}
                        onClick={() =>
                          !failed &&
                          setExpandedCandidate(
                            expandedCandidate === candidate.resume_id ? null : candidate.resume_id
                          )
                        }
                      >
                        <td className="px-4 py-3 text-sm font-medium">#{index + 1}</td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium">{candidate.candidate_name}</p>
                            <p className="text-xs text-muted-foreground">{candidate.filename}</p>
                            {failed && (
                              <p className="text-xs text-red-600 flex items-center gap-1 mt-1">
                                <AlertCircle className="h-3 w-3" />
                                {candidate.error}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {failed ? (
                            <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400">
                              Not evaluated
                            </span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className={`text-lg font-semibold ${getScoreColor(candidate.match_result.overall_score)}`}>
                                {candidate.match_result.overall_score.toFixed(1)}%
                              </span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreBackground(candidate.match_result.overall_score)}`}>
                                {candidate.match_result.overall_score >= 80 ? 'High' : candidate.match_result.overall_score >= 60 ? 'Medium' : 'Low'}
                              </span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="text-muted-foreground">
                            {failed
                              ? '—'
                              : `${candidate.match_result.matched_skills.length} / ${
                                  candidate.match_result.matched_skills.length +
                                  candidate.match_result.missing_skills.length
                                }`}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {failed ? (
                            <span className="text-xs text-muted-foreground">Unavailable</span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedCandidate(
                                    expandedCandidate === candidate.resume_id ? null : candidate.resume_id
                                  );
                                }}
                                className="p-1 hover:bg-muted rounded transition-colors"
                                aria-label={isExpanded ? 'Collapse candidate details' : 'Expand candidate details'}
                              >
                                {isExpanded ? (
                                  <ChevronUp className="h-4 w-4" />
                                ) : (
                                  <ChevronDown className="h-4 w-4" />
                                )}
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleExport(candidate, 'csv');
                                }}
                                disabled={exportingCandidate === candidate.resume_id}
                                className="p-1 hover:bg-muted rounded transition-colors disabled:opacity-50"
                                title="Export CSV"
                              >
                                <Download className="h-4 w-4" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={5} className="px-4 py-4 bg-muted/20">
                            <CandidateAnalysis candidate={candidate} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {results.results.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No results to display
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
