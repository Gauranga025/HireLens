import logging
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.screening_repository import ScreeningRepository
from app.schemas.api import CandidateMatchResult, MatchingRequest, MatchingResponse
from app.schemas.matching import MatchResult
from app.services.scoring_service import ScoringService
from app.utils.serialization import serialize_for_jsonb

router = APIRouter(prefix="/matching", tags=["matching"])
logger = logging.getLogger(__name__)


@router.post("/evaluate", response_model=MatchingResponse, status_code=status.HTTP_200_OK)
async def evaluate_matching(
    request: MatchingRequest,
    db: AsyncSession = Depends(get_db),
) -> MatchingResponse:
    """
    Evaluate resume-job matching for multiple candidates against a job.

    Retrieves the job description and resumes from their repositories,
    computes match scores using TF-IDF, semantic similarity, and skill matching,
    and returns results sorted by overall match score descending.
    """
    logger.info("=== MATCHING ENDPOINT INVOKED ===")
    
    # Parse job UUID
    try:
        job_uuid = UUID(request.job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job ID format: '{request.job_id}'",
        )

    job_repo = JobRepository()
    job = await job_repo.get_by_id(db, job_uuid)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{request.job_id}' not found",
        )

    job_analysis = job.analysis_data
    job_text = job_analysis.get("raw_text", "")
    job_skills = job_analysis.get("required_skills", [])
    preferred_skills = job_analysis.get("preferred_skills", [])

    resume_repo = ResumeRepository()
    screening_repo = ScreeningRepository()
    scoring_service = ScoringService()

    resume_uuids: List[UUID] = []
    for resume_id in request.resume_ids:
        try:
            resume_uuids.append(UUID(resume_id))
        except ValueError:
            logger.warning(f"Invalid resume ID format: '{resume_id}'")

    resumes = await resume_repo.get_by_ids(db, resume_uuids)
    resume_map = {str(r.id): r for r in resumes}

    logger.info(f"[DIAGNOSTIC] Repository get_by_ids returned {len(resumes)} resumes out of {len(request.resume_ids)} requested")

    results: list[CandidateMatchResult] = []
    successful = 0
    failed = 0

    for resume_id in request.resume_ids:
        try:
            resume = resume_map.get(resume_id)  # resume_id is string, map keys are strings

            if not resume:
                logger.warning(f"Resume {resume_id} not found in repository")
                failed += 1
                results.append(
                    CandidateMatchResult(
                        resume_id=resume_id,
                        filename="unknown",
                        candidate_name="Unknown",
                        match_result=MatchResult(
                            overall_score=0.0,
                            tfidf_score=0.0,
                            semantic_score=None,
                            skill_match_score=0.0,
                            matched_skills=[],
                            missing_skills=[],
                            additional_skills=[],
                            explanation="Resume not found in repository",
                        ),
                        error="Resume not found",
                    )
                )
                continue

            filename = resume.original_filename
            candidate_info = resume.candidate_info
            candidate_name = candidate_info.get("name", "Unknown")
            resume_text = resume.extracted_text
            resume_skills = resume.skills

            match_dict = scoring_service.compute_match(
                resume_text=resume_text,
                job_text=job_text,
                resume_skills=resume_skills,
                required_skills=job_skills,
                preferred_skills=preferred_skills,
                use_semantic=request.use_semantic,
            )
            match_result = MatchResult(**match_dict)

            await screening_repo.create(
                db=db,
                job_id=job_uuid,
                resume_id=resume.id,
                overall_score=match_result.overall_score,
                tfidf_score=match_result.tfidf_score,
                semantic_score=match_result.semantic_score,
                skill_match_score=match_result.skill_match_score,
                matched_skills=match_result.matched_skills,
                missing_skills=match_result.missing_skills,
                additional_skills=match_result.additional_skills,
                explanation=match_result.explanation,
                screening_status="completed",
                skill_evidence=serialize_for_jsonb(match_result.skill_evidence),
                requirement_matches=serialize_for_jsonb(match_result.requirement_matches),
                required_skill_coverage=match_result.required_skill_coverage,
                preferred_skill_coverage=match_result.preferred_skill_coverage,
                scoring_strategy=serialize_for_jsonb(match_result.scoring_strategy),
            )
            await db.commit()

            results.append(
                CandidateMatchResult(
                    resume_id=resume_id,
                    filename=filename,
                    candidate_name=candidate_name,
                    match_result=match_result,
                    error=None,
                )
            )
            successful += 1

        except Exception as e:
            logger.exception(f"Matching failed for resume {resume_id}")
            failed += 1
            results.append(
                CandidateMatchResult(
                    resume_id=resume_id,
                    filename="unknown",
                    candidate_name="Unknown",
                    match_result=MatchResult(
                        overall_score=0.0,
                        tfidf_score=0.0,
                        semantic_score=None,
                        skill_match_score=0.0,
                        matched_skills=[],
                        missing_skills=[],
                        additional_skills=[],
                        explanation="Matching process failed",
                    ),
                    error="Matching process failed",
                )
            )

    results.sort(key=lambda x: x.match_result.overall_score, reverse=True)

    return MatchingResponse(
        job_id=request.job_id,
        total_candidates=len(request.resume_ids),
        successful=successful,
        failed=failed,
        results=results,
    )
