from typing import List, Optional
from pydantic import BaseModel, Field


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
