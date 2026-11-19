"""
Unit tests for scoring service.
"""
import pytest

try:
    from app.services.scoring_service import ScoringService, ScoringConfig
    from app.services.semantic_matching_service import SemanticError, SemanticErrorType
    SCORING_AVAILABLE = True
except ImportError:
    SCORING_AVAILABLE = False


class UnavailableSemanticService:
    """Test double that avoids loading the real embedding model."""

    def is_available(self) -> bool:
        return False

    def get_error_info(self):
        return {"error_type": "model_loading_failure", "message": "test stub"}

    def compute_similarity(self, text1: str, text2: str):
        return None


class _FakeTokenizer:
    model_max_length = 32

    def __call__(self, text, add_special_tokens=True, **kwargs):
        pieces = str(text).split()
        if add_special_tokens:
            pieces = ["[CLS]", *pieces, "[SEP]"]
        return {"input_ids": pieces}


class RequirementApiSemanticService:
    """New-API fake that never loads the real model."""

    def __init__(self, context_error=False, matrix_error=False):
        self.context_error = context_error
        self.matrix_error = matrix_error
        self.matrix_calls = []

    def is_available(self):
        return True

    def get_error_info(self):
        return None

    def get_model_context(self):
        if self.context_error:
            raise SemanticError(
                SemanticErrorType.MODEL_LOADING_FAILURE,
                "tokenizer unavailable",
            )
        return {
            "tokenizer": _FakeTokenizer(),
            "max_seq_length": 32,
            "model_name": "fake",
            "model_revision": "fake",
        }

    def compute_similarity_matrix(self, queries, chunks):
        self.matrix_calls.append((list(queries), list(chunks)))
        if self.matrix_error:
            return None
        return [
            [
                0.82 if "python" in query.lower() and "python" in chunk.lower() else 0.1
                for chunk in chunks
            ]
            for query in queries
        ]


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
        service = ScoringService(semantic_service=UnavailableSemanticService())
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
        
        assert result["semantic_score"] is None
        strategy = result["scoring_strategy"]
        assert strategy["semantic_status"] == "model_unavailable"
        assert strategy["semantic_available"] is False
        assert strategy["semantic_model_available"] is False
        assert strategy["fallback_used"] is True
        assert sum(strategy["weights"].values()) == pytest.approx(1.0)
    
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

    def test_requirement_semantic_path_adds_bounded_details(self):
        semantic = RequirementApiSemanticService()
        service = ScoringService(semantic_service=semantic)
        structured = [
            {
                "requirement_type": "REQUIRED",
                "data": {"skill": "Python", "normalized_skill": "python"},
                "original_text": "Python required",
            }
        ]

        result = service.compute_match(
            "EXPERIENCE: Built Python APIs",
            "Required: Python",
            ["Python"],
            ["Python"],
            [],
            use_semantic=True,
            structured_requirements=structured,
        )

        strategy = result["scoring_strategy"]
        assert result["semantic_score"] == pytest.approx(82.0)
        assert strategy["semantic_status"] == "used"
        assert strategy["fallback_used"] is False
        assert strategy["configured_weights"] == {
            "required_skills": 0.35,
            "preferred_skills": 0.15,
            "semantic": 0.30,
            "evidence": 0.20,
            "tfidf": 0.0,
        }
        assert strategy["semantic_details"]["algorithm"] == "requirement_chunk_v1"
        assert strategy["semantic_details"]["diagnostic_count"] <= 8
        assert semantic.matrix_calls

    def test_new_api_context_failure_maps_to_inference_failed(self):
        service = ScoringService(
            semantic_service=RequirementApiSemanticService(context_error=True)
        )

        result = service.compute_match(
            "EXPERIENCE: Built Python APIs",
            "Required: Python",
            ["Python"],
            ["Python"],
            [],
            use_semantic=True,
        )

        assert result["semantic_score"] is None
        assert result["scoring_strategy"]["semantic_status"] == "inference_failed"
        assert result["scoring_strategy"]["fallback_used"] is True
        assert result["scoring_strategy"]["semantic_error"]["error_type"] == (
            "model_loading_failure"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
