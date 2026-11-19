from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.utils.serialization import serialize_for_jsonb


def get_structured_requirements(job: Job) -> List[Dict]:
    """Return Phase 10 requirements with a legacy fallback.

    The dedicated column is authoritative when populated. Rows created before
    the column existed have an empty list (the column is NOT NULL with a
    server default), so fall back to the requirements stored inside
    ``analysis_data`` for those jobs.
    """
    if job.structured_requirements:
        return job.structured_requirements
    analysis = job.analysis_data or {}
    return analysis.get("structured_requirements") or []


class JobRepository:
    """Repository for Job database operations."""
    
    async def create(
        self,
        db: AsyncSession,
        title: str,
        description: str,
        required_skills: List[str],
        preferred_skills: List[str],
        qualifications: List[str],
        experience_required: str,
        structured_requirements: Optional[List[Dict]] = None,
        analysis_data: Optional[Dict] = None,
    ) -> Job:
        """Create a new job record.
        
        Args:
            db: Database session.
            title: Job title.
            description: Job description text.
            required_skills: Required skills list.
            preferred_skills: Preferred skills list.
            qualifications: Qualifications list.
            experience_required: Experience requirement text.
            structured_requirements: Structured requirements list.
            analysis_data: Full analysis data from job_analysis_service.
        
        Returns:
            Created Job instance.
        """
        # JSONB values must contain only JSON-compatible primitives. Normalize
        # here so every caller (routes, scripts, tests) is protected from
        # accidentally sending Pydantic models or enum members to PostgreSQL.
        job = Job(
            title=title,
            description=description,
            required_skills=serialize_for_jsonb(required_skills or []),
            preferred_skills=serialize_for_jsonb(preferred_skills or []),
            qualifications=serialize_for_jsonb(qualifications or []),
            experience_required=experience_required,
            structured_requirements=serialize_for_jsonb(structured_requirements or []),
            analysis_data=serialize_for_jsonb(analysis_data or {}),
        )
        
        db.add(job)
        await db.flush()
        await db.refresh(job)
        
        return job
    
    async def get_by_id(self, db: AsyncSession, job_id: UUID) -> Optional[Job]:
        """Retrieve a job by ID.
        
        Args:
            db: Database session.
            job_id: Job UUID.
        
        Returns:
            Job instance or None if not found.
        """
        result = await db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()
    
    async def get_all(self, db: AsyncSession, limit: int = 100, offset: int = 0) -> List[Job]:
        """Retrieve all jobs with pagination.
        
        Args:
            db: Database session.
            limit: Maximum number of results.
            offset: Number of results to skip.
        
        Returns:
            List of Job instances.
        """
        result = await db.execute(
            select(Job).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def delete(self, db: AsyncSession, job_id: UUID) -> bool:
        """Delete a job by ID.
        
        Args:
            db: Database session.
            job_id: Job UUID.
        
        Returns:
            True if deleted, False if not found.
        """
        job = await self.get_by_id(db, job_id)
        if not job:
            return False
        
        await db.delete(job)
        return True
