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
  raw_text: string;
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
