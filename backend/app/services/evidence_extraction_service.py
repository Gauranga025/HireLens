"""
Resume evidence extraction service.
Extracts supporting evidence for skills from resume sections.
"""
import re
from datetime import date
from typing import Dict, List, Optional, Tuple
from enum import Enum

from app.services.section_detection_service import SectionDetectionService, SectionType
from app.utils.text_processor import normalize_skill_name


class EvidenceType(Enum):
    """Evidence classification types."""
    DEMONSTRATED_IN_EXPERIENCE = "demonstrated_in_experience"
    DEMONSTRATED_IN_PROJECT = "demonstrated_in_project"
    DEMONSTRATED_IN_INTERNSHIP = "demonstrated_in_internship"
    LISTED_IN_SKILLS = "listed_in_skills"
    MENTIONED_IN_EDUCATION = "mentioned_in_education"
    MENTIONED_IN_CERTIFICATION = "mentioned_in_certification"
    INCIDENTAL_MENTION = "incidental_mention"
    UNCATEGORIZED = "uncategorized"


class EvidenceStrength(Enum):
    """Evidence strength indicators."""
    STRONG = "strong"
    MODERATE = "moderate"
    BASIC = "basic"
    WEAK = "weak"


class DemonstrationLevel(Enum):
    """Level of skill demonstration."""
    CLAIMED = "claimed"  # Listed without explanation
    MENTIONED = "mentioned"  # Mentioned in a project/experience
    IMPLEMENTED = "implemented"  # Supported by implementation description
    MEASURABLE = "measurable"  # Supported by measurable outcomes


class SkillEvidence:
    """Represents evidence for a skill."""
    
    def __init__(
        self,
        skill: str,
        section: SectionType,
        evidence_type: EvidenceType,
        snippet: str,
        strength: EvidenceStrength,
        start_offset: int,
        end_offset: int,
        demonstration_level: DemonstrationLevel = None,
        date_info: Dict = None,
        experience_type: Optional[str] = None,
        project_info: Optional[Dict] = None,
        temporal_info: Optional[Dict] = None,
    ):
        self.skill = skill
        self.section = section
        self.evidence_type = evidence_type
        self.snippet = snippet
        self.strength = strength
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.demonstration_level = demonstration_level
        self.date_info = date_info or {}
        # Keep experience/project context available inside date_info for
        # backward compatibility with existing consumers, while also exposing
        # the dedicated attributes.
        if experience_type is not None:
            self.date_info.setdefault("experience_type", experience_type)
        if project_info is not None:
            self.date_info.setdefault("project_info", project_info)
        self.experience_type = experience_type
        self.project_info = project_info
        self.temporal_info = temporal_info
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "skill": self.skill,
            "section": self.section.value,
            "evidence_type": self.evidence_type.value,
            "snippet": self.snippet,
            "strength": self.strength.value,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "demonstration_level": self.demonstration_level.value if self.demonstration_level else None,
            "date_info": self.date_info,
            "experience_type": self.experience_type,
            "project_info": self.project_info,
            "temporal_info": self.temporal_info,
        }


