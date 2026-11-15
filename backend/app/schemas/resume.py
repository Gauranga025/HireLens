from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class EducationEntry(BaseModel):
    """Education entry schema."""

    degree: str = Field(..., description="Degree obtained")
    institution: str = Field(..., description="Institution name")
    year: str = Field(..., description="Year or year range")


class ExperienceEntry(BaseModel):
    """Work experience entry schema."""

    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    duration: str = Field(..., description="Employment duration")


class ExtractedResumeInfo(BaseModel):
    """Extracted resume information schema."""

    name: str = Field(..., description="Candidate name")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    education: List[EducationEntry] = Field(default_factory=list, description="Education history")
    experience: List[ExperienceEntry] = Field(default_factory=list, description="Work experience")
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    projects: List[str] = Field(default_factory=list, description="Key projects")
    skills: List[str] = Field(default_factory=list, description="Detected skills")


class DocumentExtractionResult(BaseModel):
    """Document text extraction result schema."""

    text: str = Field(..., description="Extracted text content")
    source_format: str = Field(..., description="Source file format (pdf or docx)")
    num_pages: Optional[int] = Field(default=None, description="Number of pages (PDF only)")
    num_paragraphs: Optional[int] = Field(default=None, description="Number of paragraphs (DOCX only)")
    is_scanned: bool = Field(default=False, description="Whether document appears to be scanned")
    metadata: Dict = Field(default_factory=dict, description="Document metadata")
