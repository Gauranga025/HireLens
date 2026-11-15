from typing import Optional, List
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ScreeningResult(Base, UUIDMixin, TimestampMixin):
    """Screening result model for storing resume-job match results."""
    
    __tablename__ = "screening_results"
    
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    tfidf_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skill_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    missing_skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    additional_skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    screening_status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    
    job: Mapped["Job"] = relationship("Job", back_populates="screening_results")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="screening_results")
    
    __table_args__ = (
        UniqueConstraint("job_id", "resume_id", name="uq_job_resume_screening"),
        Index("ix_screening_results_overall_score", "overall_score"),
        Index("ix_screening_results_job_id", "job_id"),
        Index("ix_screening_results_resume_id", "resume_id"),
    )
