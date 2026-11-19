"""
Scoring service for evidence-aware candidate matching.
Combines skill coverage, semantic relevance, and evidence strength.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from app.services.skill_service import (
    collect_structured_preferred_skills,
    match_skills_to_requirements,
)
from app.services.evidence_extraction_service import EvidenceExtractionService, EvidenceStrength, DemonstrationLevel
from app.services.semantic_matching_service import SemanticMatchingService, SemanticError
from app.services.semantic_input_service import build_semantic_inputs
from app.services.requirement_semantic_service import RequirementSemanticService
from app.services.keyword_stuffing_detector import KeywordStuffingDetector
from app.services.evidence_mapping_service import EvidenceMappingService
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
        self.evidence_mapping_service = EvidenceMappingService()
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
        experience_metadata: List[Dict] = None,
        project_metadata: List[Dict] = None,
        structured_requirements: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Compute evidence-aware match score.

        Args:
            resume_text: Full resume text.
            job_text: Full job description text.
            resume_skills: Skills extracted from resume.
            required_skills: Required skills from job (backward compatibility).
            preferred_skills: Preferred skills from job (backward compatibility).
            use_semantic: Whether to use semantic matching.
            experience_metadata: Experience entries with classification (from Phase 8.1).
            project_metadata: Project entries with intelligence (from Phase 8.2).
            structured_requirements: Structured requirements from Phase 10.1/10.2.

        Returns:
            Dictionary with match results and scoring metadata.
        """
        # Extract skill evidence with experience/project context
        skill_evidence = self.evidence_service.extract_skill_evidence(
            resume_text,
            resume_skills,
            experience_metadata,
            project_metadata,
        )

        # Structured units are authoritative when present. Flat lists are used
        # only as a legacy fallback and are never unioned with structured units.
        if structured_requirements:
            from app.services.skill_service import match_structured_requirements
            required_match = match_structured_requirements(
                resume_skills,
                structured_requirements,
                use_hierarchy=self.config.use_skill_hierarchy,
                related_skill_credit_threshold=self.config.related_skill_credit_threshold,
            )
            effective_preferred_skills = collect_structured_preferred_skills(
                structured_requirements
            )
        else:
            required_match = match_skills_to_requirements(
                resume_skills,
                required_skills,
                use_hierarchy=self.config.use_skill_hierarchy,
                related_skill_credit_threshold=self.config.related_skill_credit_threshold,
            )
            effective_preferred_skills = []

        preferred_scoring_skills = effective_preferred_skills or preferred_skills
        preferred_match = match_skills_to_requirements(
            resume_skills,
            preferred_scoring_skills,
            use_hierarchy=self.config.use_skill_hierarchy,
            related_skill_credit_threshold=self.config.related_skill_credit_threshold,
        )

        # Calculate skill coverage scores from actual hierarchy credit
        required_coverage = required_match["match_percentage"]
        preferred_coverage = preferred_match["match_percentage"]

        # Evidence scoring accepts only required scoring units. Preferred skills
        # and duplicate group alternatives are excluded by construction.
        evidence_score = self._calculate_evidence_score(
            required_match.get("required_units", []),
            skill_evidence,
            use_demonstration_levels=self.config.use_demonstration_levels,
        )

        # Resolve one explicit semantic path for this evaluation.
        semantic_score: Optional[float] = None
        semantic_error: Optional[Dict[str, str]] = None
        semantic_details: Optional[Dict[str, Any]] = None
        semantic_model_available: Optional[bool] = None
        semantic_empty_text = (
            not (resume_text or "").strip() or not (job_text or "").strip()
        )

        if not use_semantic:
            semantic_status = "disabled"
        elif semantic_empty_text:
            semantic_status = "empty_text"
            semantic_model_available = self.semantic_service.is_available()
        else:
            semantic_model_available = self.semantic_service.is_available()
            if not semantic_model_available:
                semantic_status = "model_unavailable"
                error_info = self.semantic_service.get_error_info()
                if error_info:
                    semantic_error = error_info
            else:
                (
                    semantic_score,
                    semantic_error,
                    semantic_details,
                ) = self._calculate_semantic_score(
                    job_text,
                    resume_text,
                    structured_requirements,
                )
                semantic_status = "used" if semantic_score is not None else "inference_failed"

        # Calculate TF-IDF similarity (optional)
        tfidf_score = 0.0
        if self.config.tfidf_weight > 0:
            tfidf_score = tfidf_similarity(
                preprocess_for_tfidf(resume_text),
                preprocess_for_tfidf(job_text),
            )

        configured_weights = self._configured_weights()
        effective_weights = self._effective_weights(semantic_score is not None)
        overall_score = self._compute_overall_score(
            required_coverage,
            preferred_coverage,
            evidence_score,
            semantic_score,
            tfidf_score,
            effective_weights,
        )

        fallback_used = semantic_status in {
            "model_unavailable",
            "inference_failed",
            "empty_text",
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
            "weights": effective_weights,
            "configured_weights": configured_weights,
            "semantic_available": semantic_score is not None,
            "semantic_status": semantic_status,
            "semantic_model_available": semantic_model_available,
            "semantic_error": semantic_error,
            "semantic_details": semantic_details,
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
            required_match.get("required_units", []),
            semantic_status,
            effective_weights,
        )

        # Map evidence to requirements using the same canonical units as scoring.
        required_display_skills = self._unit_skill_names(
            required_match.get("required_units", [])
        )
        requirement_credits = {
            **(preferred_match.get("requirement_credits") or {}),
            **(required_match.get("requirement_credits") or {}),
        }
        requirement_evaluations = self.evidence_mapping_service.map_evidence_to_requirements(
            required_display_skills,
            preferred_scoring_skills,
            required_match,
            skill_evidence,
            required_match.get("group_evaluation", []),
            requirement_credits,
        )

        # Generate evidence summary
        evidence_summary = self.evidence_mapping_service.generate_evidence_summary(
            requirement_evaluations,
        )

        # Generate strengths and gaps
        strengths_gaps = self.evidence_mapping_service.generate_strengths_and_gaps(
            requirement_evaluations,
        )

        # Convert evidence to dict format
        skill_evidence_dict = {
            skill: [ev.to_dict() for ev in ev_list]
            for skill, ev_list in skill_evidence.items()
        }

        # Convert requirement evaluations to dict format
        requirement_evaluations_dict = {
            skill: {
                "skill": eval.skill,
                "requirement_type": eval.requirement_type,
                "matched": eval.matched,
                "match_type": eval.match_type.value if eval.match_type else None,
                "match_credit": eval.match_credit,
                "evidence_level": eval.evidence_level,
                "source_section": eval.source_section,
                "evidence": eval.evidence,
                "source_reference": eval.source_reference,
                "experience_type": eval.experience_type,
                "project_info": eval.project_info,
                "satisfied_by_group": eval.satisfied_by_group,
            }
            for skill, eval in requirement_evaluations.items()
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
            "evidence_summary": evidence_summary,
            "requirement_evaluations": requirement_evaluations_dict,
            "strengths": strengths_gaps["strengths"],
            "gaps": strengths_gaps["gaps"],
            "group_evaluation": required_match.get("group_evaluation", []),  # Phase 10.2: Group evaluation details
        }

    def _configured_weights(self) -> Dict[str, float]:
        return {
            "required_skills": self.config.required_skill_weight,
            "preferred_skills": self.config.preferred_skill_weight,
            "semantic": self.config.semantic_weight,
            "evidence": self.config.evidence_weight,
            "tfidf": self.config.tfidf_weight,
        }

    def _effective_weights(self, semantic_used: bool) -> Dict[str, float]:
        """Return configured or renormalized weights for the active path."""
        configured = self._configured_weights()
        if semantic_used:
            return dict(configured)

        renormalizable = {
            "required_skills": self.config.required_skill_weight,
            "preferred_skills": self.config.preferred_skill_weight,
            "evidence": self.config.evidence_weight,
            "tfidf": self.config.tfidf_weight,
        }
        denominator = sum(renormalizable.values())
        if denominator <= 0:
            return dict(configured)

        return {
            "required_skills": configured["required_skills"] / denominator,
            "preferred_skills": configured["preferred_skills"] / denominator,
            "semantic": 0.0,
            "evidence": configured["evidence"] / denominator,
            "tfidf": configured["tfidf"] / denominator,
        }

    def _unit_skill_names(self, units: List[Dict[str, Any]]) -> List[str]:
        names: List[str] = []
        seen = set()
        for unit in units:
            for skill in unit.get("skills", []):
                key = skill.lower()
                if key not in seen:
                    seen.add(key)
                    names.append(skill)
        return names

    def _calculate_evidence_score(
        self,
        required_units: List[Dict[str, Any]],
        skill_evidence: Dict[str, List],
        use_demonstration_levels: bool = True,
    ) -> float:
        """
        Calculate evidence strength over eligible required scoring units only.

        Individual, ANY, and ALL units each contribute at most one bounded
        value. Actual hierarchy credit scales every contribution.
        """
        if not required_units:
            return 0.0

        strength_values = {
            EvidenceStrength.STRONG: 100.0,
            EvidenceStrength.MODERATE: 75.0,
            EvidenceStrength.BASIC: 50.0,
            EvidenceStrength.WEAK: 25.0,
        }
        demonstration_multipliers = {
            DemonstrationLevel.MEASURABLE: 1.2,
            DemonstrationLevel.IMPLEMENTED: 1.1,
            DemonstrationLevel.MENTIONED: 1.0,
            DemonstrationLevel.CLAIMED: 0.8,
            None: 1.0,
        }

        def raw_strength(skill: Optional[str]) -> float:
            if not skill:
                return 25.0
            evidence_list = skill_evidence.get(skill) or []
            if not evidence_list:
                return 25.0
            best_evidence = self.evidence_service.get_best_evidence(evidence_list)
            if not best_evidence:
                return 50.0
            base_strength = strength_values.get(best_evidence.strength, 50.0)
            if use_demonstration_levels:
                multiplier = demonstration_multipliers.get(
                    best_evidence.demonstration_level, 1.0
                )
                return base_strength * multiplier
            return base_strength

        total_strength = 0.0
        denominator = 0

        for unit in required_units:
            kind = unit.get("kind")
            skills = unit.get("skills", [])
            member_credits = unit.get("member_credits", [])
            member_evidence_skills = unit.get("member_evidence_skills", [])

            if kind == "individual":
                credit = float(unit.get("credit", 0.0))
                if credit <= 0.0:
                    continue
                evidence_skill = unit.get("evidence_skill") or skills[0]
                total_strength += credit * raw_strength(evidence_skill)
                denominator += 1
                continue

            if kind == "any":
                group_credit = max(member_credits, default=0.0)
                if group_credit <= 0.0:
                    continue
                eligible = [
                    (index, credit)
                    for index, credit in enumerate(member_credits)
                    if credit > 0.0
                ]
                representative_index, _ = max(
                    eligible,
                    key=lambda item: (
                        item[1],
                        raw_strength(
                            member_evidence_skills[item[0]]
                            if item[0] < len(member_evidence_skills)
                            else skills[item[0]]
                        ),
                        -item[0],
                    ),
                )
                evidence_skill = (
                    member_evidence_skills[representative_index]
                    if representative_index < len(member_evidence_skills)
                    else skills[representative_index]
                )
                total_strength += group_credit * raw_strength(evidence_skill)
                denominator += 1
                continue

            if kind == "all" and skills:
                if not any(credit > 0.0 for credit in member_credits):
                    continue
                group_sum = 0.0
                for index, credit in enumerate(member_credits):
                    evidence_skill = (
                        member_evidence_skills[index]
                        if index < len(member_evidence_skills)
                        else skills[index]
                    )
                    group_sum += credit * raw_strength(evidence_skill)
                total_strength += group_sum / len(skills)
                denominator += 1

        if denominator == 0:
            return 0.0
        return min(total_strength / denominator, 100.0)

    def _calculate_semantic_score(
        self,
        job_text: str,
        resume_text: str,
        structured_requirements: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[float], Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
        """Calculate the semantic scalar, preserving failure as ``None``.

        The requirement-to-chunk path is used when the injected semantic
        service exposes the tokenizer/matrix API. Older services and test
        doubles retain the legacy document-level path so Phase 11.3
        compatibility is preserved.
        """
        has_requirement_api = all(
            callable(getattr(self.semantic_service, method, None))
            for method in ("get_model_context", "compute_similarity_matrix")
        )

        try:
            if has_requirement_api:
                model_context = self.semantic_service.get_model_context()
                inputs = build_semantic_inputs(
                    job_text,
                    resume_text,
                    structured_requirements,
                    model_context["tokenizer"],
                    model_context["max_seq_length"],
                )
                result = RequirementSemanticService().score(
                    inputs, self.semantic_service
                )
                return float(result.score), None, result.details

            doc_similarity = self.semantic_service.compute_similarity(job_text, resume_text)
            if doc_similarity is None:
                return None, {
                    "error_type": "inference_failure",
                    "message": "Semantic similarity computation returned no score.",
                }, None
            return doc_similarity * 100.0, None, None
        except SemanticError as e:
            logger.error(f"Semantic context computation failed: {e}")
            return None, {
                "error_type": e.error_type.value,
                "message": e.message,
            }, None
        except Exception as e:
            logger.error(f"Semantic score calculation failed: {e}")
            return None, {
                "error_type": "inference_failure",
                "message": str(e),
            }, None

    def _compute_overall_score(
        self,
        required_coverage: float,
        preferred_coverage: float,
        evidence_score: float,
        semantic_score: Optional[float],
        tfidf_score: float,
        weights: Dict[str, float],
    ) -> float:
        """Compute the weighted score using the supplied effective weights."""
        required_norm = required_coverage / 100.0
        preferred_norm = preferred_coverage / 100.0
        evidence_norm = evidence_score / 100.0
        semantic_norm = (semantic_score / 100.0) if semantic_score is not None else 0.0
        tfidf_norm = tfidf_score / 100.0

        weighted_score = (
            weights.get("required_skills", 0.0) * required_norm
            + weights.get("preferred_skills", 0.0) * preferred_norm
            + weights.get("evidence", 0.0) * evidence_norm
            + weights.get("semantic", 0.0) * semantic_norm
            + weights.get("tfidf", 0.0) * tfidf_norm
        )

        overall = weighted_score * 100.0
        return max(0.0, min(100.0, overall))

    def _generate_explanation(
        self,
        overall_score: float,
        required_coverage: float,
        preferred_coverage: float,
        evidence_score: float,
        semantic_score: Optional[float],
        required_units: List[Dict[str, Any]],
        semantic_status: str,
        effective_weights: Dict[str, float],
    ) -> str:
        """Generate explanation consistent with canonical scoring units."""
        parts = []

        if overall_score >= 80:
            parts.append("The candidate demonstrates strong alignment with the job requirements.")
        elif overall_score >= 60:
            parts.append("The candidate shows moderate alignment with the job requirements.")
        else:
            parts.append("The candidate has limited alignment with the job requirements.")

        if required_units:
            fully_matched_units = sum(
                1 for unit in required_units if float(unit.get("credit", 0.0)) >= 1.0
            )
            partially_matched_units = sum(
                1
                for unit in required_units
                if 0.0 < float(unit.get("credit", 0.0)) < 1.0
            )
            parts.append(
                f"They fully matched {fully_matched_units} of {len(required_units)} required requirement units "
                f"and partially matched {partially_matched_units} "
                f"({required_coverage:.1f}% weighted coverage)."
            )
            partially_matched_all_groups = sum(
                1
                for unit in required_units
                if unit.get("match_mode") == "ALL"
                and 0.0 < float(unit.get("credit", 0.0)) < 1.0
            )
            if partially_matched_all_groups:
                parts.append(
                    f"{partially_matched_all_groups} ALL requirement group(s) were partially matched; "
                    "they were not counted as fully matched."
                )
            elif partially_matched_units:
                parts.append(
                    f"{partially_matched_units} required requirement(s) received partial credit from related skills."
                )
        else:
            parts.append("No required requirement units were declared.")

        if preferred_coverage > 0:
            parts.append(
                f"They also cover {preferred_coverage:.1f}% of preferred skills."
            )

        if evidence_score >= 75:
            parts.append("Skills are well-demonstrated with strong supporting evidence.")
        elif evidence_score >= 50:
            parts.append("Skills have moderate supporting evidence.")
        else:
            parts.append("Skills have limited supporting evidence.")

        if semantic_score is not None:
            if semantic_score >= 70:
                parts.append("The resume shows strong semantic relevance to the job description.")
            elif semantic_score >= 50:
                parts.append("The resume shows moderate semantic relevance to the job description.")
            else:
                parts.append("The resume has limited semantic relevance to the job description.")
        else:
            parts.append(
                "Semantic matching was not applied ("
                + semantic_status
                + f"); effective weights were required {effective_weights.get('required_skills', 0.0):.3f}, "
                + f"preferred {effective_weights.get('preferred_skills', 0.0):.3f}, "
                + f"evidence {effective_weights.get('evidence', 0.0):.3f}."
            )

        return " ".join(parts)
