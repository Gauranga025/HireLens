"""
Unit tests for scoring service.
"""
import pytest

try:
    from app.services.scoring_service import ScoringService, ScoringConfig
    SCORING_AVAILABLE = True
except ImportError:
    SCORING_AVAILABLE = False


@pytest.mark.skipif(not SCORING_AVAILABLE, reason="scoring_service imports failed")
class TestScoringService:
    """Test evidence-aware scoring service."""
    
    def test_default_config(self):
        service = ScoringService()
        assert service.config.required_skill_weight == 0.35
        assert service.config.preferred_skill_weight == 0.15
        assert service.config.semantic_weight == 0.30
        assert service.config.evidence_weight == 0.20
    
    def test_custom_config(self):
        config = ScoringConfig(
            required_skill_weight=0.5,
            preferred_skill_weight=0.2,
            semantic_weight=0.2,
            evidence_weight=0.1,
        )
        service = ScoringService(config=config)
        assert service.config.required_skill_weight == 0.5
        assert service.config.evidence_weight == 0.1
    
    def test_compute_match_basic(self):
        service = ScoringService()
        resume_text = "Skills: Python, JavaScript"
        job_text = "Required: Python"
        resume_skills = ["Python", "JavaScript"]
        required_skills = ["Python"]
        preferred_skills = []
        
        result = service.compute_match(
            resume_text,
            job_text,
            resume_skills,
            required_skills,
            preferred_skills,
            use_semantic=False,
        )
        
        assert "overall_score" in result
        assert "required_skill_coverage" in result
        assert "preferred_skill_coverage" in result
        assert "evidence_score" in result
        assert "matched_skills" in result
        assert "missing_skills" in result
        assert "scoring_strategy" in result
    
    def test_compute_match_no_semantic(self):
        service = ScoringService()
        resume_text = "Skills: Python"
        job_text = "Required: Python"
        resume_skills = ["Python"]
        required_skills = ["Python"]
        preferred_skills = []
        
        result = service.compute_match(
            resume_text,
            job_text,
            resume_skills,
            required_skills,
            preferred_skills,
            use_semantic=False,
        )
        
        assert result["scoring_strategy"]["semantic_available"] == False
        assert result["scoring_strategy"]["fallback_used"] == False
    
    def test_compute_match_with_semantic_unavailable(self):
        service = ScoringService()
        resume_text = "Skills: Python"
        job_text = "Required: Python"
        resume_skills = ["Python"]
        required_skills = ["Python"]
        preferred_skills = []
        
        result = service.compute_match(
            resume_text,
            job_text,
            resume_skills,
            required_skills,
            preferred_skills,
            use_semantic=True,
        )
        
        # Semantic may be unavailable depending on environment
        assert "semantic_score" in result
    
    def test_compute_match_empty_inputs(self):
        service = ScoringService()
        result = service.compute_match("", "", [], [], [], use_semantic=False)
        
        assert result["overall_score"] == 0.0
        assert result["required_skill_coverage"] == 0.0
        assert result["matched_skills"] == []
    
    def test_explanation_generation(self):
        service = ScoringService()
        resume_text = "Skills: Python, JavaScript"
        job_text = "Required: Python, Java"
        resume_skills = ["Python", "JavaScript"]
        required_skills = ["Python", "Java"]
        preferred_skills = []
        
        result = service.compute_match(
            resume_text,
            job_text,
            resume_skills,
            required_skills,
            preferred_skills,
            use_semantic=False,
        )
        
        assert "explanation" in result
        assert len(result["explanation"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
