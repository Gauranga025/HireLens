import uuid
from typing import Any, Dict, List, Optional

from app.schemas.resume import ExtractedResumeInfo, DocumentExtractionResult
from app.schemas.job import AnalyzedJobDescription


class ResumeRepository:
    """In-memory repository for storing processed resumes.
    
    Designed to be replaced with PostgreSQL in future stages.
    """

    def __init__(self) -> None:
        self._resumes: Dict[str, Dict[str, Any]] = {}

    def save(
        self,
        filename: str,
        extraction: DocumentExtractionResult,
        candidate_info: ExtractedResumeInfo,
    ) -> str:
        """Save a processed resume and return its ID."""
        resume_id = str(uuid.uuid4())
        self._resumes[resume_id] = {
            "resume_id": resume_id,
            "filename": filename,
            "extraction": extraction.model_dump(),
            "candidate_info": candidate_info.model_dump(),
        }
        return resume_id

    def get(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a processed resume by ID."""
        return self._resumes.get(resume_id)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all stored resumes."""
        return list(self._resumes.values())

    def delete(self, resume_id: str) -> bool:
        """Delete a resume by ID. Returns True if deleted, False if not found."""
        if resume_id in self._resumes:
            del self._resumes[resume_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all stored resumes."""
        self._resumes.clear()


class JobRepository:
    """In-memory repository for storing analyzed job descriptions.
    
    Designed to be replaced with PostgreSQL in future stages.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def save(self, analysis: AnalyzedJobDescription) -> str:
        """Save an analyzed job description and return its ID."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "analysis": analysis.model_dump(),
        }
        return job_id

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an analyzed job by ID."""
        return self._jobs.get(job_id)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all stored jobs."""
        return list(self._jobs.values())

    def delete(self, job_id: str) -> bool:
        """Delete a job by ID. Returns True if deleted, False if not found."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all stored jobs."""
        self._jobs.clear()


class ReportRepository:
    """In-memory repository for storing generated reports.
    
    Designed to be replaced with PostgreSQL in future stages.
    """

    def __init__(self) -> None:
        self._reports: Dict[str, Dict[str, Any]] = {}

    def save(self, format: str, content: str) -> str:
        """Save a generated report and return its ID."""
        report_id = str(uuid.uuid4())
        self._reports[report_id] = {
            "report_id": report_id,
            "format": format,
            "content": content,
        }
        return report_id

    def get(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        return self._reports.get(report_id)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all stored reports."""
        return list(self._reports.values())

    def delete(self, report_id: str) -> bool:
        """Delete a report by ID. Returns True if deleted, False if not found."""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all stored reports."""
        self._reports.clear()


# Global repository instances (for this stage)
resume_repository = ResumeRepository()
job_repository = JobRepository()
report_repository = ReportRepository()
