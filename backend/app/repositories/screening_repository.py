from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening_result import ScreeningResult


class ScreeningRepository:
    """Repository for ScreeningResult database operations."""
    
    async def create(
        self,
        db: AsyncSession,
        job_id: UUID,
        resume_id: UUID,
        overall_score: float,
        tfidf_score: float,
        semantic_score: Optional[float],
        skill_match_score: float,
        matched_skills: List[str],
        missing_skills: List[str],
        additional_skills: List[str],
        explanation: str,
        screening_status: str = "completed",
        skill_evidence: Optional[Dict] = None,
        requirement_matches: Optional[List[Dict]] = None,
        required_skill_coverage: float = 0.0,
        preferred_skill_coverage: float = 0.0,
        scoring_strategy: Optional[Dict] = None,
    ) -> ScreeningResult:
        """Create a new screening result record.
        
        Args:
            db: Database session.
            job_id: Job UUID.
            resume_id: Resume UUID.
            overall_score: Overall match score.
            tfidf_score: TF-IDF similarity score.
            semantic_score: Semantic similarity score (may be None).
            skill_match_score: Skill match percentage.
            matched_skills: List of matched skills.
            missing_skills: List of missing skills.
            additional_skills: List of additional skills in resume.
            explanation: Match explanation text.
            screening_status: Screening status.
            skill_evidence: Skill evidence dictionary.
            requirement_matches: Requirement match results.
            required_skill_coverage: Required skill coverage percentage.
            preferred_skill_coverage: Preferred skill coverage percentage.
            scoring_strategy: Scoring strategy metadata.
        
        Returns:
            Created ScreeningResult instance.
        """
        screening = ScreeningResult(
            job_id=job_id,
            resume_id=resume_id,
            overall_score=overall_score,
            tfidf_score=tfidf_score,
            semantic_score=semantic_score,
            skill_match_score=skill_match_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            additional_skills=additional_skills,
            explanation=explanation,
            screening_status=screening_status,
            skill_evidence=skill_evidence,
            requirement_matches=requirement_matches,
            required_skill_coverage=required_skill_coverage,
            preferred_skill_coverage=preferred_skill_coverage,
            scoring_strategy=scoring_strategy,
        )
        
        try:
            db.add(screening)
            await db.flush()
            await db.refresh(screening)
        except Exception as e:
            await db.rollback()
            raise
        
        return screening
    
    async def get_by_id(self, db: AsyncSession, screening_id: UUID) -> Optional[ScreeningResult]:
        """Retrieve a screening result by ID.
        
        Args:
            db: Database session.
            screening_id: ScreeningResult UUID.
        
        Returns:
            ScreeningResult instance or None if not found.
        """
        result = await db.execute(
            select(ScreeningResult).where(ScreeningResult.id == screening_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_job_and_resume(
        self, db: AsyncSession, job_id: UUID, resume_id: UUID
    ) -> Optional[ScreeningResult]:
        """Retrieve a screening result by job and resume IDs.
        
        Args:
            db: Database session.
            job_id: Job UUID.
            resume_id: Resume UUID.
        
        Returns:
            ScreeningResult instance or None if not found.
        """
        result = await db.execute(
            select(ScreeningResult).where(
                ScreeningResult.job_id == job_id,
                ScreeningResult.resume_id == resume_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_job_id(
        self, db: AsyncSession, job_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[ScreeningResult]:
        """Retrieve all screening results for a job.
        
        Args:
            db: Database session.
            job_id: Job UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.
        
        Returns:
            List of ScreeningResult instances.
        """
        result = await db.execute(
            select(ScreeningResult)
            .where(ScreeningResult.job_id == job_id)
            .order_by(ScreeningResult.overall_score.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_by_resume_id(
        self, db: AsyncSession, resume_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[ScreeningResult]:
        """Retrieve all screening results for a resume.
        
        Args:
            db: Database session.
            resume_id: Resume UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.
        
        Returns:
            List of ScreeningResult instances.
        """
        result = await db.execute(
            select(ScreeningResult)
            .where(ScreeningResult.resume_id == resume_id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def delete(self, db: AsyncSession, screening_id: UUID) -> bool:
        """Delete a screening result by ID.
        
        Args:
            db: Database session.
            screening_id: ScreeningResult UUID.
        
        Returns:
            True if deleted, False if not found.
        """
        screening = await self.get_by_id(db, screening_id)
        if not screening:
            return False
        
        await db.delete(screening)
        return True
