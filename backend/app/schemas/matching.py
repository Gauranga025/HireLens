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
    demonstration_level: Optional[str] = Field(default=None, description="Demonstration level (claimed, mentioned, implemented, measurable)")
    date_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Date and context information")
    experience_type: Optional[str] = Field(default=None, description="Experience type (full_time, internship, etc.)")
    project_info: Optional[Dict[str, Any]] = Field(default=None, description="Project information")
    temporal_info: Optional[Dict[str, Any]] = Field(default=None, description="Temporal information")


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
    weights: Dict[str, float] = Field(default_factory=dict, description="Effective weights used for each component")
    configured_weights: Dict[str, float] = Field(default_factory=dict, description="Configured weights before semantic normalization")
    semantic_available: bool = Field(default=False, description="Whether semantic matching was actually used")
    semantic_status: str = Field(default="used", description="Semantic path: used, disabled, model_unavailable, inference_failed, or empty_text")
    semantic_model_available: Optional[bool] = Field(default=None, description="Whether the semantic model was available when evaluated")
    semantic_error: Optional[Dict[str, str]] = Field(default=None, description="Semantic model or inference error information")
    semantic_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Bounded, additive requirement-to-chunk semantic diagnostics"
    )
    fallback_used: bool = Field(default=False, description="Whether unavailable/failed semantic scoring used normalized fallback weights")
    skill_hierarchy_enabled: bool = Field(default=False, description="Whether skill hierarchy matching is enabled")
    demonstration_levels_enabled: bool = Field(default=False, description="Whether demonstration level weighting is enabled")
    keyword_stuffing_penalty_enabled: bool = Field(default=False, description="Whether keyword stuffing penalty is enabled")
    keyword_stuffing_education_aware: bool = Field(default=False, description="Whether keyword stuffing detection is education-aware")
    related_skill_credit_threshold: float = Field(default=1.0, description="Minimum credit for hierarchy match")
    evaluation_date: Optional[str] = Field(default=None, description="Evaluation date for temporal calculations")


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
    evidence_score: Optional[float] = Field(default=None, description="Evidence strength score (0-100)")
    evidence_summary: Optional[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description="Summary of demonstrated, mentioned, and unsupported skills"
    )
    requirement_evaluations: Optional[Dict[str, Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Detailed evaluation of each requirement with evidence context"
    )
    strengths: Optional[List[str]] = Field(
        default_factory=list,
        description="Strengths identified from evidence"
    )
    gaps: Optional[List[str]] = Field(
        default_factory=list,
        description="Gaps identified from missing evidence"
    )
    temporal_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Temporal intelligence metadata (duration, recency, timeline)"
    )
    keyword_stuffing_penalty: Optional[float] = Field(
        default=0.0,
        description="Keyword stuffing penalty applied to score"
    )
    keyword_stuffing_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Keyword stuffing analysis details"
    )
    group_evaluation: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Group-level evaluation details for alternative skill groups (Phase 10.2)"
    )
