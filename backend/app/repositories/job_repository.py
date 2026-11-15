from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


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
        analysis_data: Dict,
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
            analysis_data: Full analysis data from job_analysis_service.
        
        Returns:
            Created Job instance.
        """
        job = Job(
            title=title,
            description=description,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            qualifications=qualifications,
            experience_required=experience_required,
            analysis_data=analysis_data,
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
