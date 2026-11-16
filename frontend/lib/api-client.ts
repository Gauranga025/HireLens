// API client for HireLens backend
import type {
  HealthResponse,
  JobAnalysisRequest,
  JobAnalysisResponse,
  BatchResumeUploadResponse,
  MatchingRequest,
  MatchingResponse,
  ReportResponse,
} from './types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async analyzeJob(request: JobAnalysisRequest): Promise<JobAnalysisResponse> {
    return this.request<JobAnalysisResponse>('/api/v1/jobs/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async uploadResumes(formData: FormData): Promise<BatchResumeUploadResponse> {
    const url = `${this.baseUrl}/api/v1/resumes/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async evaluateMatching(request: MatchingRequest): Promise<MatchingResponse> {
    return this.request<MatchingResponse>('/api/v1/matching/evaluate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async generateReport(jobId: string, resumeId: string, format: 'json' | 'csv' = 'json'): Promise<ReportResponse> {
    return this.request<ReportResponse>(`/api/v1/reports/generate?job_id=${jobId}&resume_id=${resumeId}&format=${format}`, {
      method: 'POST',
    });
  }
}

export const apiClient = new ApiClient(BACKEND_URL);
