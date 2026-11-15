from typing import Optional, List, Dict
from uuid import UUID

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Resume(Base, UUIDMixin, TimestampMixin):
    """Resume model for storing processed resume data."""
    
    __tablename__ = "resumes"
    
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    candidate_info: Mapped[Dict] = mapped_column(JSONB, nullable=False, default=dict)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    
    screening_results: Mapped[List["ScreeningResult"]] = relationship(
        "ScreeningResult",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_resumes_email", "email"),
        Index("ix_resumes_candidate_name", "candidate_name"),
        Index("ix_resumes_processing_status", "processing_status"),
    )
