from typing import List
from pydantic import BaseModel, Field


class AnalyzedJobDescription(BaseModel):
    """Analyzed job description schema."""

    title: str = Field(..., description="Job title")
    required_skills: List[str] = Field(default_factory=list, description="Required skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills")
    qualifications: List[str] = Field(default_factory=list, description="Qualification requirements")
    experience_required: str = Field(default="Not specified", description="Required experience")
    raw_text: str = Field(..., description="Original job description text")
