from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field, field_validator


class EducationEntry(BaseModel):
    """Education entry schema."""

    degree: str = Field(..., description="Degree obtained")
    institution: str = Field(..., description="Institution name")
    year: str = Field(..., description="Year or year range")


class ExperienceEntry(BaseModel):
    """Work experience entry schema."""

    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    duration: str = Field(..., description="Employment duration (original string)")
    experience_type: Optional[str] = Field(default=None, description="Experience type (full_time, internship, etc.)")
    start_date: Optional[str] = Field(default=None, description="Start date (normalized YYYY-MM)")
    end_date: Optional[str] = Field(default=None, description="End date (normalized YYYY-MM)")
    is_current: Optional[bool] = Field(default=False, description="Whether this is a current position")
    duration_months: Optional[int] = Field(default=None, description="Duration in months")
    recency_category: Optional[str] = Field(default=None, description="Recency category (within_6_months, within_1_year, etc.)")
    temporal_status: Optional[str] = Field(default=None, description="Temporal status (current, completed, open_ended, unknown, invalid)")
    date_confidence: Optional[float] = Field(default=None, description="Confidence in date parsing (0.0 to 1.0)")


class ProjectEntry(BaseModel):
    """Project entry schema with intelligence metadata."""

    title: str = Field(..., description="Project title or description")
    project_type: Optional[str] = Field(default=None, description="Project type (academic_project, personal_project)")
    technologies: List[str] = Field(default_factory=list, description="Technologies used in project")
    complexity_indicators: List[str] = Field(default_factory=list, description="Technical complexity indicators")
    implementation_evidence: List[str] = Field(default_factory=list, description="Evidence of implementation")
    measurable_outcomes: List[str] = Field(default_factory=list, description="Measurable outcomes achieved")
    complexity_level: Optional[str] = Field(default=None, description="Complexity level (UNASSESSED, LOW, MEDIUM, HIGH)")
    description: Optional[str] = Field(default=None, description="Full project description")
    start_date: Optional[str] = Field(default=None, description="Start date (normalized YYYY-MM)")
    end_date: Optional[str] = Field(default=None, description="End date (normalized YYYY-MM)")
    is_current: Optional[bool] = Field(default=False, description="Whether this is a current project")
    duration_months: Optional[int] = Field(default=None, description="Duration in months")
    recency_category: Optional[str] = Field(default=None, description="Recency category")
    temporal_status: Optional[str] = Field(default=None, description="Temporal status")
    date_confidence: Optional[float] = Field(default=None, description="Confidence in date parsing")


class ExtractedResumeInfo(BaseModel):
    """Extracted resume information schema."""

    name: str = Field(..., description="Candidate name")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    education: List[EducationEntry] = Field(default_factory=list, description="Education history")
    experience: List[ExperienceEntry] = Field(default_factory=list, description="Work experience")
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    projects: List[Union[ProjectEntry, str]] = Field(default_factory=list, description="Key projects")
    skills: List[str] = Field(default_factory=list, description="Detected skills")

    @field_validator('projects', mode='before')
    @classmethod
    def normalize_projects(cls, v):
        """Convert string projects to ProjectEntry for backward compatibility."""
        if not v:
            return []
        normalized = []
        for item in v:
            if isinstance(item, str):
                normalized.append(ProjectEntry(title=item, description=item))
            else:
                normalized.append(item)
        return normalized


class DocumentExtractionResult(BaseModel):
    """Document text extraction result schema."""

    text: str = Field(..., description="Extracted text content")
    source_format: str = Field(..., description="Source file format (pdf or docx)")
    num_pages: Optional[int] = Field(default=None, description="Number of pages (PDF only)")
    num_paragraphs: Optional[int] = Field(default=None, description="Number of paragraphs (DOCX only)")
    is_scanned: bool = Field(default=False, description="Whether document appears to be scanned")
    metadata: Dict = Field(default_factory=dict, description="Document metadata")
