"""
Evidence Mapping Service
Maps evidence to job requirements with structured evaluation.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MatchType(Enum):
    """Type of skill match."""
    EXACT = "exact"
    RELATED = "related"
    DISTINCT = "distinct"


@dataclass
class RequirementEvaluation:
    """Evaluation of a job requirement."""
    skill: str
    requirement_type: str  # REQUIRED or PREFERRED
    matched: bool
    match_type: Optional[MatchType]
    evidence_level: Optional[str]  # CLAIMED, MENTIONED, IMPLEMENTED, MEASURABLE
    source_section: Optional[str]
    evidence: Optional[str]
    source_reference: Optional[str]
    experience_type: Optional[str]
    project_info: Optional[Dict]
    satisfied_by_group: bool = False
    match_credit: Optional[float] = None


class EvidenceMappingService:
    """Service for mapping evidence to job requirements."""
    
    def __init__(self):
        """Initialize the evidence mapping service."""
        pass
    
    def map_evidence_to_requirements(
        self,
        required_skills: List[str],
        preferred_skills: List[str],
        skill_match: Dict[str, Any],
        skill_evidence: Dict[str, List],
        group_evaluation: Optional[List[Dict[str, Any]]] = None,
        requirement_credits: Optional[Dict[str, float]] = None,
    ) -> Dict[str, RequirementEvaluation]:
        """
        Map evidence to job requirements.
        
        Args:
            required_skills: Required skills from job.
            preferred_skills: Preferred skills from job.
            skill_match: Skill match result from SkillService.
            skill_evidence: Evidence dictionary from EvidenceExtractionService.
            group_evaluation: Group-level results from SkillService (Phase 10.2).
        
        Returns:
            Dictionary mapping skill names to RequirementEvaluation.
        """
        evaluations = {}

        # Alternatives inside a satisfied ANY group are not gaps even when the
        # candidate did not match them individually. Track them so the summary
        # and gap generation respect ANY-group semantics.
        satisfied_group_alternatives = set()
        for group in group_evaluation or []:
            if group.get("match_mode") == "ANY" and group.get("is_satisfied"):
                satisfied_group_alternatives.update(group.get("required_skills", []))
        
        # Process required skills
        for skill in required_skills:
            evaluation = self._evaluate_requirement(
                skill,
                "REQUIRED",
                skill_match,
                skill_evidence,
                satisfied_group_alternatives,
                requirement_credits,
            )
            evaluations[skill] = evaluation
        
        # Process preferred skills
        for skill in preferred_skills:
            evaluation = self._evaluate_requirement(
                skill,
                "PREFERRED",
                skill_match,
                skill_evidence,
                requirement_credits=requirement_credits,
            )
            evaluations[skill] = evaluation
        
        return evaluations
    
    def _evaluate_requirement(
        self,
        skill: str,
        requirement_type: str,
        skill_match: Dict[str, Any],
        skill_evidence: Dict[str, List],
        satisfied_group_alternatives: Optional[set] = None,
        requirement_credits: Optional[Dict[str, float]] = None,
    ) -> RequirementEvaluation:
        """
        Evaluate a single requirement.
        
        Args:
            skill: Skill to evaluate.
            requirement_type: REQUIRED or PREFERRED.
            skill_match: Skill match result.
            skill_evidence: Evidence dictionary.
            satisfied_group_alternatives: Skills covered by a satisfied ANY group.
        
        Returns:
            RequirementEvaluation.
        """
        # Check if skill is matched
        matched = skill in skill_match.get("matched", [])
        satisfied_by_group = (
            not matched
            and satisfied_group_alternatives is not None
            and skill in satisfied_group_alternatives
        )
        
        # Determine match type from actual credit when available.
        match_type = None
        match_credit: Optional[float] = None
        if requirement_credits is not None and skill in requirement_credits:
            match_credit = float(requirement_credits[skill])
            if match_credit >= 1.0:
                match_type = MatchType.EXACT
            elif match_credit > 0.0:
                match_type = MatchType.RELATED
            else:
                match_type = MatchType.DISTINCT
        elif matched:
            match_type = MatchType.EXACT
        elif skill in skill_match.get("additional", []):
            match_type = MatchType.RELATED
        elif skill in skill_match.get("missing", []):
            match_type = MatchType.DISTINCT
        
        # Get evidence for this skill
        evidence_list = skill_evidence.get(skill, [])
        
        # Determine evidence level
        evidence_level = None
        source_section = None
        evidence = None
        source_reference = None
        experience_type = None
        project_info = None
        
        if evidence_list:
            # Get best evidence
            best_evidence = evidence_list[0]  # First is usually strongest after deduplication
            level = best_evidence.demonstration_level
            if level is not None:
                # DemonstrationLevel values are lowercase; the mapping
                # comparisons below are uppercase constants.
                evidence_level = (
                    level.value if hasattr(level, "value") else str(level)
                ).upper()
            source_section = best_evidence.section.value if best_evidence.section else None
            evidence = best_evidence.snippet
            source_reference = f"{source_section}[{best_evidence.start_offset}]"
            
            # Extract experience/project context. Prefer dedicated evidence
            # attributes, then fall back to date_info for older callers.
            experience_type = getattr(best_evidence, "experience_type", None)
            if experience_type is None and best_evidence.date_info:
                experience_type = best_evidence.date_info.get("experience_type")
            
            project_info = getattr(best_evidence, "project_info", None)
            if project_info is None and best_evidence.date_info:
                project_info = best_evidence.date_info.get("project_info")
        
        return RequirementEvaluation(
            skill=skill,
            requirement_type=requirement_type,
            matched=matched,
            match_type=match_type,
            evidence_level=evidence_level,
            source_section=source_section,
            evidence=evidence,
            source_reference=source_reference,
            experience_type=experience_type,
            project_info=project_info,
            satisfied_by_group=satisfied_by_group,
            match_credit=match_credit,
        )
    
    def generate_evidence_summary(
        self,
        evaluations: Dict[str, RequirementEvaluation],
    ) -> Dict[str, Any]:
        """
        Generate evidence summary for API response.
        
        Args:
            evaluations: Requirement evaluations.
            
        Returns:
            Evidence summary dictionary.
        """
        demonstrated_skills = []
        mentioned_skills = []
        unsupported_required_skills = []
        unsupported_preferred_skills = []
        
        for skill, eval in evaluations.items():
            if eval.matched:
                if eval.evidence_level in ["IMPLEMENTED", "MEASURABLE"]:
                    demonstrated_skills.append(skill)
                elif eval.evidence_level == "MENTIONED":
                    mentioned_skills.append(skill)
                elif eval.evidence_level == "CLAIMED":
                    mentioned_skills.append(skill)
            elif eval.satisfied_by_group:
                # Covered by a satisfied ANY group; not an unsupported gap.
                continue
            else:
                if eval.requirement_type == "REQUIRED":
                    unsupported_required_skills.append(skill)
                else:
                    unsupported_preferred_skills.append(skill)
        
        return {
            "demonstrated_skills": demonstrated_skills,
            "mentioned_skills": mentioned_skills,
            "unsupported_required_skills": unsupported_required_skills,
            "unsupported_preferred_skills": unsupported_preferred_skills,
        }
    
    def generate_strengths_and_gaps(
        self,
        evaluations: Dict[str, RequirementEvaluation],
    ) -> Dict[str, List[str]]:
        """
        Generate strengths and gaps from evaluations.
        
        Args:
            evaluations: Requirement evaluations.
            
        Returns:
            Dictionary with strengths and gaps lists.
        """
        strengths = []
        gaps = []
        
        for skill, eval in evaluations.items():
            if eval.matched and eval.evidence_level in ["IMPLEMENTED", "MEASURABLE"]:
                # Generate strength explanation
                if eval.experience_type:
                    strengths.append(
                        f"{skill} implementation demonstrated in {eval.experience_type.lower()} experience"
                    )
                elif eval.project_info:
                    project_type = eval.project_info.get("project_type", "project")
                    strengths.append(
                        f"{skill} implementation demonstrated in {project_type.replace('_', ' ')}"
                    )
                else:
                    strengths.append(f"{skill} implementation demonstrated")
            elif eval.matched and eval.evidence_level == "MENTIONED":
                strengths.append(f"{skill} mentioned in resume")
            elif eval.satisfied_by_group:
                continue
            elif not eval.matched and eval.requirement_type == "REQUIRED":
                gaps.append(f"No supporting {skill} evidence found in the submitted resume")
            elif eval.matched and eval.evidence_level == "CLAIMED":
                gaps.append(f"{skill} claimed but implementation evidence not identified")
        
        return {
            "strengths": strengths,
            "gaps": gaps,
        }
