"""
Unit tests for section detection service.
"""
import pytest
from app.services.section_detection_service import SectionDetectionService, SectionType


class TestSectionDetection:
    """Test resume section detection."""
    
    def test_detect_experience_section(self):
        service = SectionDetectionService()
        text = """
        John Doe
        john@example.com
        
        Work Experience
        Senior Developer at ABC Corp
        Developed backend systems.
        
        Skills
        Python, JavaScript
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.EXPERIENCE in section_types
    
    def test_detect_skills_section(self):
        service = SectionDetectionService()
        text = """
        Skills
        Python, JavaScript, SQL
        
        Experience
        Developer at ABC
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.SKILLS in section_types
    
    def test_detect_projects_section(self):
        service = SectionDetectionService()
        text = """
        Projects
        Built a web application.
        
        Education
        BS in CS
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.PROJECTS in section_types
    
    def test_detect_education_section(self):
        service = SectionDetectionService()
        text = """
        Education
        Bachelor of Science in Computer Science
        University of XYZ
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.EDUCATION in section_types
    
    def test_case_insensitive_detection(self):
        service = SectionDetectionService()
        text = """
        WORK EXPERIENCE
        Developer at ABC
        
        work experience
        Another role
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.EXPERIENCE in section_types
    
    def test_heading_with_colon(self):
        service = SectionDetectionService()
        text = """
        Skills:
        Python, Java
        
        Experience:
        Developer
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.SKILLS in section_types
        assert SectionType.EXPERIENCE in section_types
    
    def test_heading_with_content_on_same_line(self):
        service = SectionDetectionService()
        text = """
        Skills: Python, JavaScript, SQL
        Experience: Developer at ABC
        """
        sections = service.detect_sections(text)
        section_types = [s[0] for s in sections]
        assert SectionType.SKILLS in section_types
    
    def test_empty_text(self):
        service = SectionDetectionService()
        sections = service.detect_sections("")
        assert sections == []
    
    def test_no_sections(self):
        service = SectionDetectionService()
        text = "Some random text without section headings."
        sections = service.detect_sections(text)
        # Should have at least one uncategorized section
        assert len(sections) > 0
        assert sections[0][0] == SectionType.UNCATEGORIZED
    
    def test_get_section_for_offset(self):
        service = SectionDetectionService()
        text = """
        Skills
        Python, JavaScript
        
        Experience
        Developer at ABC
        """
        sections = service.detect_sections(text)
        
        # Find offset in skills section
        skills_section = next(s for s in sections if s[0] == SectionType.SKILLS)
        offset = skills_section[1] + 10  # Middle of skills section
        
        section = service.get_section_for_offset(offset, sections)
        assert section == SectionType.SKILLS
    
    def test_extract_section_text(self):
        service = SectionDetectionService()
        text = """
        Skills
        Python, JavaScript
        
        Experience
        Developer at ABC
        """
        skills_text = service.extract_section_text(text, SectionType.SKILLS)
        assert "Python" in skills_text or "Skills" in skills_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
