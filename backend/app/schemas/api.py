from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.resume import ExtractedResumeInfo, DocumentExtractionResult
from app.schemas.job import AnalyzedJobDescription
from app.schemas.matching import MatchResult


class ResumeUploadResponse(BaseModel):
    """Response for resume upload endpoint."""

    resume_id: str = Field(..., description="Unique identifier for the processed resume")
    filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Processing status (success/error)")
    message: str = Field(..., description="Status message")
    extraction: Optional[DocumentExtractionResult] = Field(default=None, description="Document extraction result")
    candidate_info: Optional[ExtractedResumeInfo] = Field(default=None, description="Extracted candidate information")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")


class BatchResumeUploadResponse(BaseModel):
    """Response for batch resume upload endpoint."""

    total_files: int = Field(..., description="Total number of files uploaded")
    successful: int = Field(..., description="Number of successfully processed files")
    failed: int = Field(..., description="Number of files that failed processing")
    results: List[ResumeUploadResponse] = Field(..., description="Individual file processing results")


class ResumeRetrieveResponse(BaseModel):
    """Response for resume retrieval endpoint."""

    resume_id: str = Field(..., description="Resume identifier")
    filename: str = Field(..., description="Original filename")
    extraction: DocumentExtractionResult = Field(..., description="Document extraction result")
    candidate_info: ExtractedResumeInfo = Field(..., description="Extracted candidate information")


class JobAnalysisRequest(BaseModel):
    """Request for job analysis endpoint."""

    job_description: str = Field(..., description="Job description text")


class JobAnalysisResponse(BaseModel):
    """Response for job analysis endpoint."""

    job_id: str = Field(..., description="Unique identifier for the analyzed job")
    analysis: AnalyzedJobDescription = Field(..., description="Analyzed job requirements")


class JobRetrieveResponse(BaseModel):
    """Response for job retrieval endpoint."""

    job_id: str = Field(..., description="Job identifier")
    analysis: AnalyzedJobDescription = Field(..., description="Analyzed job requirements")


class MatchingRequest(BaseModel):
    """Request for matching evaluation endpoint."""

    job_id: str = Field(..., description="Job identifier to match against")
    resume_ids: List[str] = Field(..., description="List of resume identifiers to evaluate")
    use_semantic: bool = Field(default=True, description="Whether to use semantic similarity")


class CandidateMatchResult(BaseModel):
    """Individual candidate match result."""

    resume_id: str = Field(..., description="Resume identifier")
    filename: str = Field(..., description="Original filename")
    candidate_name: str = Field(..., description="Candidate name")
    match_result: MatchResult = Field(..., description="Match score and details")
    error: Optional[str] = Field(default=None, description="Error message if matching failed")


class MatchingResponse(BaseModel):
    """Response for matching evaluation endpoint."""

    job_id: str = Field(..., description="Job identifier used for matching")
    total_candidates: int = Field(..., description="Total number of candidates evaluated")
    successful: int = Field(..., description="Number of successfully matched candidates")
    failed: int = Field(..., description="Number of candidates that failed matching")
    results: List[CandidateMatchResult] = Field(..., description="Individual candidate match results, sorted by score descending")


class ReportRequest(BaseModel):
    """Request for report generation."""

    job_id: str = Field(..., description="Job identifier")
    resume_id: str = Field(..., description="Resume identifier")
    format: str = Field(default="json", description="Report format (json or csv)")


class ReportResponse(BaseModel):
    """Response for report retrieval endpoint."""

    report_id: str = Field(..., description="Unique identifier for the report")
    format: str = Field(..., description="Report format")
    content: str = Field(..., description="Report content as string")