class EvidenceExtractionService:
    """Service for extracting skill evidence from resumes."""
    
    def __init__(self):
        """Initialize the evidence extraction service."""
        self.section_detector = SectionDetectionService()
        
        # Patterns for strong evidence (action verbs + skill)
        self.action_verbs = [
            "developed", "built", "created", "implemented", "designed",
            "engineered", "architected", "programmed", "coded", "wrote",
            "deployed", "maintained", "optimized", "refactored", "integrated",
            "used", "utilized", "leveraged", "applied", "employed",
        ]
    
    def extract_skill_evidence(
        self,
        resume_text: str,
        skills: List[str],
        experience_metadata: List[Dict] = None,
        project_metadata: List[Dict] = None,
    ) -> Dict[str, List[SkillEvidence]]:
        """
        Extract evidence for each skill from resume text.
        
        Args:
            resume_text: Full resume text.
            skills: List of skills to find evidence for.
            experience_metadata: Experience entries with classification (from Phase 8.1).
            project_metadata: Project entries with intelligence (from Phase 8.2).
            
        Returns:
            Dictionary mapping skill names to lists of evidence.
        """
        if not resume_text or not skills:
            return {}
        
        # Detect sections
        sections = self.section_detector.detect_sections(resume_text)
        
        # Extract evidence for each skill
        evidence_map: Dict[str, List[SkillEvidence]] = {}
        
        for skill in skills:
            normalized_skill = normalize_skill_name(skill)
            evidence = self._find_skill_evidence(
                resume_text, normalized_skill, sections, skill,
                experience_metadata, project_metadata
            )
            if evidence:
                evidence_map[skill] = evidence
        
        return evidence_map
    
    def _find_skill_evidence(
        self,
        text: str,
        normalized_skill: str,
        sections: List[Tuple[SectionType, int, int, str]],
        original_skill: str,
        experience_metadata: List[Dict] = None,
        project_metadata: List[Dict] = None,
    ) -> List[SkillEvidence]:
        """
        Find evidence for a specific skill.
        
        Args:
            text: Full resume text.
            normalized_skill: Normalized skill name.
            sections: Detected sections.
            original_skill: Original skill name for display.
            experience_metadata: Experience entries with classification (from Phase 8.1).
            project_metadata: Project entries with intelligence (from Phase 8.2).
            
        Returns:
            List of evidence items for the skill.
        """
        evidence: List[SkillEvidence] = []
        
        # Find all occurrences of the skill
        pattern = re.compile(rf"\b{re.escape(normalized_skill)}\b", re.IGNORECASE)
        
        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            
            # Get the section containing this occurrence
            section = self.section_detector.get_section_for_offset(start, sections)
            
            # Extract surrounding context (sentence or bullet)
            snippet = self._extract_context(text, start, end)
            
            # Determine evidence type based on section
            evidence_type = self._classify_evidence_type(section, snippet)
            
            # Determine evidence strength
            strength = self._classify_evidence_strength(snippet, evidence_type)
            
            # Determine demonstration level
            demonstration_level = self._classify_demonstration_level(snippet, evidence_type)
            
            # Extract date information
            date_info = self._extract_date_info(snippet, section)
            
            # Add experience type context if available
            experience_type = None
            if experience_metadata and section == SectionType.EXPERIENCE:
                experience_type = self._find_experience_type_for_offset(start, experience_metadata, text)
            
            # Add project context if available
            project_info = None
            if project_metadata and section == SectionType.PROJECTS:
                project_info = self._find_project_for_offset(start, project_metadata, text)
            
            evidence_item = SkillEvidence(
                skill=original_skill,
                section=section,
                evidence_type=evidence_type,
                snippet=snippet,
                strength=strength,
                start_offset=start,
                end_offset=end,
                demonstration_level=demonstration_level,
                date_info=date_info,
                experience_type=experience_type,
                project_info=project_info,
                temporal_info=None,  # Can be populated from experience/project metadata in future
            )
            
            evidence.append(evidence_item)
        
        # Deduplicate similar evidence (avoid redundant snippets)
        evidence = self._deduplicate_evidence(evidence)
        
        return evidence
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 150) -> str:
        """
        Extract surrounding context for a skill occurrence.
        
        Args:
            text: Full text.
            start: Start offset of skill.
            end: End offset of skill.
            window: Characters to include on each side.
            
        Returns:
            Context snippet.
        """
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        snippet = text[context_start:context_end].strip()
        
        # Try to extract complete sentence
        sentence_ends = ['.', '!', '?', '\n']
        for end_char in sentence_ends:
            if end_char in snippet:
                idx = snippet.find(end_char, end - context_start)
                if idx != -1:
                    snippet = snippet[:idx + 1].strip()
                    break
        
        # Clean up snippet
        snippet = re.sub(r'\s+', ' ', snippet)
        
        # Add ellipsis if truncated
        if context_start > 0:
            snippet = "..." + snippet
        if context_end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def _classify_evidence_type(self, section: SectionType, snippet: str) -> EvidenceType:
        """
        Classify evidence type based on section and context.
        
        Args:
            section: Section where skill was found.
            snippet: Context snippet.
            
        Returns:
            Evidence type.
        """
        section_mapping = {
            SectionType.EXPERIENCE: EvidenceType.DEMONSTRATED_IN_EXPERIENCE,
            SectionType.PROJECTS: EvidenceType.DEMONSTRATED_IN_PROJECT,
            SectionType.SKILLS: EvidenceType.LISTED_IN_SKILLS,
            SectionType.EDUCATION: EvidenceType.MENTIONED_IN_EDUCATION,
            SectionType.CERTIFICATIONS: EvidenceType.MENTIONED_IN_CERTIFICATION,
        }
        
        # Direct section mapping
        if section in section_mapping:
            # Check for internship in experience section
            if section == SectionType.EXPERIENCE:
                lower_snippet = snippet.lower()
                if "intern" in lower_snippet or "internship" in lower_snippet:
                    return EvidenceType.DEMONSTRATED_IN_INTERNSHIP
            return section_mapping[section]
        
        # Check for action verbs in snippet (indicates demonstration)
        lower_snippet = snippet.lower()
        for verb in self.action_verbs:
            if verb in lower_snippet:
                return EvidenceType.DEMONSTRATED_IN_EXPERIENCE
        
        # Default to incidental
        return EvidenceType.INCIDENTAL_MENTION
    
    def _classify_evidence_strength(self, snippet: str, evidence_type: EvidenceType) -> EvidenceStrength:
        """
        Classify evidence strength based on context.
        
        Args:
            snippet: Context snippet.
            evidence_type: Type of evidence.
            
        Returns:
            Evidence strength.
        """
        # Strong evidence: action verb + concrete implementation
        lower_snippet = snippet.lower()
        
        if evidence_type in [EvidenceType.DEMONSTRATED_IN_EXPERIENCE, EvidenceType.DEMONSTRATED_IN_PROJECT]:
            # Check for action verbs
            for verb in self.action_verbs:
                if verb in lower_snippet:
                    # Check for additional context (e.g., "developed X using Y")
                    if len(snippet) > 50:  # Has some context
                        return EvidenceStrength.STRONG
                    return EvidenceStrength.MODERATE
            return EvidenceStrength.MODERATE
        
        if evidence_type == EvidenceType.DEMONSTRATED_IN_INTERNSHIP:
            # Internship evidence is moderate by default
            return EvidenceStrength.MODERATE
        
        if evidence_type == EvidenceType.LISTED_IN_SKILLS:
            return EvidenceStrength.BASIC
        
        if evidence_type in [EvidenceType.MENTIONED_IN_EDUCATION, EvidenceType.MENTIONED_IN_CERTIFICATION]:
            return EvidenceStrength.MODERATE
        
        return EvidenceStrength.WEAK
    
    def _classify_demonstration_level(self, snippet: str, evidence_type: EvidenceType) -> DemonstrationLevel:
        """
        Classify the level of skill demonstration.
        
        Args:
            snippet: Context snippet.
            evidence_type: Type of evidence.
            
        Returns:
            Demonstration level.
        """
        lower_snippet = snippet.lower()
        
        # Skills section: claimed only
        if evidence_type == EvidenceType.LISTED_IN_SKILLS:
            return DemonstrationLevel.CLAIMED
        
        # Education/certification: mentioned
        if evidence_type in [EvidenceType.MENTIONED_IN_EDUCATION, EvidenceType.MENTIONED_IN_CERTIFICATION]:
            return DemonstrationLevel.MENTIONED
        
        # Check for measurable outcomes (numbers, percentages, metrics)
        measurable_indicators = [
            r'\d+%', r'\d+\s*(users|customers|clients|transactions|requests)',
            r'(increased|decreased|reduced|improved|optimized)\s+by\s+\d+',
            r'(saved|reduced|cut)\s+\d+\s*(hours|days|weeks|months)',
            r'\$\d+', r'\d+\s*(gb|tb|pb|mb)',
        ]
        for pattern in measurable_indicators:
            if re.search(pattern, lower_snippet):
                return DemonstrationLevel.MEASURABLE
        
        # Check for implementation description (action verbs + context)
        if evidence_type in [EvidenceType.DEMONSTRATED_IN_EXPERIENCE, EvidenceType.DEMONSTRATED_IN_PROJECT, EvidenceType.DEMONSTRATED_IN_INTERNSHIP]:
            for verb in self.action_verbs:
                if verb in lower_snippet:
                    # Check for implementation context
                    if len(snippet) > 60:  # Substantial description
                        return DemonstrationLevel.IMPLEMENTED
                    return DemonstrationLevel.MENTIONED
        
        return DemonstrationLevel.MENTIONED
    
    def _extract_date_info(self, snippet: str, section: SectionType) -> Dict:
        """
        Extract date information from evidence snippet.
        
        Args:
            snippet: Context snippet.
            section: Section where evidence was found.
            
        Returns:
            Dictionary with date information (has_dates, date_range, is_recent).
        """
        date_info = {
            "has_dates": False,
            "date_range": None,
            "is_recent": None,
        }
        
        # Date patterns
        date_patterns = [
            r'\d{4}',  # Year
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',  # Month Year
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{4}\s*-\s*(present|current|ongoing)',  # Year - present
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, snippet, re.IGNORECASE):
                date_info["has_dates"] = True
                break
        
        # Check for recent years (last 3 years, including the current year)
        current_year = date.today().year
        recent_years = [str(current_year - i) for i in range(0, 4)]
        for year in recent_years:
            if year in snippet:
                date_info["is_recent"] = True
                break
        
        return date_info
    
    def _deduplicate_evidence(self, evidence: List[SkillEvidence]) -> List[SkillEvidence]:
        """
        Remove duplicate or very similar evidence items.
        
        Args:
            evidence: List of evidence items.
            
        Returns:
            Deduplicated list.
        """
        if not evidence:
            return []
        
        # Sort by strength (strongest first)
        strength_order = {
            EvidenceStrength.STRONG: 0,
            EvidenceStrength.MODERATE: 1,
            EvidenceStrength.BASIC: 2,
            EvidenceStrength.WEAK: 3,
        }
        evidence.sort(key=lambda e: strength_order[e.strength])
        
        # Keep only the strongest evidence from each section
        seen_sections = set()
        deduplicated = []
        
        for ev in evidence:
            if ev.section not in seen_sections:
                deduplicated.append(ev)
                seen_sections.add(ev.section)
        
        return deduplicated
    
    def get_best_evidence(self, evidence: List[SkillEvidence]) -> Optional[SkillEvidence]:
        """
        Get the strongest evidence for a skill.
        
        Args:
            evidence: List of evidence items.
            
        Returns:
            Strongest evidence item, or None if no evidence.
        """
        if not evidence:
            return None
        
        strength_order = {
            EvidenceStrength.STRONG: 0,
            EvidenceStrength.MODERATE: 1,
            EvidenceStrength.BASIC: 2,
            EvidenceStrength.WEAK: 3,
        }
        
        return min(evidence, key=lambda e: strength_order[e.strength])
    
    def _find_experience_type_for_offset(
        self,
        offset: int,
        experience_metadata: List[Dict],
        text: str,
    ) -> Optional[str]:
        """
        Find the experience type for a given text offset.
        
        Args:
            offset: Text offset.
            experience_metadata: Experience entries with classification.
            text: Full resume text.
            
        Returns:
            Experience type if found, None otherwise.
        """
        if not experience_metadata:
            return None
        
        # Find the experience entry that contains this offset
        # This is a simplified approach - in production, you'd need to track offsets during parsing
        for exp in experience_metadata:
            exp_title = exp.get("title", "")
            if exp_title and exp_title.lower() in text.lower():
                # Check if this is likely the right experience entry
                # Return the experience type
                return exp.get("experience_type")
        
        return None
    
    def _find_project_for_offset(
        self,
        offset: int,
        project_metadata: List[Dict],
        text: str,
    ) -> Optional[Dict]:
        """
        Find the project info for a given text offset.
        
        Args:
            offset: Text offset.
            project_metadata: Project entries with intelligence.
            text: Full resume text.
            
        Returns:
            Project info dict if found, None otherwise.
        """
        if not project_metadata:
            return None
        
        # Find the project entry that contains this offset
        for proj in project_metadata:
            proj_title = proj.get("title", "")
            if proj_title and proj_title.lower() in text.lower():
                # Return relevant project info
                return {
                    "title": proj.get("title"),
                    "project_type": proj.get("project_type"),
                    "complexity_level": proj.get("complexity_level"),
                }
        
        return None
