"""Integration regressions for Phase 11.4 requirement-to-chunk semantics."""
import json
import math

import pytest

from app.schemas.matching import MatchResult, ScoringStrategy
from app.services.report_service import generate_json_report, generate_match_summary
from app.services.scoring_service import ScoringConfig, ScoringService
from app.services.semantic_matching_service import SemanticError, SemanticErrorType


class FakeTokenizer:
    model_max_length = 40

    def __call__(self, text, add_special_tokens=True, **kwargs):
        pieces = str(text).split()
        if add_special_tokens:
            pieces = ["[CLS]", *pieces, "[SEP]"]
        return {"input_ids": pieces}


class MatrixSemanticService:
    """New-API semantic fake driven by an explicit similarity function."""

    def __init__(
        self,
        similarity_fn=None,
        matrix_error=False,
        context_error=False,
        matrix_raises=False,
    ):
        self.similarity_fn = similarity_fn or (lambda query, chunk: 0.1)
        self.matrix_error = matrix_error
        self.context_error = context_error
        self.matrix_raises = matrix_raises
        self.calls = []

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
            "tokenizer": FakeTokenizer(),
            "max_seq_length": FakeTokenizer.model_max_length,
            "model_name": "fake-model",
            "model_revision": "fake-revision",
        }

    def compute_similarity_matrix(self, queries, chunks):
        self.calls.append((list(queries), list(chunks)))
        if self.matrix_raises:
            raise RuntimeError("matrix failure")
        if self.matrix_error:
            return None
        return [
            [self.similarity_fn(query, chunk) for chunk in chunks]
            for query in queries
        ]


def _requirement(skill, requirement_type="REQUIRED"):
    return {
        "requirement_type": requirement_type,
        "data": {"skill": skill, "normalized_skill": skill.lower()},
        "original_text": skill,
    }


def _group(mode, skills):
    return {
        "requirement_type": "REQUIRED_GROUP",
        "data": {
            "group_name": "Alternatives",
            "match_mode": mode,
            "skills": [
                {"skill": skill, "normalized_skill": skill.lower()}
                for skill in skills
            ],
        },
        "original_text": ", ".join(skills),
    }


def _score(semantic, resume_text, job_text, resume_skills, requirements, preferred=None):
    service = ScoringService(config=ScoringConfig(), semantic_service=semantic)
    return service.compute_match(
        resume_text=resume_text,
        job_text=job_text,
        resume_skills=resume_skills,
        required_skills=resume_skills,
        preferred_skills=preferred or [],
        use_semantic=True,
        structured_requirements=requirements,
    )


def test_long_resume_evidence_after_the_old_window_can_contribute():
    filler = "\n".join(
        f"Performed routine platform task {index} with standard tooling"
        for index in range(45)
    )
    resume = f"SUMMARY:\n{filler}\nEXPERIENCE:\nBuilt Node.js REST APIs with Express"
    semantic = MatrixSemanticService(
        lambda query, chunk: (
            0.92
            if "node.js" in query.lower() and "node.js" in chunk.lower()
            else 0.05
        )
    )

    result = _score(
        semantic,
        resume,
        "Node.js REST API development",
        ["Node.js"],
        [_requirement("Node.js")],
    )
    details = result["scoring_strategy"]["semantic_details"]

    assert result["semantic_score"] > 0
    assert any("Node.js REST APIs" in entry for _, chunks in semantic.calls for entry in chunks)
    assert details["chunk_stats"]["generated"] > 1
    assert details["retrieval_status"] == "matched"


def test_overflow_keeps_late_evidence_and_records_counts_only():
    resume = "EXPERIENCE:\n" + "\n".join(
        f"Completed generic assignment {index}" if index < 69 else "Built Python APIs"
        for index in range(70)
    )
    semantic = MatrixSemanticService(
        lambda query, chunk: (
            0.88 if "python" in query.lower() and "python" in chunk.lower() else 0.05
        )
    )

    result = _score(
        semantic, resume, "Python APIs", ["Python"], [_requirement("Python")]
    )
    stats = result["scoring_strategy"]["semantic_details"]["chunk_stats"]

    assert result["semantic_score"] > 0
    assert stats["generated"] > 64
    assert stats["retained"] == 64
    assert stats["omitted"] > 0
    assert set(stats) == {"generated", "retained", "omitted", "overflow_policy"}


