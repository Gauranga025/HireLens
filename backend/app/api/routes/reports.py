import logging
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import report_repository
from app.db.session import get_db
from app.repositories.job_repository import JobRepository, get_structured_requirements
from app.repositories.resume_repository import ResumeRepository
from app.schemas.api import ReportResponse
from app.services.candidate_evaluation_service import (
    CandidateEvaluationContext,
    CandidateEvaluationService,
)
from app.services.report_service import generate_csv_report, generate_json_report
from app.services.scoring_service import ScoringConfig

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
        candidate_info = resume.candidate_info or {}
        job_analysis = job.analysis_data or {}
        job_title = job_analysis.get("title", job.title or "Not specified")

        # Use the same unified evaluation pipeline and configuration as
        # /matching/evaluate so exported scores match the displayed scores.
        structured_requirements = get_structured_requirements(job)
        evaluation_service = CandidateEvaluationService(
            scoring_config=ScoringConfig(
                keyword_stuffing_education_aware=True,
                related_skill_credit_threshold=0.5,
            )
        )
        context = CandidateEvaluationContext(
            resume_text=resume.extracted_text,
            job_text=job.description or job_analysis.get("raw_text", ""),
            resume_skills=resume.skills,
            required_skills=job.required_skills or job_analysis.get("required_skills", []),
            preferred_skills=(
                job.preferred_skills
                or job_analysis.get("preferred_skills", [])
            ),
            use_semantic=True,
            experience_metadata=candidate_info.get("experience", []),
            project_metadata=candidate_info.get("projects", []),
            structured_requirements=structured_requirements,
        )
        match_dict = asdict(evaluation_service.evaluate_candidate(context))

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
