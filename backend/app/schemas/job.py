from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RequirementType(str, Enum):
    """Requirement type categories."""
    REQUIRED = "REQUIRED"
    REQUIRED_GROUP = "REQUIRED_GROUP"
    PREFERRED = "PREFERRED"
    OPTIONAL = "OPTIONAL"
    EXPERIENCE = "EXPERIENCE"
    FUNDAMENTAL = "FUNDAMENTAL"


class MatchMode(str, Enum):
    """Match mode for requirement groups."""
    ANY = "ANY"  # At least one skill must match
    ALL = "ALL"  # All skills must match


class ExperienceType(str, Enum):
    """Experience type categories."""
    PROFESSIONAL = "professional"
    INTERNSHIP = "internship"
    ANY = "any"


class SkillRequirement(BaseModel):
    """Individual skill requirement."""
    skill: str = Field(..., description="Skill name")
    normalized_skill: Optional[str] = Field(None, description="Normalized skill name")
    original_text: str = Field(..., description="Original text from JD")


class RequirementGroup(BaseModel):
    """Group of alternative skills."""
    requirement_type: Literal[RequirementType.REQUIRED_GROUP] = Field(default=RequirementType.REQUIRED_GROUP)
    group_name: str = Field(..., description="Group name (e.g., 'Programming Languages')")
    match_mode: MatchMode = Field(default=MatchMode.ANY, description="ANY or ALL")
    skills: List[SkillRequirement] = Field(..., description="List of alternative skills")
    original_text: str = Field(..., description="Original text from JD")


class ExperienceRequirement(BaseModel):
    """Experience requirement."""
    requirement_type: Literal[RequirementType.EXPERIENCE] = Field(default=RequirementType.EXPERIENCE)
    min_years: Optional[int] = Field(None, description="Minimum years of experience")
    max_years: Optional[int] = Field(None, description="Maximum years of experience")
    experience_type: ExperienceType = Field(default=ExperienceType.ANY, description="Type of experience")
    original_text: str = Field(..., description="Original text from JD")


class FundamentalRequirement(BaseModel):
    """Fundamental engineering requirement."""
    requirement_type: Literal[RequirementType.FUNDAMENTAL] = Field(default=RequirementType.FUNDAMENTAL)
    skill: str = Field(..., description="Fundamental skill name")
    normalized_skill: Optional[str] = Field(None, description="Normalized skill name")
    original_text: str = Field(..., description="Original text from JD")


class StructuredRequirement(BaseModel):
    """Structured requirement (union of all requirement types)."""
    requirement_type: RequirementType = Field(..., description="Requirement type")
    data: Dict[str, Any] = Field(..., description="Requirement data (group, experience, or skill)")
    original_text: str = Field(..., description="Original text from JD")


class AnalyzedJobDescription(BaseModel):
    """Analyzed job description schema."""

    title: str = Field(..., description="Job title")
    required_skills: List[str] = Field(default_factory=list, description="Required skills (backward compatibility)")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills (backward compatibility)")
    qualifications: List[str] = Field(default_factory=list, description="Qualification requirements")
    experience_required: str = Field(default="Not specified", description="Required experience (backward compatibility)")
    structured_requirements: List[StructuredRequirement] = Field(default_factory=list, description="Structured requirements")
    raw_text: str = Field(..., description="Original job description text")
