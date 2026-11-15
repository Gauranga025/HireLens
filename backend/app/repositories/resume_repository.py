from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume


class ResumeRepository:
    """Repository for Resume database operations."""
    
    async def create(
        self,
        db: AsyncSession,
        original_filename: str,
        file_type: str,
        candidate_name: Optional[str],
        email: Optional[str],
        phone: Optional[str],
        candidate_info: Dict,
        extracted_text: str,
        skills: List[str],
        storage_key: str,
        processing_status: str = "completed",
    ) -> Resume:
        """Create a new resume record.
        
        Args:
            db: Database session.
            original_filename: Original filename.
            file_type: File type (pdf or docx).
            candidate_name: Extracted candidate name.
            email: Extracted email.
            phone: Extracted phone.
            candidate_info: Structured candidate information.
            extracted_text: Extracted text content.
            skills: Extracted skills list.
            storage_key: File storage key.
            processing_status: Processing status.
        
        Returns:
            Created Resume instance.
        """
        resume = Resume(
            original_filename=original_filename,
            file_type=file_type,
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            candidate_info=candidate_info,
            extracted_text=extracted_text,
            skills=skills,
            storage_key=storage_key,
            processing_status=processing_status,
        )
        
        db.add(resume)
        await db.flush()
        await db.refresh(resume)
        
        return resume
    
    async def get_by_id(self, db: AsyncSession, resume_id: UUID) -> Optional[Resume]:
        """Retrieve a resume by ID.
        
        Args:
            db: Database session.
            resume_id: Resume UUID.
        
        Returns:
            Resume instance or None if not found.
        """
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        return result.scalar_one_or_none()
    
    async def get_by_ids(self, db: AsyncSession, resume_ids: List[UUID]) -> List[Resume]:
        """Retrieve multiple resumes by IDs.
        
        Args:
            db: Database session.
            resume_ids: List of resume UUIDs.
        
        Returns:
            List of Resume instances.
        """
        result = await db.execute(
            select(Resume).where(Resume.id.in_(resume_ids))
        )
        return list(result.scalars().all())
    
    async def get_all(self, db: AsyncSession, limit: int = 100, offset: int = 0) -> List[Resume]:
        """Retrieve all resumes with pagination.
        
        Args:
            db: Database session.
            limit: Maximum number of results.
            offset: Number of results to skip.
        
        Returns:
            List of Resume instances.
        """
        result = await db.execute(
            select(Resume).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
    
    async def delete(self, db: AsyncSession, resume_id: UUID) -> bool:
        """Delete a resume by ID.
        
        Args:
            db: Database session.
            resume_id: Resume UUID.
        
        Returns:
            True if deleted, False if not found.
        """
        resume = await self.get_by_id(db, resume_id)
        if not resume:
            return False
        
        await db.delete(resume)
        return True
