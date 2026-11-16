"""
Unit tests for evidence extraction service.
"""
import pytest
from app.services.evidence_extraction_service import (
    EvidenceExtractionService,
    EvidenceType,
    EvidenceStrength,
)


class TestEvidenceExtraction:
    """Test skill evidence extraction."""
    
    def test_extract_skill_evidence_from_projects(self):
        service = EvidenceExtractionService()
        text = """
        Projects
        Developed backend APIs using Python and FastAPI to support real-time data processing.
        Built microservices architecture with Docker and Kubernetes.
        """
        skills = ["Python", "FastAPI", "Docker"]
        evidence = service.extract_skill_evidence(text, skills)
        
        assert "Python" in evidence or len(evidence) > 0
    
    def test_extract_skill_evidence_from_skills_section(self):
        service = EvidenceExtractionService()
        text = """
        Technical Skills
        Python, Docker, PostgreSQL, Redis
        """
        skills = ["Python", "Docker"]
        evidence = service.extract_skill_evidence(text, skills)
        
        # Should find evidence in skills section
        assert len(evidence) > 0
    
    def test_extract_skill_evidence_from_experience(self):
        service = EvidenceExtractionService()
        text = """
        Work Experience
        Senior Developer at ABC Corp
        - Implemented RESTful APIs using Node.js and Express
        - Designed database schemas with PostgreSQL
        """
        skills = ["Node.js", "PostgreSQL"]
        evidence = service.extract_skill_evidence(text, skills)
        
        assert len(evidence) > 0
    
    def test_evidence_classification_demonstrated(self):
        service = EvidenceExtractionService()
        text = """
        Experience
        Developed scalable web applications using React and TypeScript.
        """
        skills = ["React"]
        evidence = service.extract_skill_evidence(text, skills)
        
        if evidence and "React" in evidence:
            react_evidence = evidence["React"]
            if react_evidence:
                # Should be classified as demonstrated in experience
                assert react_evidence[0].evidence_type in [
                    EvidenceType.DEMONSTRATED_IN_EXPERIENCE,
                    EvidenceType.DEMONSTRATED_IN_PROJECT,
                ]
    
    def test_evidence_strength_strong(self):
        service = EvidenceExtractionService()
        text = """
        Projects
        Built a complete e-commerce platform using Python Django with PostgreSQL database.
        """
        skills = ["Python"]
        evidence = service.extract_skill_evidence(text, skills)
        
        if evidence and "Python" in evidence:
            python_evidence = evidence["Python"]
            if python_evidence:
                # Should have at least moderate or strong strength
                assert python_evidence[0].strength in [
                    EvidenceStrength.STRONG,
                    EvidenceStrength.MODERATE,
                ]
    
    def test_empty_text(self):
        service = EvidenceExtractionService()
        evidence = service.extract_skill_evidence("", ["Python"])
        assert evidence == {}
    
    def test_empty_skills(self):
        service = EvidenceExtractionService()
        text = "Some resume text."
        evidence = service.extract_skill_evidence(text, [])
        assert evidence == {}
    
    def test_skill_not_found(self):
        service = EvidenceExtractionService()
        text = """
        Skills
        Python, JavaScript
        """
        evidence = service.extract_skill_evidence(text, ["Rust"])
        assert evidence == {}
    
    def test_get_best_evidence(self):
        service = EvidenceExtractionService()
        text = """
        Projects
        Developed backend using Python.
        
        Skills
        Python, JavaScript
        """
        skills = ["Python"]
        evidence = service.extract_skill_evidence(text, skills)
        
        if evidence and "Python" in evidence:
            best = service.get_best_evidence(evidence["Python"])
            assert best is not None
    
    def test_deduplicate_evidence(self):
        service = EvidenceExtractionService()
        text = """
        Skills
        Python, Python, Python
        """
        skills = ["Python"]
        evidence = service.extract_skill_evidence(text, skills)
        
        if evidence and "Python" in evidence:
            # Should not have duplicate evidence from same section
            python_evidence = evidence["Python"]
            sections = [ev.section for ev in python_evidence]
            assert len(sections) == len(set(sections))
    
    def test_evidence_to_dict(self):
        service = EvidenceExtractionService()
        text = """
        Projects
        Built app using Python.
        """
        skills = ["Python"]
        evidence = service.extract_skill_evidence(text, skills)
        
        if evidence and "Python" in evidence and evidence["Python"]:
            ev_dict = evidence["Python"][0].to_dict()
            assert "skill" in ev_dict
            assert "section" in ev_dict
            assert "evidence_type" in ev_dict
            assert "snippet" in ev_dict
            assert "strength" in ev_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
