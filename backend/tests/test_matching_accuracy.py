"""
Unit tests for matching accuracy improvements.
Tests skill normalization, alternative skills, and matching behavior.
"""
import pytest
from app.utils.text_processor import normalize_skill_name
from app.services.skill_service import match_skills_to_requirements, extract_skills
from app.services.job_analysis_service import analyze_job_description, detect_alternative_skills


class TestSkillNormalization:
    """Test skill alias normalization."""
    
    def test_js_normalization(self):
        assert normalize_skill_name("js") == "javascript"
        assert normalize_skill_name("JS") == "javascript"
    
    def test_node_normalization(self):
        assert normalize_skill_name("node") == "node.js"
        assert normalize_skill_name("nodejs") == "node.js"
    
    def test_postgres_normalization(self):
        assert normalize_skill_name("postgre") == "postgresql"
        assert normalize_skill_name("postgres") == "postgresql"
    
    def test_mongo_normalization(self):
        assert normalize_skill_name("mongo") == "mongodb"
    
    def test_ts_normalization(self):
        assert normalize_skill_name("ts") == "typescript"
    
    def test_python_normalization(self):
        assert normalize_skill_name("py") == "python"
    
    def test_oop_normalization(self):
        assert normalize_skill_name("oop") == "object-oriented programming"
    
    def test_rest_normalization(self):
        assert normalize_skill_name("rest") == "rest api"
        assert normalize_skill_name("restful") == "rest api"
    
    def test_unknown_skill(self):
        assert normalize_skill_name("unknownskill") == "unknownskill"
    
    def test_empty_skill(self):
        assert normalize_skill_name("") == ""
        assert normalize_skill_name(None) == ""


class TestAlternativeSkillsDetection:
    """Test detection of alternative skills in job descriptions."""
    
    def test_or_pattern(self):
        line = "Python, Java, or JavaScript"
        skills = ["Python", "Java", "JavaScript", "C++"]
        alternatives = detect_alternative_skills(line, skills)
        assert len(alternatives) == 3
        assert "Python" in alternatives
        assert "Java" in alternatives
        assert "JavaScript" in alternatives
    
    def test_slash_pattern(self):
        line = "Node.js/Express.js"
        skills = ["Node.js", "Express.js", "React"]
        alternatives = detect_alternative_skills(line, skills)
        assert len(alternatives) == 2
        assert "Node.js" in alternatives
        assert "Express.js" in alternatives
    
    def test_no_alternative(self):
        line = "Python and Java"
        skills = ["Python", "Java"]
        alternatives = detect_alternative_skills(line, skills)
        assert len(alternatives) == 0
    
    def test_single_skill(self):
        line = "Python"
        skills = ["Python"]
        alternatives = detect_alternative_skills(line, skills)
        assert len(alternatives) == 0


class TestSkillMatching:
    """Test skill matching with normalization and alternatives."""
    
    def test_exact_match(self):
        candidate = ["Python", "JavaScript", "SQL"]
        required = ["Python", "SQL"]
        result = match_skills_to_requirements(candidate, required)
        assert result["match_percentage"] == 100.0
        assert len(result["matched"]) == 2
        assert len(result["missing"]) == 0
    
    def test_normalized_match(self):
        candidate = ["js", "node"]
        required = ["JavaScript", "Node.js"]
        result = match_skills_to_requirements(candidate, required)
        assert result["match_percentage"] == 100.0
        assert len(result["matched"]) == 2
    
    def test_partial_match(self):
        candidate = ["Python", "SQL"]
        required = ["Python", "Java", "SQL"]
        result = match_skills_to_requirements(candidate, required)
        assert result["match_percentage"] == 66.67
        assert len(result["matched"]) == 2
        assert len(result["missing"]) == 1
        assert "Java" in result["missing"]
    
    def test_additional_skills(self):
        candidate = ["Python", "Java", "React", "Docker"]
        required = ["Python", "SQL"]
        result = match_skills_to_requirements(candidate, required)
        assert len(result["additional"]) == 3
        assert "React" in result["additional"]
    
    def test_empty_candidate(self):
        candidate = []
        required = ["Python", "Java"]
        result = match_skills_to_requirements(candidate, required)
        assert result["match_percentage"] == 0.0
        assert len(result["matched"]) == 0
        assert len(result["missing"]) == 2
    
    def test_empty_requirements(self):
        candidate = ["Python", "Java"]
        required = []
        result = match_skills_to_requirements(candidate, required)
        assert result["match_percentage"] == 0.0
        assert len(result["additional"]) == 2


class TestJobAnalysis:
    """Test job description analysis."""
    
    def test_basic_jd(self):
        jd = """
        Senior Python Developer
        
        Required Skills:
        - Python
        - Django
        - PostgreSQL
        
        Preferred Skills:
        - Docker
        - Kubernetes
        """
        result = analyze_job_description(jd)
        assert result["title"] == "Senior Python Developer"
        assert "Python" in result["required_skills"]
        assert "Django" in result["required_skills"]
        assert len(result["required_skills"]) >= 2
    
    def test_jd_with_alternatives(self):
        jd = """
        Software Engineer
        
        Required:
        - Experience with Python, Java, or JavaScript
        - SQL knowledge
        
        Preferred:
        - Docker
        """
        result = analyze_job_description(jd)
        # Should detect multiple skills from the alternative line
        assert len(result["required_skills"]) >= 2
    
    def test_empty_jd(self):
        result = analyze_job_description("")
        assert result["title"] == "Not found"
        assert result["required_skills"] == []


class TestSkillExtraction:
    """Test skill extraction from text."""
    
    def test_extract_python_skills(self):
        text = "Experience with Python, Django, Flask, and PostgreSQL"
        result = extract_skills(text)
        assert "Python" in result["technical_skills"]
    
    def test_extract_web_skills(self):
        text = "Built applications using React, Node.js, and MongoDB"
        result = extract_skills(text)
        assert "React" in result["technical_skills"]
        assert "Node.js" in result["technical_skills"]
    
    def test_extract_devops_skills(self):
        text = "Deployed with Docker, Kubernetes, and CI/CD pipelines"
        result = extract_skills(text)
        assert "Docker" in result["technical_skills"]
        assert "Kubernetes" in result["technical_skills"]
    
    def test_empty_text(self):
        result = extract_skills("")
        assert result["technical_skills"] == []
        assert result["soft_skills"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
