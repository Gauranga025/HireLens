// TypeScript interfaces based on backend FastAPI schemas

export interface HealthResponse {
  status: string;
  version: string;
  app_name: string;
}

export interface EducationEntry {
  degree: string;
  institution: string;
  year: string;
}

export interface ExperienceEntry {
  title: string;
  company: string;
  duration: string;
}

export interface ExtractedResumeInfo {
  name: string;
  email: string;
  phone: string;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  certifications: string[];
  projects: string[];
  skills: string[];
}

export interface DocumentExtractionResult {
  text: string;
  source_format: string;
  num_pages?: number;
  num_paragraphs?: number;
  is_scanned: boolean;
  metadata: Record<string, unknown>;
}

export interface ResumeUploadResponse {
  resume_id: string;
  filename: string;
  status: string;
  message: string;
  extraction?: DocumentExtractionResult;
  candidate_info?: ExtractedResumeInfo;
  error?: string;
}

export interface BatchResumeUploadResponse {
  total_files: number;
  successful: number;
  failed: number;
  results: ResumeUploadResponse[];
}

export interface AnalyzedJobDescription {
  title: string;
  required_skills: string[];
  preferred_skills: string[];
  qualifications: string[];
  experience_required: string;
  structured_requirements?: StructuredRequirement[];
  raw_text: string;
}

export interface StructuredSkill {
  skill: string;
  normalized_skill?: string | null;
  original_text: string;
}

export interface StructuredRequirementData {
  skill?: string;
  normalized_skill?: string;
  group_name?: string;
  match_mode?: 'ANY' | 'ALL';
  skills?: StructuredSkill[];
  min_years?: number | null;
  max_years?: number | null;
  experience_type?: 'professional' | 'internship' | 'any';
  original_text?: string;
}

export interface StructuredRequirement {
  requirement_type:
    | 'REQUIRED'
    | 'REQUIRED_GROUP'
    | 'PREFERRED'
    | 'OPTIONAL'
    | 'EXPERIENCE'
    | 'FUNDAMENTAL';
  data: StructuredRequirementData;
  original_text: string;
}

export interface JobAnalysisRequest {
  job_description: string;
}

export interface JobAnalysisResponse {
  job_id: string;
  analysis: AnalyzedJobDescription;
}

export interface JobRetrieveResponse {
  job_id: string;
  analysis: AnalyzedJobDescription;
}

export interface SkillEvidence {
  skill: string;
  section: string;
  evidence_type: string;
  snippet: string;
  strength: string;
  start_offset?: number;
  end_offset?: number;
  demonstration_level?: string | null;
  date_info?: Record<string, unknown> | null;
  experience_type?: string | null;
  project_info?: Record<string, unknown> | null;
  temporal_info?: Record<string, unknown> | null;
}

export interface RequirementMatch {
  requirement: string;
  matched: boolean;
  similarity_score?: number;
  evidence: SkillEvidence[];
  is_alternative: boolean;
}

export interface ScoringStrategy {
  algorithm_version: string;
  components: string[];
  weights: Record<string, number>;
  semantic_available: boolean;
  fallback_used: boolean;
  skill_hierarchy_enabled?: boolean;
  demonstration_levels_enabled?: boolean;
  keyword_stuffing_penalty_enabled?: boolean;
  keyword_stuffing_education_aware?: boolean;
  related_skill_credit_threshold?: number;
  evaluation_date?: string | null;
}

export interface RequirementEvaluation {
  skill: string;
  requirement_type: string;
  matched: boolean;
  match_type: string | null;
  evidence_level: string | null;
  source_section: string | null;
  evidence: string | null;
  source_reference: string | null;
  experience_type: string | null;
  project_info: Record<string, unknown> | null;
  satisfied_by_group?: boolean;
}

export interface GroupEvaluation {
  requirement_type: string;
  match_mode: string;
  group_name: string;
  required_skills: string[];
  matched_skills: string[];
  is_satisfied: boolean;
  original_text: string;
}

export interface EvidenceSummary {
  demonstrated_skills: string[];
  mentioned_skills: string[];
  unsupported_required_skills: string[];
  unsupported_preferred_skills: string[];
}

export interface KeywordStuffingAnalysis {
  is_stuffed: boolean;
  stuffing_ratio: number;
  total_skills: number;
  skills_without_evidence: number;
}

export interface MatchResult {
  overall_score: number;
  tfidf_score: number;
  semantic_score: number | null;
  skill_match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  additional_skills: string[];
  explanation: string;
  skill_evidence: Record<string, SkillEvidence[]>;
  requirement_matches: RequirementMatch[];
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  scoring_strategy?: ScoringStrategy;
  evidence_score?: number | null;
  evidence_summary?: EvidenceSummary;
  requirement_evaluations?: Record<string, RequirementEvaluation>;
  strengths?: string[];
  gaps?: string[];
  temporal_metadata?: Record<string, unknown> | null;
  keyword_stuffing_penalty?: number;
  keyword_stuffing_analysis?: KeywordStuffingAnalysis | null;
  group_evaluation?: GroupEvaluation[];
}

export interface CandidateMatchResult {
  resume_id: string;
  filename: string;
  candidate_name: string;
  match_result: MatchResult;
  error?: string;
}

export interface MatchingRequest {
  job_id: string;
  resume_ids: string[];
  use_semantic?: boolean;
}

export interface MatchingResponse {
  job_id: string;
  total_candidates: number;
  successful: number;
  failed: number;
  results: CandidateMatchResult[];
}

export interface ReportResponse {
  report_id: string;
  format: string;
  content: string;
}

// Frontend-specific types
export interface UploadedFile {
  file: File;
  resumeId?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'checking';

export interface ScreeningState {
  jobTitle: string;
  jobDescription: string;
  jobId: string | null;
  uploadedFiles: UploadedFile[];
  isScreening: boolean;
  screeningResults: MatchingResponse | null;
}
