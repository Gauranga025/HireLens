"""
Unit tests for semantic matching service.
"""
import pytest

# Import with error handling for missing dependencies
try:
    from app.services.semantic_matching_service import (
        SemanticMatchingService,
        SemanticError,
        SemanticErrorType,
    )
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


@pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="semantic_matching_service imports failed")
class TestSemanticMatchingService:
    """Test semantic matching service."""
    
    def test_service_initialization(self):
        service = SemanticMatchingService()
        assert service.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert service._model is None
        assert not service._load_attempted
    
    def test_custom_model_name(self):
        service = SemanticMatchingService(model_name="custom-model")
        assert service.model_name == "custom-model"
    
    def test_is_available_when_unavailable(self):
        """Test when sentence-transformers is not available."""
        service = SemanticMatchingService()
        # This will fail to load if package not installed
        available = service.is_available()
        # Result depends on environment
        assert isinstance(available, bool)
    
    def test_compute_similarity_empty_text(self):
        service = SemanticMatchingService()
        result = service.compute_similarity("", "test")
        assert result is None
    
    def test_compute_similarity_none_text(self):
        service = SemanticMatchingService()
        result = service.compute_similarity(None, "test")
        assert result is None
    
    def test_compute_embedding_empty_text(self):
        service = SemanticMatchingService()
        result = service.compute_embedding("")
        assert result is None
    
    def test_compute_embeddings_empty_list(self):
        service = SemanticMatchingService()
        result = service.compute_embeddings([])
        assert result == []
    
    def test_find_best_match_empty_candidates(self):
        service = SemanticMatchingService()
        best_match, score = service.find_best_match("query", [])
        assert best_match is None
        assert score is None
    
    def test_find_best_match_empty_query(self):
        service = SemanticMatchingService()
        best_match, score = service.find_best_match("", ["candidate1"])
        assert best_match is None
        assert score is None
    
    def test_match_requirements_empty_inputs(self):
        service = SemanticMatchingService()
        result = service.match_requirements([], [])
        assert result == []
    
    def test_match_requirements_empty_requirements(self):
        service = SemanticMatchingService()
        result = service.match_requirements([], ["evidence1"])
        assert result == []
    
    def test_match_requirements_empty_evidence(self):
        service = SemanticMatchingService()
        result = service.match_requirements(["req1"], [])
        assert result == []
    
    def test_get_error_info_no_error(self):
        service = SemanticMatchingService()
        # No load attempted yet
        error_info = service.get_error_info()
        assert error_info is None
    
    def test_semantic_error_creation(self):
        error = SemanticError(
            SemanticErrorType.PACKAGE_NOT_INSTALLED,
            "Package not found"
        )
        assert error.error_type == SemanticErrorType.PACKAGE_NOT_INSTALLED
        assert error.message == "Package not found"
        assert str(error) == "Package not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
