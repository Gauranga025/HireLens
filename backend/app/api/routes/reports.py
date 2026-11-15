import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import report_repository
from app.db.session import get_db
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.schemas.api import ReportResponse
from app.services.report_service import generate_csv_report, generate_json_report

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)


@router.get("/{report_id}", response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def get_report(report_id: str) -> ReportResponse:
    """
    Retrieve a generated report by its ID.
    
    Returns the report content in the format it was generated (JSON or CSV).
    """
    report_data = report_repository.get(report_id)

    if not report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found",
        )

    return ReportResponse(
        report_id=report_id,
        format=report_data["format"],
        content=report_data["content"],
    )


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def generate_report(
    job_id: str,
    resume_id: str,
    format: str = "json",
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """
    Generate a match report for a specific resume and job.
    
    Supports JSON and CSV formats. The report includes match scores,
    skill analysis, and improvement suggestions.
    """
    if format not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be either 'json' or 'csv'",
        )

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job ID format: '{job_id}'",
        )

    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resume ID format: '{resume_id}'",
        )

    job_repo = JobRepository()
    resume_repo = ResumeRepository()

    job = await job_repo.get_by_id(db, job_uuid)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    resume = await resume_repo.get_by_id(db, resume_uuid)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID '{resume_id}' not found",
        )

    try:
        candidate_info = resume.candidate_info
        job_analysis = job.analysis_data
        job_title = job_analysis.get("title", "Not specified")

        from app.services.matching_service import compute_match

        match_dict = compute_match(
            resume_text=resume.extracted_text,
            job_text=job_analysis.get("raw_text", ""),
            resume_skills=resume.skills,
            job_skills=job_analysis.get("required_skills", []),
            use_semantic=True,
        )

        if format == "json":
            content = generate_json_report(
                candidate_info=candidate_info,
                match_result=match_dict,
                job_title=job_title,
            )
        else:
            content = generate_csv_report(
                candidate_info=candidate_info,
                match_result=match_dict,
                job_title=job_title,
            )

        report_id = report_repository.save(format=format, content=content)

        return ReportResponse(
            report_id=report_id,
            format=format,
            content=content,
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )
