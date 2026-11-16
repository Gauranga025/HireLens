"""
Experience Classification Service
Classifies experience entries by type (full-time, internship, research, etc.)
and provides relevance scoring based on job requirements.
"""
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


class ExperienceType(Enum):
    """Experience type categories."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERNSHIP = "internship"
    RESEARCH = "research"
    ACADEMIC_PROJECT = "academic_project"
    PERSONAL_PROJECT = "personal_project"
    FREELANCE = "freelance"
    CONTRACT = "contract"
    UNKNOWN = "unknown"


@dataclass
class ExperienceEntry:
    """Represents a classified experience entry."""
    title: str
    company: str
    duration: str
    experience_type: ExperienceType
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False


class ExperienceClassificationService:
    """Service for classifying experience entries."""
    
    # Patterns for detecting experience types
    INTERNSHIP_PATTERNS = [
        r"\bintern\b",
        r"\binternship\b",
        r"\binternsh\b",
    ]
    
    RESEARCH_PATTERNS = [
        r"\bresearch\s+(assistant|associate|fellow|scientist)\b",
        r"\bgraduate\s+(research\s+)?assistant\b",
        r"\bpostdoctoral\b",
        r"\bphd\s+(candidate|student)\b",
    ]
    
    PART_TIME_PATTERNS = [
        r"\bpart\s*time\b",
        r"\bpart-time\b",
        r"\bcontractor\b",
    ]
    
    FREELANCE_PATTERNS = [
        r"\bfreelance\b",
        r"\bfreelancer\b",
        r"\bself-employed\b",
        r"\bconsultant\b",
        r"\bcontract\b",
    ]
    
    ACADEMIC_PROJECT_PATTERNS = [
        r"\bthesis\b",
        r"\bdissertation\b",
        r"\bcapstone\b",
        r"\bsenior\s+project\b",
        r"\bfinal\s+year\s+project\b",
        r"\bacademic\s+project\b",
    ]
    
    PERSONAL_PROJECT_PATTERNS = [
        r"\bpersonal\s+project\b",
        r"\bside\s+project\b",
        r"\bhobby\s+project\b",
        r"\bopen\s+source\s+contributor\b",
    ]
    
    def __init__(self):
        """Initialize the experience classification service."""
        # Compile regex patterns
        self._internship_regex = re.compile(
            "|".join(self.INTERNSHIP_PATTERNS), re.IGNORECASE
        )
        self._research_regex = re.compile(
            "|".join(self.RESEARCH_PATTERNS), re.IGNORECASE
        )
        self._part_time_regex = re.compile(
            "|".join(self.PART_TIME_PATTERNS), re.IGNORECASE
        )
        self._freelance_regex = re.compile(
            "|".join(self.FREELANCE_PATTERNS), re.IGNORECASE
        )
        self._academic_project_regex = re.compile(
            "|".join(self.ACADEMIC_PROJECT_PATTERNS), re.IGNORECASE
        )
        self._personal_project_regex = re.compile(
            "|".join(self.PERSONAL_PROJECT_PATTERNS), re.IGNORECASE
        )
    
    def classify_experience(
        self,
        title: str,
        company: str,
        duration: str,
        description: str = "",
        section: str = "experience",
    ) -> ExperienceEntry:
        """
        Classify an experience entry by type.
        
        Args:
            title: Job title or project name.
            company: Company name or organization.
            duration: Duration string (e.g., "2020-2022", "6 months").
            description: Description of the experience.
            section: Section where this entry appears (experience, projects, etc.).
            
        Returns:
            ExperienceEntry with classified type.
        """
        # Normalize inputs
        title_lower = title.lower() if title else ""
        company_lower = company.lower() if company else ""
        description_lower = description.lower() if description else ""
        combined_text = f"{title_lower} {company_lower} {description_lower}"
        
        # Determine experience type based on section and patterns
        if section == "projects":
            # Projects section: classify as academic or personal project
            if self._academic_project_regex.search(combined_text):
                experience_type = ExperienceType.ACADEMIC_PROJECT
            elif self._personal_project_regex.search(combined_text):
                experience_type = ExperienceType.PERSONAL_PROJECT
            else:
                experience_type = ExperienceType.ACADEMIC_PROJECT  # Default for projects
        else:
            # Experience section: classify by job title and company
            if self._internship_regex.search(combined_text):
                experience_type = ExperienceType.INTERNSHIP
            elif self._research_regex.search(combined_text):
                experience_type = ExperienceType.RESEARCH
            elif self._freelance_regex.search(combined_text):
                experience_type = ExperienceType.FREELANCE
            elif self._part_time_regex.search(combined_text):
                experience_type = ExperienceType.PART_TIME
            else:
                # Default to full-time for professional experience
                experience_type = ExperienceType.FULL_TIME
        
        # Parse dates
        start_date, end_date, is_current = self._parse_dates(duration)
        
        return ExperienceEntry(
            title=title,
            company=company,
            duration=duration,
            experience_type=experience_type,
            description=description,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
        )
    
    def _parse_dates(self, duration: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Parse dates from duration string.
        
        Args:
            duration: Duration string (e.g., "2020-2022", "Jan 2020 - Present").
            
        Returns:
            Tuple of (start_date, end_date, is_current).
        """
        if not duration:
            return None, None, False
        
        duration_lower = duration.lower()
        
        # Check for "present" or "current"
        is_current = "present" in duration_lower or "current" in duration_lower
        
        # Try to extract years
        year_pattern = re.compile(r"\b(19|20)\d{2}\b")
        years = year_pattern.findall(duration)
        
        if len(years) >= 2:
            start_date = years[0]
            end_date = years[1] if not is_current else None
        elif len(years) == 1:
            start_date = years[0]
            end_date = None if is_current else years[0]
        else:
            start_date = None
            end_date = None
        
        return start_date, end_date, is_current
    
    def get_experience_weight(self, experience_type: ExperienceType) -> float:
        """
        Get the weight for an experience type.
        
        Args:
            experience_type: The experience type.
            
        Returns:
            Weight multiplier (1.0 = full credit).
        """
        weights = {
            ExperienceType.FULL_TIME: 1.0,
            ExperienceType.PART_TIME: 0.8,
            ExperienceType.INTERNSHIP: 0.6,
            ExperienceType.RESEARCH: 0.8,
            ExperienceType.ACADEMIC_PROJECT: 0.5,
            ExperienceType.PERSONAL_PROJECT: 0.4,
            ExperienceType.FREELANCE: 0.7,
            ExperienceType.CONTRACT: 0.9,
            ExperienceType.UNKNOWN: 0.5,
        }
        return weights.get(experience_type, 0.5)
