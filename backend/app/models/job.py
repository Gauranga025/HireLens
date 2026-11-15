from typing import List, Dict

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Job(Base, UUIDMixin, TimestampMixin):
    """Job model for storing job descriptions and analysis."""
    
    __tablename__ = "jobs"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    preferred_skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    qualifications: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    experience_required: Mapped[str] = mapped_column(String(255), nullable=False, default="Not specified")
    analysis_data: Mapped[Dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    screening_results: Mapped[List["ScreeningResult"]] = relationship(
        "ScreeningResult",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_jobs_title", "title"),
    )