def test_any_group_only_needs_one_semantically_supported_alternative():
    requirements = [_group("ANY", ["AWS", "Azure"])]
    semantic = MatrixSemanticService(
        lambda query, chunk: (
            0.9 if "azure" in query.lower() and "azure" in chunk.lower() else 0.05
        )
    )

    enabled = _score(
        semantic,
        "EXPERIENCE: Deployed Azure services",
        "AWS or Azure",
        ["Azure"],
        requirements,
    )
    disabled_service = ScoringService(semantic_service=MatrixSemanticService())
    disabled = disabled_service.compute_match(
        resume_text="EXPERIENCE: Deployed Azure services",
        job_text="AWS or Azure",
        resume_skills=["Azure"],
        required_skills=["Azure"],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=requirements,
    )

    assert enabled["semantic_score"] > 0
    assert enabled["group_evaluation"] == disabled["group_evaluation"]
    assert [
        group["is_satisfied"] for group in enabled["group_evaluation"]
    ] == [group["is_satisfied"] for group in disabled["group_evaluation"]]


def test_all_group_missing_member_stays_in_the_semantic_average():
    requirements = [_group("ALL", ["Docker", "Kubernetes"])]
    semantic = MatrixSemanticService(
        lambda query, chunk: (
            0.86 if "docker" in query.lower() and "docker" in chunk.lower() else 0.05
        )
    )

    enabled = _score(
        semantic,
        "EXPERIENCE: Used Docker",
        "Docker and Kubernetes",
        ["Docker"],
        requirements,
    )
    disabled = ScoringService(semantic_service=MatrixSemanticService()).compute_match(
        resume_text="EXPERIENCE: Used Docker",
        job_text="Docker and Kubernetes",
        resume_skills=["Docker"],
        required_skills=["Docker"],
        preferred_skills=[],
        use_semantic=False,
        structured_requirements=requirements,
    )

    assert 0.0 < enabled["semantic_score"] < 60.0
    assert enabled["group_evaluation"] == disabled["group_evaluation"]
    assert enabled["scoring_strategy"]["semantic_details"]["scored_requirements"][0][
        "match_mode"
    ] == "ALL"


def _paraphrase_aware_similarity(query, chunk):
    """Fake provider that treats two explicit phrasings as equivalent."""
    query_lower = query.lower()
    chunk_lower = chunk.lower()
    paraphrases = ("rest api", "node.js", "backend service", "express")
    if any(phrase in query_lower for phrase in paraphrases) and "node.js" in chunk_lower:
        return 0.78
    return 0.05


def test_paraphrased_requirements_have_bounded_score_difference():
    resume = "EXPERIENCE: Built REST APIs with Node.js and Express"
    first_text = "Built REST APIs using Node.js"
    second_text = "Developed backend services with Express"
    first = _score(
        MatrixSemanticService(_paraphrase_aware_similarity),
        resume,
        first_text,
        [first_text],
        [_requirement(first_text)],
    )
    second = _score(
        MatrixSemanticService(_paraphrase_aware_similarity),
        resume,
        second_text,
        [second_text],
        [_requirement(second_text)],
    )

    assert first["semantic_score"] > 0
    assert second["semantic_score"] > 0
    assert abs(first["semantic_score"] - second["semantic_score"]) <= 30.0


def test_irrelevant_boilerplate_scores_below_a_matching_resume():
    similarity = MatrixSemanticService(
        lambda query, chunk: (
            0.9 if "python" in query.lower() and "python" in chunk.lower() else 0.05
        )
    )
    boilerplate = "SUMMARY:\n" + "\n".join(
        ["Responsive collaborative fast-paced results-driven hard-working team player"]
        * 5
    )
    matching = "EXPERIENCE: Built Python APIs"

    boilerplate_score = _score(
        similarity, boilerplate, "Python APIs", ["Python"], [_requirement("Python")]
    )["semantic_score"]
    matching_score = _score(
        similarity, matching, "Python APIs", ["Python"], [_requirement("Python")]
    )["semantic_score"]

    assert matching_score > boilerplate_score


