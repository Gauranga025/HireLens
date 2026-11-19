import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.job_repository import JobRepository, get_structured_requirements
from app.schemas.api import JobAnalysisRequest, JobAnalysisResponse, JobRetrieveResponse
from app.schemas.job import AnalyzedJobDescription
from app.services.job_analysis_service import analyze_job_description
from app.utils.serialization import serialize_for_jsonb

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=JobAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_job(
    request: JobAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> JobAnalysisResponse:
    """
    Analyze a job description to extract requirements.
    
    Extracts job title, required skills, preferred skills, qualifications,
    and experience requirements from the provided job description text.
    """
    if not request.job_description or not request.job_description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description cannot be empty",
        )

    try:
        analysis_dict = analyze_job_description(request.job_description)
        analysis = AnalyzedJobDescription(**analysis_dict)

        job_repo = JobRepository()
        job = await job_repo.create(
            db=db,
            title=analysis.title,
            description=request.job_description,
            required_skills=analysis.required_skills,
            preferred_skills=analysis.preferred_skills,
            qualifications=analysis.qualifications,
            experience_required=analysis.experience_required,
            structured_requirements=serialize_for_jsonb(analysis.structured_requirements),
            analysis_data=serialize_for_jsonb(analysis),
        )
        await db.commit()

        return JobAnalysisResponse(
            job_id=str(job.id),
            analysis=analysis,
        )

    except Exception as e:
        logger.error(f"Job analysis failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze job description",
        )


@router.get("/{job_id}", response_model=JobRetrieveResponse, status_code=status.HTTP_200_OK)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobRetrieveResponse:
    """
    Retrieve an analyzed job description by its ID.
    
    Returns the analyzed job requirements including skills and experience.
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job ID format: '{job_id}'",
        )

    job_repo = JobRepository()
    job = await job_repo.get_by_id(db, job_uuid)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    # Prefer the dedicated structured_requirements column, which is also
    # populated for jobs created after Phase 10.1. Merge flat/legacy fields as
    # fallbacks so jobs persisted before structured requirements still load.
    analysis_payload = dict(job.analysis_data or {})
    analysis_payload["structured_requirements"] = get_structured_requirements(job)
    analysis_payload.setdefault("title", job.title)
    analysis_payload.setdefault("required_skills", job.required_skills or [])
    analysis_payload.setdefault("preferred_skills", job.preferred_skills or [])
    analysis_payload.setdefault("qualifications", job.qualifications or [])
    analysis_payload.setdefault("experience_required", job.experience_required)
    analysis_payload.setdefault("raw_text", job.description)

    analysis = AnalyzedJobDescription(**analysis_payload)

    return JobRetrieveResponse(
        job_id=str(job.id),
        analysis=analysis,
    )
