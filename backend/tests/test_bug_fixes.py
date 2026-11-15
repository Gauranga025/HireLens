import pytest

from app.services.skill_service import match_skills_to_requirements
from app.services.matching_service import semantic_similarity, compute_match

try:
    import sentence_transformers
    import torch
    HAS_ST = True
except (ImportError, OSError):
    HAS_ST = False


def test_empty_skill_lists_returns_zero_match() -> None:
    """Bug fix: Empty candidate and job skill lists should return 0% match, not 100%."""
    result = match_skills_to_requirements([], [])

    assert result["matched"] == []
    assert result["missing"] == []
    assert result["additional"] == []
    assert result["match_percentage"] == 0.0


def test_empty_required_skills_returns_zero_match() -> None:
    """Bug fix: Empty required skills list should return 0% match."""
    result = match_skills_to_requirements(["Python", "Django"], [])

    assert result["matched"] == []
    assert result["missing"] == []
    assert set(result["additional"]) == {"Python", "Django"}
    assert result["match_percentage"] == 0.0


def test_empty_candidate_skills_returns_zero_match() -> None:
    """Bug fix: Empty candidate skills with requirements should return 0% match."""
    result = match_skills_to_requirements([], ["Python", "Django"])

    assert result["matched"] == []
    assert set(result["missing"]) == {"Python", "Django"}
    assert result["additional"] == []
    assert result["match_percentage"] == 0.0


def test_semantic_similarity_empty_text_returns_none() -> None:
    """Bug fix: Semantic similarity with empty text should return None, not 0.0."""
    assert semantic_similarity("", "test text") is None
    assert semantic_similarity("test text", "") is None
    assert semantic_similarity("", "") is None


def test_semantic_similarity_failure_distinguishable_from_zero() -> None:
    """Bug fix: Semantic model failure returns None, distinguishable from genuine 0.0 score."""
    if HAS_ST:
        text1 = "Completely unrelated text"
        text2 = "Another completely different text"
        score = semantic_similarity(text1, text2)
        if score is not None:
            assert 0.0 <= score <= 1.0
    else:
        score = semantic_similarity("test", "test")
        assert score is None


def test_compute_match_semantic_fallback_activates() -> None:
    """Bug fix: When semantic scoring fails, fallback to TF-IDF + skills should activate."""
    result = compute_match(
        resume_text="Python developer with Django experience.",
        job_text="Backend engineer needing Python and Django.",
        resume_skills=["Python", "Django"],
        job_skills=["Python", "Django"],
        use_semantic=True,
    )

    if HAS_ST:
        if result["semantic_score"] is not None:
            expected_overall = round(
                0.3 * result["tfidf_score"] + 0.4 * result["semantic_score"] + 0.3 * result["skill_match_score"], 2
            )
        else:
            expected_overall = round(
                0.5 * result["tfidf_score"] + 0.5 * result["skill_match_score"], 2
            )
    else:
        assert result["semantic_score"] is None
        expected_overall = round(
            0.5 * result["tfidf_score"] + 0.5 * result["skill_match_score"], 2
        )

    assert result["overall_score"] == expected_overall


def test_compute_match_without_semantic_uses_fallback_weights() -> None:
    """Bug fix: When use_semantic=False, should use 50/50 TF-IDF + skills weights."""
    result = compute_match(
        resume_text="Python developer with Django experience.",
        job_text="Backend engineer needing Python and Django.",
        resume_skills=["Python", "Django"],
        job_skills=["Python", "Django"],
        use_semantic=False,
    )

    assert result["semantic_score"] is None
    expected_overall = round(
        0.5 * result["tfidf_score"] + 0.5 * result["skill_match_score"], 2
    )
    assert result["overall_score"] == expected_overall
