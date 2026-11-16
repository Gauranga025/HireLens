"""
Keyword Stuffing Detection Service
Detects excessive skill listing without demonstrated experience.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class StuffingAnalysis:
    """Result of keyword stuffing analysis."""
    is_stuffed: bool
    stuffing_ratio: float  # 0.0 to 1.0
    total_skills: int
    skills_without_evidence: int
    penalty: float  # 0.0 to 1.0


class KeywordStuffingDetector:
    """
    Detects keyword stuffing in resumes.
    
    Keyword stuffing is defined as listing many skills without
    demonstrated experience (evidence in experience/projects sections).
    
    When education_aware is enabled, skills demonstrated through education,
    coursework, academic projects, and internships are also considered valid evidence.
    """
    
    def __init__(self, threshold: float = 0.7, education_aware: bool = False):
        """
        Initialize the detector.
        
        Args:
            threshold: Ratio threshold for considering stuffing (default 0.7).
                       If 70% or more of skills have no evidence, it's considered stuffing.
            education_aware: Whether to consider education evidence as valid (default False).
                           When enabled, skills in education/certifications are not counted
                           as unsupported. This helps avoid penalizing fresh graduates.
        """
        self.threshold = threshold
        self.education_aware = education_aware
    
    def analyze(
        self,
        skills: List[str],
        skill_evidence: Dict[str, List],
    ) -> StuffingAnalysis:
        """
        Analyze a resume for keyword stuffing.
        
        Args:
            skills: List of extracted skills.
            skill_evidence: Dictionary mapping skills to evidence lists.
            
        Returns:
            StuffingAnalysis with detection results.
        """
        if not skills:
            return StuffingAnalysis(
                is_stuffed=False,
                stuffing_ratio=0.0,
                total_skills=0,
                skills_without_evidence=0,
                penalty=0.0,
            )
        
        total_skills = len(skills)
        skills_without_evidence = 0
        
        for skill in skills:
            evidence = skill_evidence.get(skill, [])
            
            # Check if skill has any evidence
            has_demonstrated_evidence = False
            for ev in evidence:
                ev_type = ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else str(ev.evidence_type)
                
                # Always count experience, project, and internship as valid evidence
                if ev_type in [
                    "demonstrated_in_experience",
                    "demonstrated_in_project",
                    "demonstrated_in_internship",
                ]:
                    has_demonstrated_evidence = True
                    break
                
                # If education_aware is enabled, also count education and certifications
                if self.education_aware and ev_type in [
                    "mentioned_in_education",
                    "mentioned_in_certification",
                ]:
                    has_demonstrated_evidence = True
                    break
            
            if not has_demonstrated_evidence:
                skills_without_evidence += 1
        
        stuffing_ratio = skills_without_evidence / total_skills if total_skills > 0 else 0.0
        is_stuffed = stuffing_ratio >= self.threshold
        
        # Calculate penalty (linear ramp from threshold to 1.0)
        if is_stuffed:
            excess = stuffing_ratio - self.threshold
            max_excess = 1.0 - self.threshold
            penalty = min(excess / max_excess, 1.0) if max_excess > 0 else 1.0
        else:
            penalty = 0.0
        
        return StuffingAnalysis(
            is_stuffed=is_stuffed,
            stuffing_ratio=stuffing_ratio,
            total_skills=total_skills,
            skills_without_evidence=skills_without_evidence,
            penalty=penalty,
        )
    
    def get_penalty_threshold(self) -> float:
        """Get the current stuffing threshold."""
        return self.threshold
    
    def set_penalty_threshold(self, threshold: float):
        """
        Set the stuffing threshold.
        
        Args:
            threshold: New threshold value (0.0 to 1.0).
        """
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")
