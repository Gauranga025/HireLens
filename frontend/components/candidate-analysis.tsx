"use client";

import { Award, AlertTriangle, Plus, FileText, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { useState } from 'react';
import type { CandidateMatchResult } from '@/lib/types';

interface CandidateAnalysisProps {
  candidate: CandidateMatchResult;
}

export function CandidateAnalysis({ candidate }: CandidateAnalysisProps) {
  const { match_result } = candidate;
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());
  const groupEvaluation = match_result.group_evaluation ?? [];
  const strengths = match_result.strengths ?? [];
  const gaps = match_result.gaps ?? [];

  const toggleSkill = (skill: string) => {
    const newExpanded = new Set(expandedSkills);
    if (newExpanded.has(skill)) {
      newExpanded.delete(skill);
    } else {
      newExpanded.add(skill);
    }
    setExpandedSkills(newExpanded);
  };

  const getEvidenceColor = (strength: string) => {
    switch (strength) {
      case 'strong': return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      case 'moderate': return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20';
      case 'basic': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20';
      case 'weak': return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
      default: return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  const getSectionLabel = (section: string) => {
    const labels: Record<string, string> = {
      'experience': 'Work Experience',
      'projects': 'Projects',
      'skills': 'Skills Section',
      'education': 'Education',
      'certifications': 'Certifications',
      'uncategorized': 'Other',
    };
    return labels[section] || section;
  };

  return (
    <div className="space-y-6">
      {/* Scoring Strategy */}
      {match_result.scoring_strategy && (
        <div className="p-4 bg-muted/30 border border-border rounded-md">
          <h3 className="font-medium mb-2 flex items-center gap-2 text-sm">
            <Info className="h-4 w-4" />
            Scoring Strategy
          </h3>
          <div className="text-xs space-y-1">
            <p><strong>Algorithm:</strong> {match_result.scoring_strategy.algorithm_version}</p>
            <p><strong>Components:</strong> {match_result.scoring_strategy.components.join(', ') || 'None'}</p>
            {!match_result.scoring_strategy.semantic_available && (
              <p className="text-yellow-600 dark:text-yellow-400">
                <strong>Note:</strong> Semantic matching unavailable - using fallback scoring
              </p>
            )}
          </div>
        </div>
      )}

      {/* Score Breakdown */}
      <div>
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <Award className="h-4 w-4" />
          Score Breakdown
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-muted/50 border border-border rounded-md">
            <p className="text-xs text-muted-foreground mb-1">Required Skills</p>
            <p className="text-lg font-semibold">{match_result.required_skill_coverage.toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-muted/50 border border-border rounded-md">
            <p className="text-xs text-muted-foreground mb-1">Preferred Skills</p>
            <p className="text-lg font-semibold">{match_result.preferred_skill_coverage.toFixed(1)}%</p>
          </div>
          {match_result.semantic_score !== null && (
            <div className="p-3 bg-muted/50 border border-border rounded-md">
              <p className="text-xs text-muted-foreground mb-1">Semantic</p>
              <p className="text-lg font-semibold">{match_result.semantic_score.toFixed(1)}%</p>
            </div>
          )}
          <div className="p-3 bg-muted/50 border border-border rounded-md">
            <p className="text-xs text-muted-foreground mb-1">Evidence</p>
            <p className="text-lg font-semibold">
              {match_result.evidence_score != null
                ? `${match_result.evidence_score.toFixed(1)}%`
                : Object.keys(match_result.skill_evidence).length > 0
                  ? 'Available'
                  : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Alternative requirement groups */}
      {groupEvaluation.length > 0 && (
        <div>
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <Award className="h-4 w-4" />
            Alternative Requirements
          </h3>
          <div className="space-y-2">
            {groupEvaluation.map((group, index) => (
              <div
                key={`${group.group_name}-${index}`}
                className="p-3 border border-border rounded-md"
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="text-sm font-medium">{group.group_name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      group.is_satisfied
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    }`}
                  >
                    {group.is_satisfied ? 'Satisfied' : 'Not satisfied'}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {group.match_mode === 'ANY' ? 'Requires at least one of' : 'Requires all of'}:{' '}
                  {group.required_skills.join(', ')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Matched: {group.matched_skills.length > 0 ? group.matched_skills.join(', ') : 'None'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Matched Skills with Evidence */}
      <div>
        <h3 className="font-medium mb-3 flex items-center gap-2 text-green-600">
          <Award className="h-4 w-4" />
          Matched Skills ({match_result.matched_skills.length})
        </h3>
        <div className="space-y-2">
          {match_result.matched_skills.length > 0 ? (
            match_result.matched_skills.map((skill) => {
              const evidence = match_result.skill_evidence[skill] || [];
              const hasEvidence = evidence.length > 0;
              
              return (
                <div key={skill} className="border border-border rounded-md">
                  <button
                    onClick={() => toggleSkill(skill)}
                    className="w-full px-3 py-2 flex items-center justify-between hover:bg-muted/50 transition-colors"
                  >
                    <span className="font-medium">{skill}</span>
                    <div className="flex items-center gap-2">
                      {hasEvidence && (
                        <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full">
                          Evidence
                        </span>
                      )}
                      {expandedSkills.has(skill) ? (
                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </button>
                  
                  {expandedSkills.has(skill) && hasEvidence && (
                    <div className="px-3 py-2 border-t border-border space-y-2">
                      {evidence.map((ev, i) => (
                        <div key={i} className="p-2 bg-muted/30 rounded-md">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium text-muted-foreground">
                              {getSectionLabel(ev.section)}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${getEvidenceColor(ev.strength)}`}>
                              {ev.strength}
                            </span>
                            {ev.demonstration_level && (
                              <span className="text-xs text-muted-foreground">
                                {ev.demonstration_level}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground italic">
                            &quot;{ev.snippet}&quot;
                          </p>
                          {ev.experience_type && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Context: {ev.experience_type.replace(/_/g, ' ')}
                            </p>
                          )}
                          {!ev.experience_type &&
                            ev.project_info &&
                            typeof ev.project_info.title === 'string' && (
                              <p className="text-xs text-muted-foreground mt-1">
                                Project: {ev.project_info.title}
                              </p>
                            )}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {expandedSkills.has(skill) && !hasEvidence && (
                    <div className="px-3 py-2 border-t border-border">
                      <p className="text-sm text-muted-foreground">
                        No supporting evidence found in resume sections.
                      </p>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <p className="text-sm text-muted-foreground">None matched</p>
          )}
        </div>
      </div>

      {/* Strengths and gaps */}
      {(strengths.length > 0 || gaps.length > 0) && (
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="font-medium mb-3 flex items-center gap-2 text-green-600">
              <Award className="h-4 w-4" />
              Strengths ({strengths.length})
            </h3>
            <ul className="space-y-2">
              {strengths.length > 0 ? (
                strengths.map((strength, index) => (
                  <li
                    key={index}
                    className="p-2 text-sm bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900/40 rounded-md"
                  >
                    {strength}
                  </li>
                ))
              ) : (
                <li className="text-sm text-muted-foreground">No demonstrated strengths identified.</li>
              )}
            </ul>
          </div>
          <div>
            <h3 className="font-medium mb-3 flex items-center gap-2 text-yellow-600">
              <AlertTriangle className="h-4 w-4" />
              Gaps ({gaps.length})
            </h3>
            <ul className="space-y-2">
              {gaps.length > 0 ? (
                gaps.map((gap, index) => (
                  <li
                    key={index}
                    className="p-2 text-sm bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900/40 rounded-md"
                  >
                    {gap}
                  </li>
                ))
              ) : (
                <li className="text-sm text-muted-foreground">No evidence gaps identified.</li>
              )}
            </ul>
          </div>
        </div>
      )}

      {/* Missing Skills */}
      <div>
        <h3 className="font-medium mb-3 flex items-center gap-2 text-yellow-600">
          <AlertTriangle className="h-4 w-4" />
          Missing Skills ({match_result.missing_skills.length})
        </h3>
        <div className="flex flex-wrap gap-2">
          {match_result.missing_skills.length > 0 ? (
            match_result.missing_skills.map((skill, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 text-xs rounded-md"
              >
                {skill}
              </span>
            ))
          ) : (
            <span className="text-sm text-muted-foreground">All required skills present</span>
          )}
        </div>
      </div>

      {/* Additional Skills */}
      <div>
        <h3 className="font-medium mb-3 flex items-center gap-2 text-blue-600">
          <Plus className="h-4 w-4" />
          Additional Skills ({match_result.additional_skills.length})
        </h3>
        <div className="flex flex-wrap gap-2">
          {match_result.additional_skills.length > 0 ? (
            match_result.additional_skills.slice(0, 10).map((skill, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 text-xs rounded-md"
              >
                {skill}
              </span>
            ))
          ) : (
            <span className="text-sm text-muted-foreground">None</span>
          )}
          {match_result.additional_skills.length > 10 && (
            <span className="text-xs text-muted-foreground">
              +{match_result.additional_skills.length - 10} more
            </span>
          )}
        </div>
      </div>

      {/* Explanation */}
      <div>
        <h3 className="font-medium mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Why This Score
        </h3>
        <div className="p-4 bg-muted/50 border border-border rounded-md">
          <p className="text-sm leading-relaxed">{match_result.explanation}</p>
        </div>
      </div>

      {/* Recruiter Interpretation */}
      <div className="p-4 bg-primary/5 border border-primary/20 rounded-md">
        <h3 className="font-medium mb-2 text-primary">Recruiter Interpretation</h3>
        <div className="text-sm space-y-2">
          {match_result.overall_score >= 80 && (
            <p className="text-green-700 dark:text-green-400">
              <strong>Strong Match:</strong> This candidate demonstrates excellent alignment with the job requirements.
              Consider advancing to interview stage.
            </p>
          )}
          {match_result.overall_score >= 60 && match_result.overall_score < 80 && (
            <p className="text-yellow-700 dark:text-yellow-400">
              <strong>Moderate Match:</strong> This candidate meets several core requirements but may have skill gaps.
              Review missing skills and consider if they can be learned on the job.
            </p>
          )}
          {match_result.overall_score < 60 && (
            <p className="text-red-700 dark:text-red-400">
              <strong>Limited Match:</strong> This candidate has significant gaps relative to core requirements.
              Consider if other strengths compensate for missing skills.
            </p>
          )}
          <p className="text-muted-foreground text-xs mt-2">
            Note: Match scores are decision-support indicators, not guaranteed measures of candidate quality.
            Consider the full context including experience, cultural fit, and potential.
          </p>
        </div>
      </div>
    </div>
  );
}
