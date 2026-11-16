"""
Resume section detection service.
Identifies and classifies resume sections for evidence extraction.
"""
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SectionType(Enum):
    """Resume section types."""
    PERSONAL_INFO = "personal_info"
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    ACHIEVEMENTS = "achievements"
    PUBLICATIONS = "publications"
    AWARDS = "awards"
    EXTRACURRICULAR = "extracurricular"
    UNCATEGORIZED = "uncategorized"


class SectionDetectionService:
    """Service for detecting resume sections."""
    
    # Section heading patterns - normalized to lowercase for matching
    SECTION_PATTERNS: Dict[SectionType, List[str]] = {
        SectionType.PERSONAL_INFO: [
            "contact information",
            "contact",
            "personal details",
            "personal information",
        ],
        SectionType.SUMMARY: [
            "summary",
            "professional summary",
            "career objective",
            "objective",
            "profile",
            "about me",
            "personal profile",
            "executive summary",
            "overview",
            "professional profile",
        ],
        SectionType.SKILLS: [
            "skills",
            "technical skills",
            "core competencies",
            "technologies",
            "key skills",
            "skills & abilities",
            "tools & technologies",
            "areas of expertise",
            "technical expertise",
            "technical stack",
            "programming languages",
            "technologies used",
        ],
        SectionType.EXPERIENCE: [
            "work experience",
            "professional experience",
            "experience",
            "employment history",
            "work history",
            "employment",
            "relevant experience",
            "career history",
            "internships",
            "professional background",
            "working experience",
            "work experience & projects",
        ],
        SectionType.PROJECTS: [
            "projects",
            "academic projects",
            "personal projects",
            "key projects",
            "selected projects",
            "technical projects",
            "side projects",
            "notable projects",
            "project work",
            "project experience",
        ],
        SectionType.EDUCATION: [
            "education",
            "academic background",
            "academics",
            "educational qualification",
            "educational qualifications",
            "academic qualifications",
            "academic history",
            "education and credentials",
            "education & credentials",
            "degrees",
            "qualifications",
            "academic education",
        ],
        SectionType.CERTIFICATIONS: [
            "certifications",
            "certificates",
            "licenses & certifications",
            "certifications & licenses",
            "professional certifications",
            "courses & certifications",
            "licenses and certifications",
            "accreditations",
            "certifications and courses",
            "certificates & courses",
            "training",
            "courses",
        ],
        SectionType.ACHIEVEMENTS: [
            "achievements",
            "accomplishments",
            "key achievements",
        ],
        SectionType.PUBLICATIONS: [
            "publications",
            "research",
            "papers",
        ],
        SectionType.AWARDS: [
            "awards",
            "honors",
            "recognition",
        ],
        SectionType.EXTRACURRICULAR: [
            "extracurricular activities",
            "extracurricular",
            "activities",
            "volunteer work",
            "volunteering",
        ],
    }
    
    def __init__(self):
        """Initialize the section detection service."""
        # Compile regex patterns for each section type
        self._compiled_patterns: Dict[SectionType, List[re.Pattern]] = {}
        for section_type, patterns in self.SECTION_PATTERNS.items():
            compiled = []
            for pattern in patterns:
                # Match case-insensitive, with optional colons, and allow content on same line
                regex = rf"^{re.escape(pattern)}\s*:?\s*"
                compiled.append(re.compile(regex, re.IGNORECASE))
            self._compiled_patterns[section_type] = compiled
    
    def detect_sections(self, text: str) -> List[Tuple[SectionType, int, int, str]]:
        """
        Detect sections in resume text.
        
        Args:
            text: Full resume text.
            
        Returns:
            List of tuples: (section_type, start_offset, end_offset, section_text)
        """
        if not text:
            return []
        
        lines = text.split('\n')
        sections: List[Tuple[SectionType, int, int, str]] = []
        
        current_section = SectionType.UNCATEGORIZED
        current_start = 0
        current_lines: List[str] = []
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line:
                current_lines.append(line)
                continue
            
            # Check if this line is a section heading
            detected_section = self._detect_section_heading(stripped_line)
            
            if detected_section:
                # Save previous section if it has content
                if current_lines and any(l.strip() for l in current_lines):
                    section_text = '\n'.join(current_lines)
                    start_offset = current_start
                    end_offset = current_start + len(section_text)
                    sections.append((current_section, start_offset, end_offset, section_text))
                
                # Start new section
                current_section = detected_section
                current_start = sum(len(l) + 1 for l in lines[:i])  # +1 for newline
                current_lines = [line]  # Include the heading
            else:
                current_lines.append(line)
        
        # Don't forget the last section
        if current_lines and any(l.strip() for l in current_lines):
            section_text = '\n'.join(current_lines)
            start_offset = current_start
            end_offset = current_start + len(section_text)
            sections.append((current_section, start_offset, end_offset, section_text))
        
        return sections
    
    def _detect_section_heading(self, line: str) -> Optional[SectionType]:
        """
        Detect if a line is a section heading.
        
        Args:
            line: Line of text to check.
            
        Returns:
            Section type if heading detected, None otherwise.
        """
        for section_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.match(line):
                    return section_type
        return None
    
    def get_section_for_offset(self, offset: int, sections: List[Tuple[SectionType, int, int, str]]) -> SectionType:
        """
        Get the section type for a given text offset.
        
        Args:
            offset: Character offset in the text.
            sections: List of detected sections.
            
        Returns:
            Section type containing the offset.
        """
        for section_type, start, end, _ in sections:
            if start <= offset < end:
                return section_type
        return SectionType.UNCATEGORIZED
    
    def extract_section_text(self, text: str, section_type: SectionType) -> str:
        """
        Extract all text belonging to a specific section type.
        
        Args:
            text: Full resume text.
            section_type: Section type to extract.
            
        Returns:
            Concatenated text from all sections of the given type.
        """
        sections = self.detect_sections(text)
        section_texts = [s[3] for s in sections if s[0] == section_type]
        return '\n\n'.join(section_texts)
