"""
Unit tests for semantic matching service.
"""
import numpy as np
import pytest

from app.services.semantic_matching_service import (
    CHUNK_EMBEDDING_CACHE_SIZE,
    REQUIREMENT_EMBEDDING_CACHE_SIZE,
    VERIFIED_MODEL_REVISION,
)

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
        assert service.model_revision == VERIFIED_MODEL_REVISION
        assert service._model is None
        assert not service._load_attempted

    def test_custom_model_name(self):
        service = SemanticMatchingService(model_name="custom-model")
        assert service.model_name == "custom-model"
        assert service.model_revision == "main"

    def test_revision_is_read_from_sentence_transformers_v3_model(self):
        class _Config:
            _commit_hash = "test-revision"

        class _AutoModel:
            config = _Config()

        class _FirstModule:
            auto_model = _AutoModel()

        class _LoadedModel:
            def _first_module(self):
                return _FirstModule()

        service = SemanticMatchingService()
        service._model = _LoadedModel()
        assert service._revision_from_model() == "test-revision"
    
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


class _FakeTokenizer:
    model_max_length = 64

    def __call__(self, text, add_special_tokens=True, **kwargs):
        pieces = str(text).split()
        if add_special_tokens:
            pieces = ["[CLS]", *pieces, "[SEP]"]
        return {"input_ids": pieces}


class _FakeModel:
    """Deterministic embedder that records batch calls."""

    VECTORS = {
        "q1": (1.0, 0.0),
        "q2": (-1.0, 0.0),
        "c1": (1.0, 0.0),
        "c2": (0.0, 1.0),
    }

    def __init__(self):
        self.tokenizer = _FakeTokenizer()
        self.max_seq_length = 64
        self._model_revision = "fake-revision"
        self.encode_calls = []

    def encode(self, texts, convert_to_numpy=True):
        self.encode_calls.append(list(texts))
        vectors = [self.VECTORS.get(text, (1.0, 1.0)) for text in texts]
        return np.asarray(vectors, dtype=float)


class _FakeSemanticMatchingService(SemanticMatchingService):
    """Service with the real model loader bypassed."""

    def __init__(self):
        super().__init__()
        self._model = _FakeModel()
        self._load_attempted = True
        self._load_error = None

    def _load_model(self):
        return None


@pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="semantic_matching_service imports failed")
class TestSemanticMatchingBatchAndCache:
    """Phase 11.4 batch, matrix, and bounded-cache behaviour."""

    def test_cache_bounds_match_plan(self):
        assert REQUIREMENT_EMBEDDING_CACHE_SIZE == 256
        assert CHUNK_EMBEDDING_CACHE_SIZE == 2048

    def test_model_context_uses_loaded_tokenizer_and_length(self):
        service = _FakeSemanticMatchingService()
        context = service.get_model_context()

        assert context["tokenizer"] is service._model.tokenizer
        assert context["max_seq_length"] == 64
        assert context["model_revision"] == "fake-revision"

    def test_model_context_without_tokenizer_fails(self):
        service = _FakeSemanticMatchingService()
        service._model.tokenizer = None
        with pytest.raises(SemanticError):
            service.get_model_context()

    def test_model_context_without_max_length_fails(self):
        service = _FakeSemanticMatchingService()
        service._model.max_seq_length = None
        service._model.tokenizer.model_max_length = None
        with pytest.raises(SemanticError):
            service.get_model_context()

    def test_similarity_matrix_is_clipped_and_shaped(self):
        service = _FakeSemanticMatchingService()
        matrix = service.compute_similarity_matrix(["q1", "q2"], ["c1", "c2"])

        assert matrix is not None
        assert matrix.shape == (2, 2)
        assert matrix.min() >= 0.0
        assert matrix.max() <= 1.0
        assert matrix[0, 0] == pytest.approx(1.0)
        assert matrix[1, 0] == pytest.approx(0.0)

    def test_duplicate_texts_are_embedded_once_and_cached(self):
        service = _FakeSemanticMatchingService()
        first = service.compute_embeddings_cached(["q1", "q1", "c1"], "requirement")
        second = service.compute_embeddings_cached(["q1", "c1"], "requirement")

        assert len(first) == 3
        assert first[0] is first[1]
        assert service._model.encode_calls == [["q1", "c1"]]
        assert service._embedding_caches["requirement"].__len__() == 2
        stats = service.get_cache_stats()["requirement"]
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert all(np.array_equal(first[0], value) for value in second)

    def test_chunk_cache_is_bounded_with_lru_eviction(self):
        service = _FakeSemanticMatchingService()
        service._cache_limits["chunk"] = 2
        service.compute_embeddings_cached(["c1", "c2", "unknown"], "chunk")

        cache = service._embedding_caches["chunk"]
        stats = service.get_cache_stats()["chunk"]
        assert len(cache) == 2
        assert stats["size"] == 2
        assert stats["evictions"] == 1

    def test_cache_key_includes_model_revision(self):
        service = _FakeSemanticMatchingService()
        service.compute_embeddings_cached(["q1"], "requirement")
        service._model._model_revision = "new-revision"
        service.compute_embeddings_cached(["q1"], "requirement")

        assert len(service._model.encode_calls) == 2
        assert len(service._embedding_caches["requirement"]) == 2

    def test_cached_matrix_is_deterministic(self):
        service = _FakeSemanticMatchingService()
        first = service.compute_similarity_matrix(["q1", "q2"], ["c1", "c2"])
        second = service.compute_similarity_matrix(["q1", "q2"], ["c1", "c2"])

        assert first is not None and second is not None
        assert np.array_equal(first, second)
        assert len(service._model.encode_calls) == 2

    def test_failed_batch_returns_no_matrix(self):
        service = _FakeSemanticMatchingService()
        service.compute_embeddings = lambda texts: [None] * len(texts)
        assert service.compute_similarity_matrix(["q1"], ["c1"]) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
