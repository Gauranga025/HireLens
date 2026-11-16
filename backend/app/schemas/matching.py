from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SkillEvidence(BaseModel):
    """Evidence for a skill found in resume."""
    
    skill: str = Field(..., description="Skill name")
    section: str = Field(..., description="Resume section where skill was found")
    evidence_type: str = Field(..., description="Type of evidence (demonstrated_in_experience, listed_in_skills, etc.)")
    snippet: str = Field(..., description="Supporting text snippet")
    strength: str = Field(..., description="Evidence strength (strong, moderate, basic, weak)")
    start_offset: Optional[int] = Field(default=None, description="Start offset in original text")
    end_offset: Optional[int] = Field(default=None, description="End offset in original text")


class RequirementMatch(BaseModel):
    """Match result for a specific job requirement."""
    
    requirement: str = Field(..., description="Job requirement text")
    matched: bool = Field(..., description="Whether requirement was matched")
    similarity_score: Optional[float] = Field(default=None, description="Semantic similarity score (0-1)")
    evidence: List[SkillEvidence] = Field(default_factory=list, description="Supporting evidence")
    is_alternative: bool = Field(default=False, description="Whether this is an alternative requirement")


class ScoringStrategy(BaseModel):
    """Metadata about the scoring strategy used."""
    
    algorithm_version: str = Field(..., description="Version of the scoring algorithm")
    components: List[str] = Field(default_factory=list, description="Active scoring components")
    weights: Dict[str, float] = Field(default_factory=dict, description="Weights used for each component")
    semantic_available: bool = Field(default=False, description="Whether semantic matching was available")
    fallback_used: bool = Field(default=False, description="Whether fallback scoring was used")


class MatchResult(BaseModel):
    """Resume-job match result schema."""

    overall_score: float = Field(..., description="Overall match score (0-100)")
    tfidf_score: float = Field(..., description="TF-IDF lexical similarity score (0-100)")
    semantic_score: Optional[float] = Field(default=None, description="Semantic similarity score (0-100)")
    skill_match_score: float = Field(..., description="Skill match percentage (0-100)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills matched from requirements")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills not found in resume")
    additional_skills: List[str] = Field(default_factory=list, description="Skills in resume not in requirements")
    explanation: str = Field(..., description="Detailed explanation of the match")
    
    # New evidence and scoring fields
    skill_evidence: Dict[str, List[SkillEvidence]] = Field(
        default_factory=dict,
        description="Evidence for each matched skill"
    )
    requirement_matches: List[RequirementMatch] = Field(
        default_factory=list,
        description="Match results for individual requirements"
    )
    required_skill_coverage: float = Field(
        default=0.0,
        description="Percentage of required skills covered"
    )
    preferred_skill_coverage: float = Field(
        default=0.0,
        description="Percentage of preferred skills covered"
    )
    scoring_strategy: Optional[ScoringStrategy] = Field(
        default=None,
        description="Scoring strategy metadata"
    )
