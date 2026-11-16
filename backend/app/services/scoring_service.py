"""
Scoring service for evidence-aware candidate matching.
Combines skill coverage, semantic relevance, and evidence strength.
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.services.skill_service import match_skills_to_requirements
from app.services.evidence_extraction_service import EvidenceExtractionService, EvidenceStrength, DemonstrationLevel
from app.services.semantic_matching_service import SemanticMatchingService
from app.services.keyword_stuffing_detector import KeywordStuffingDetector
from app.utils.text_processor import preprocess_for_tfidf
from app.services.matching_service import tfidf_similarity

logger = logging.getLogger(__name__)


@dataclass
class ScoringConfig:
    """Configurable scoring weights."""
    required_skill_weight: float = 0.35
    preferred_skill_weight: float = 0.15
    semantic_weight: float = 0.30
    evidence_weight: float = 0.20
    tfidf_weight: float = 0.0  # Optional, can be enabled
    use_skill_hierarchy: bool = True  # Enable skill hierarchy matching
    use_demonstration_levels: bool = True  # Enable demonstration level weighting
    use_keyword_stuffing_penalty: bool = False  # Enable keyword stuffing penalty (disabled by default)
    keyword_stuffing_threshold: float = 0.7  # Threshold for keyword stuffing detection
    keyword_stuffing_penalty_weight: float = 0.15  # Max penalty for keyword stuffing (15%)
    keyword_stuffing_education_aware: bool = False  # Consider education evidence as valid (helps fresh graduates)
    related_skill_credit_threshold: float = 1.0  # Minimum credit for hierarchy match (1.0 = full credit only, 0.5 = allow partial credit)


class ScoringService:
    """Service for evidence-aware candidate scoring."""
    
    ALGORITHM_VERSION = "2.1.1-fairness-improved"
    
    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        semantic_service: Optional[SemanticMatchingService] = None,
    ):
        """
        Initialize the scoring service.
        
        Args:
            config: Scoring configuration (uses defaults if None).
            semantic_service: Semantic matching service (creates new if None).
        """
        self.config = config or ScoringConfig()
        self.semantic_service = semantic_service or SemanticMatchingService()
        self.evidence_service = EvidenceExtractionService()
        self.keyword_stuffing_detector = KeywordStuffingDetector(
            threshold=self.config.keyword_stuffing_threshold,
            education_aware=self.config.keyword_stuffing_education_aware,
        )
    
    def compute_match(
        self,
        resume_text: str,
        job_text: str,
        resume_skills: List[str],
        required_skills: List[str],
        preferred_skills: List[str],
        use_semantic: bool = True,
    ) -> Dict[str, Any]:
        """
        Compute evidence-aware match score.
        
        Args:
            resume_text: Full resume text.
            job_text: Full job description text.
            resume_skills: Skills extracted from resume.
            required_skills: Required skills from job.
            preferred_skills: Preferred skills from job.
            use_semantic: Whether to use semantic matching.
            
        Returns:
            Dictionary with match results and scoring metadata.
        """
        # Extract skill evidence
        skill_evidence = self.evidence_service.extract_skill_evidence(
            resume_text,
            resume_skills,
        )
        
        # Match skills to requirements (with hierarchy if enabled)
        required_match = match_skills_to_requirements(
            resume_skills, required_skills, 
            use_hierarchy=self.config.use_skill_hierarchy,
            related_skill_credit_threshold=self.config.related_skill_credit_threshold,
        )
        preferred_match = match_skills_to_requirements(
            resume_skills, preferred_skills, 
            use_hierarchy=self.config.use_skill_hierarchy,
            related_skill_credit_threshold=self.config.related_skill_credit_threshold,
        )
        
        # Calculate skill coverage scores
        required_coverage = required_match["match_percentage"]
        preferred_coverage = preferred_match["match_percentage"]
        
        # Calculate evidence strength score (with demonstration levels if enabled)
        evidence_score = self._calculate_evidence_score(
            required_match["matched"],
            skill_evidence,
            use_demonstration_levels=self.config.use_demonstration_levels,
        )
        
        # Calculate semantic similarity if available
        semantic_score = None
        if use_semantic and self.semantic_service.is_available():
            semantic_score = self._calculate_semantic_score(
                job_text,
                resume_text,
                required_skills,
                skill_evidence,
            )
        
        # Calculate TF-IDF similarity (optional)
        tfidf_score = 0.0
        if self.config.tfidf_weight > 0:
            tfidf_score = tfidf_similarity(
                preprocess_for_tfidf(resume_text),
                preprocess_for_tfidf(job_text),
            )
        
        # Compute overall score
        # Use fallback formula if semantic unavailable and was requested
        if semantic_score is None and use_semantic:
            # Fallback: 50% required + 50% preferred
            overall_score = (0.5 * required_coverage) + (0.5 * preferred_coverage)
            fallback_used = True
            active_weights = {
                "required_skills": 0.5,
                "preferred_skills": 0.5,
            }
        else:
            overall_score = self._compute_overall_score(
                required_coverage,
                preferred_coverage,
                evidence_score,
                semantic_score,
                tfidf_score,
            )
            fallback_used = False
            active_weights = {
                "required_skills": self.config.required_skill_weight,
                "preferred_skills": self.config.preferred_skill_weight,
                "semantic": self.config.semantic_weight,
                "evidence": self.config.evidence_weight,
                "tfidf": self.config.tfidf_weight,
            }
        
        # Apply keyword stuffing penalty if enabled
        keyword_stuffing_penalty = 0.0
        keyword_stuffing_analysis = None
        if self.config.use_keyword_stuffing_penalty:
            keyword_stuffing_analysis = self.keyword_stuffing_detector.analyze(
                resume_skills,
                skill_evidence,
            )
            if keyword_stuffing_analysis.is_stuffed:
                # Apply penalty (max 15% of score)
                penalty_amount = overall_score * self.config.keyword_stuffing_penalty_weight * keyword_stuffing_analysis.penalty
                overall_score -= penalty_amount
                keyword_stuffing_penalty = penalty_amount
                overall_score = max(overall_score, 0.0)  # Ensure non-negative
        
        # Build scoring strategy metadata
        scoring_strategy = {
            "algorithm_version": self.ALGORITHM_VERSION,
            "components": [],
            "weights": active_weights,
            "semantic_available": semantic_score is not None,
            "fallback_used": fallback_used,
            "skill_hierarchy_enabled": self.config.use_skill_hierarchy,
            "demonstration_levels_enabled": self.config.use_demonstration_levels,
            "keyword_stuffing_penalty_enabled": self.config.use_keyword_stuffing_penalty,
            "keyword_stuffing_education_aware": self.config.keyword_stuffing_education_aware,
            "related_skill_credit_threshold": self.config.related_skill_credit_threshold,
        }
        
        # Add active components
        if required_coverage > 0:
            scoring_strategy["components"].append("required_skills")
        if preferred_coverage > 0:
            scoring_strategy["components"].append("preferred_skills")
        if semantic_score is not None:
            scoring_strategy["components"].append("semantic")
        if evidence_score > 0:
            scoring_strategy["components"].append("evidence")
        if tfidf_score > 0:
            scoring_strategy["components"].append("tfidf")
        if self.config.use_skill_hierarchy:
            scoring_strategy["components"].append("skill_hierarchy")
        if self.config.use_demonstration_levels:
            scoring_strategy["components"].append("demonstration_levels")
        if keyword_stuffing_penalty > 0:
            scoring_strategy["components"].append("keyword_stuffing_penalty")
        
        # Generate explanation
        explanation = self._generate_explanation(
            overall_score,
            required_coverage,
            preferred_coverage,
            evidence_score,
            semantic_score,
            required_match,
        )
        
        # Convert evidence to dict format
        skill_evidence_dict = {
            skill: [ev.to_dict() for ev in ev_list]
            for skill, ev_list in skill_evidence.items()
        }
        
        return {
            "overall_score": overall_score,
            "required_skill_coverage": required_coverage,
            "preferred_skill_coverage": preferred_coverage,
            "evidence_score": evidence_score,
            "semantic_score": semantic_score,
            "tfidf_score": tfidf_score,
            "skill_match_score": required_coverage,  # Alias for backward compatibility with MatchResult schema
            "matched_skills": required_match["matched"],
            "missing_skills": required_match["missing"],
            "additional_skills": required_match["additional"],
            "skill_evidence": skill_evidence_dict,
            "explanation": explanation,
            "scoring_strategy": scoring_strategy,
            "keyword_stuffing_penalty": keyword_stuffing_penalty,
            "keyword_stuffing_analysis": {
                "is_stuffed": keyword_stuffing_analysis.is_stuffed if keyword_stuffing_analysis else False,
                "stuffing_ratio": keyword_stuffing_analysis.stuffing_ratio if keyword_stuffing_analysis else 0.0,
                "total_skills": keyword_stuffing_analysis.total_skills if keyword_stuffing_analysis else 0,
                "skills_without_evidence": keyword_stuffing_analysis.skills_without_evidence if keyword_stuffing_analysis else 0,
            } if keyword_stuffing_analysis else None,
        }
    
    def _calculate_evidence_score(
        self,
        matched_skills: List[str],
        skill_evidence: Dict[str, List],
        use_demonstration_levels: bool = True,
    ) -> float:
        """
        Calculate evidence strength score with demonstration level weighting.
        
        Args:
            matched_skills: List of matched skills.
            skill_evidence: Evidence dictionary.
            use_demonstration_levels: Whether to apply demonstration level weighting.
            
        Returns:
            Evidence score (0-100).
        """
        if not matched_skills:
            return 0.0
        
        total_strength = 0.0
        
        # Base strength values
        strength_values = {
            EvidenceStrength.STRONG: 100.0,
            EvidenceStrength.MODERATE: 75.0,
            EvidenceStrength.BASIC: 50.0,
            EvidenceStrength.WEAK: 25.0,
        }
        
        # Demonstration level multipliers (only used if enabled)
        demonstration_multipliers = {
            DemonstrationLevel.MEASURABLE: 1.2,  # 20% boost for measurable outcomes
            DemonstrationLevel.IMPLEMENTED: 1.1,  # 10% boost for implementation
            DemonstrationLevel.MENTIONED: 1.0,  # No change for mentioned
            DemonstrationLevel.CLAIMED: 0.8,  # 20% penalty for claimed only
            None: 1.0,  # No demonstration level info
        }
        
        for skill in matched_skills:
            if skill in skill_evidence and skill_evidence[skill]:
                # Get best evidence for this skill
                best_evidence = self.evidence_service.get_best_evidence(skill_evidence[skill])
                if best_evidence:
                    base_strength = strength_values.get(best_evidence.strength, 50.0)
                    if use_demonstration_levels:
                        demo_multiplier = demonstration_multipliers.get(best_evidence.demonstration_level, 1.0)
                        total_strength += base_strength * demo_multiplier
                    else:
                        total_strength += base_strength
                else:
                    total_strength += 50.0  # Default if evidence exists but no best
            else:
                # Skill matched but no evidence found
                total_strength += 25.0
        
        # Normalize to 0-100 range
        evidence_score = total_strength / len(matched_skills)
        return min(evidence_score, 100.0)
    
    def _calculate_semantic_score(
        self,
        job_text: str,
        resume_text: str,
        required_skills: List[str],
        skill_evidence: Dict[str, List],
    ) -> float:
        """
        Calculate semantic similarity score.
        
        Args:
            job_text: Job description text.
            resume_text: Resume text.
            required_skills: Required skills.
            skill_evidence: Skill evidence dictionary.
            
        Returns:
            Semantic score (0-100).
        """
        try:
            # Overall document similarity
            doc_similarity = self.semantic_service.compute_similarity(job_text, resume_text)
            
            if doc_similarity is None:
                return 0.0
            
            # Convert to percentage
            return doc_similarity * 100.0
        except Exception as e:
            logger.error(f"Semantic score calculation failed: {e}")
            return 0.0
    
    def _compute_overall_score(
        self,
        required_coverage: float,
        preferred_coverage: float,
        evidence_score: float,
        semantic_score: Optional[float],
        tfidf_score: float,
    ) -> float:
        """
        Compute overall match score.
        
        Args:
            required_coverage: Required skill coverage percentage.
            preferred_coverage: Preferred skill coverage percentage.
            evidence_score: Evidence strength score.
            semantic_score: Semantic similarity score (0-100).
            tfidf_score: TF-IDF similarity score (0-100).
            
        Returns:
            Overall score (0-100).
        """
        # Normalize scores to 0-1 range
        required_norm = required_coverage / 100.0
        preferred_norm = preferred_coverage / 100.0
        evidence_norm = evidence_score / 100.0
        semantic_norm = (semantic_score / 100.0) if semantic_score is not None else 0.0
        tfidf_norm = tfidf_score / 100.0
        
        # Calculate weighted score
        weighted_score = (
            (self.config.required_skill_weight * required_norm) +
            (self.config.preferred_skill_weight * preferred_norm) +
            (self.config.evidence_weight * evidence_norm) +
            (self.config.semantic_weight * semantic_norm) +
            (self.config.tfidf_weight * tfidf_norm)
        )
        
        # Convert back to percentage
        overall = weighted_score * 100.0
        
        # Clamp to 0-100
        return max(0.0, min(100.0, overall))
    
    def _generate_explanation(
        self,
        overall_score: float,
        required_coverage: float,
        preferred_coverage: float,
        evidence_score: float,
        semantic_score: Optional[float],
        skill_match: Dict[str, Any],
    ) -> str:
        """
        Generate explanation for the match score.
        
        Args:
            overall_score: Overall match score.
            required_coverage: Required skill coverage.
            preferred_coverage: Preferred skill coverage.
            evidence_score: Evidence strength score.
            semantic_score: Semantic similarity score.
            skill_match: Skill match result.
            
        Returns:
            Explanation text.
        """
        parts = []
        
        # Overall assessment
        if overall_score >= 80:
            parts.append("The candidate demonstrates strong alignment with the job requirements.")
        elif overall_score >= 60:
            parts.append("The candidate shows moderate alignment with the job requirements.")
        else:
            parts.append("The candidate has limited alignment with the job requirements.")
        
        # Skill coverage
        parts.append(
            f"They satisfy {len(skill_match['matched'])} of {len(skill_match['matched']) + len(skill_match['missing'])} "
            f"required skills ({required_coverage:.1f}% coverage)."
        )
        
        # Preferred skills
        if preferred_coverage > 0:
            parts.append(
                f"They also cover {preferred_coverage:.1f}% of preferred skills."
            )
        
        # Evidence quality
        if evidence_score >= 75:
            parts.append("Skills are well-demonstrated with strong supporting evidence.")
        elif evidence_score >= 50:
            parts.append("Skills have moderate supporting evidence.")
        else:
            parts.append("Skills have limited supporting evidence.")
        
        # Semantic similarity
        if semantic_score is not None:
            if semantic_score >= 70:
                parts.append("The resume shows strong semantic relevance to the job description.")
            elif semantic_score >= 50:
                parts.append("The resume shows moderate semantic relevance to the job description.")
            else:
                parts.append("The resume has limited semantic relevance to the job description.")
        
        # Missing skills
        if skill_match["missing"]:
            missing_preview = ", ".join(skill_match["missing"][:3])
            if len(skill_match["missing"]) > 3:
                missing_preview += f" (+{len(skill_match['missing']) - 3} more)"
            parts.append(f"Notable gaps include: {missing_preview}.")
        
        return " ".join(parts)