def test_missing_requirement_records_zero_evidence_without_fallback():
    semantic = MatrixSemanticService(lambda query, chunk: 0.1)
    result = _score(
        semantic,
        "EXPERIENCE: Built Java services",
        "Kubernetes operation",
        ["Java"],
        [_requirement("Kubernetes")],
    )
    details = result["scoring_strategy"]["semantic_details"]

    assert result["semantic_score"] == 0.0
    assert result["scoring_strategy"]["semantic_status"] == "used"
    assert result["scoring_strategy"]["fallback_used"] is False
    assert details["retrieval_status"] == "no_relevant_chunks"
    assert details["missing_semantic_evidence"]


def test_more_than_eight_requirement_diagnostics_are_bounded():
    requirements = [_requirement(f"Skill{index}") for index in range(12)]
    semantic = MatrixSemanticService(lambda query, chunk: 0.6)

    result = _score(
        semantic,
        "EXPERIENCE: Built systems",
        "Required: many skills",
        [f"Skill{index}" for index in range(12)],
        requirements,
    )
    details = result["scoring_strategy"]["semantic_details"]

    assert details["requirement_count"] >= 12
    assert details["diagnostic_count"] <= 8
    assert details["omitted_diagnostic_count"] >= 4
    assert result["semantic_score"] == pytest.approx(60.0)


def test_tokenizer_failure_maps_to_inference_failed_and_existing_fallback():
    service = ScoringService(
        semantic_service=MatrixSemanticService(context_error=True)
    )
    result = service.compute_match(
        resume_text="EXPERIENCE: Built Python APIs",
        job_text="Python APIs",
        resume_skills=["Python"],
        required_skills=["Python"],
        preferred_skills=[],
        use_semantic=True,
    )
    strategy = result["scoring_strategy"]

    assert result["semantic_score"] is None
    assert strategy["semantic_status"] == "inference_failed"
    assert strategy["fallback_used"] is True
    assert strategy["semantic_details"] is None
    assert strategy["weights"] == pytest.approx(
        {
            "required_skills": 0.35 / 0.70,
            "preferred_skills": 0.15 / 0.70,
            "semantic": 0.0,
            "evidence": 0.20 / 0.70,
            "tfidf": 0.0,
        }
    )


def test_matrix_failure_maps_to_inference_failed():
    for semantic in (
        MatrixSemanticService(matrix_error=True),
        MatrixSemanticService(matrix_raises=True),
    ):
        result = _score(
            semantic,
            "EXPERIENCE: Built Python APIs",
            "Python APIs",
            ["Python"],
            [_requirement("Python")],
        )
        assert result["semantic_score"] is None
        assert result["scoring_strategy"]["semantic_status"] == "inference_failed"
        assert result["scoring_strategy"]["fallback_used"] is True


def test_api_schema_accepts_additive_semantic_details():
    result = _score(
        MatrixSemanticService(lambda query, chunk: 0.7),
        "EXPERIENCE: Built Python APIs",
        "Python APIs",
        ["Python"],
        [_requirement("Python")],
    )

    validated = MatchResult(**result)
    strategy = ScoringStrategy(**result["scoring_strategy"])

    assert validated.semantic_score == result["semantic_score"]
    assert strategy.semantic_details["algorithm"] == "requirement_chunk_v1"


def test_report_generation_reads_the_same_semantic_scalar():
    result = _score(
        MatrixSemanticService(lambda query, chunk: 0.7),
        "EXPERIENCE: Built Python APIs",
        "Python APIs",
        ["Python"],
        [_requirement("Python")],
    )
    summary = generate_match_summary(result)
    report = json.loads(generate_json_report({}, result))

    expected = f"{result['semantic_score']:.1f}%"
    assert expected in summary
    assert report["match_result"]["semantic_score"] == result["semantic_score"]


def test_repeated_evaluations_are_deterministic():
    kwargs = dict(
        semantic=MatrixSemanticService(lambda query, chunk: 0.73),
        resume_text="EXPERIENCE: Built Python APIs",
        job_text="Python APIs",
        resume_skills=["Python"],
        requirements=[_requirement("Python")],
    )
    first = _score(**kwargs)
    second = _score(**kwargs)

    assert first["semantic_score"] == second["semantic_score"]
    assert first["scoring_strategy"]["semantic_details"] == second[
        "scoring_strategy"
    ]["semantic_details"]
    assert [
        chunk for _, chunks in kwargs["semantic"].calls for chunk in chunks
    ]
    assert all(
        not math.isnan(value)
        for value in (first["semantic_score"], second["semantic_score"])
    )
