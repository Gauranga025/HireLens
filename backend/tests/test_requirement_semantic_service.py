"""Tests for the requirement-to-chunk semantic scorer."""
import pytest

from app.services.requirement_semantic_service import (
    RequirementSemanticService,
    SemanticScoringError,
    aggregate_unit_scores,
)
from app.services.semantic_input_service import (
    MAX_METADATA_TEXT_CHARS,
    MAX_SEMANTIC_DIAGNOSTICS,
    RANK_WEIGHTS,
    RELEVANCE_THRESHOLD,
    TOP_K,
    ResumeChunk,
    SemanticInputs,
    SemanticUnit,
)


_MISSING = object()


class MatrixProvider:
    """Deterministic similarity provider keyed by query text."""

    def __init__(self, mapping=None, matrix=None, error=_MISSING, raises=False):
        self.mapping = mapping or {}
        self.matrix = matrix
        self.error = error
        self.raises = raises
        self.calls = []

    def compute_similarity_matrix(self, queries, chunks):
        self.calls.append((list(queries), list(chunks)))
        if self.raises:
            raise RuntimeError("simulated matrix failure")
        if self.error is not _MISSING:
            return self.error
        if self.matrix is not None:
            return self.matrix
        return [
            [float(self.mapping.get(query, [0.0] * len(chunks))[index]) for index in range(len(chunks))]
            for query in queries
        ]


def _chunk(index=0, beta=1.0, section="EXPERIENCE", offset=None):
    return ResumeChunk(
        chunk_id=f"{index:04d}",
        section_type=section,
        section_key=f"0:{section}",
        section_index=0,
        offset=index if offset is None else offset,
        text=f"{section}: content {index}",
        token_count=8,
        beta=beta,
    )


def _unit(
    unit_id,
    query,
    alpha=1.0,
    member_queries=None,
    match_mode=None,
    label=None,
):
    query_texts = [query]
    member_query_texts = []
    if member_queries is not None:
        member_query_texts = [[member] for member in member_queries]
        query_texts = list(member_queries)
    return SemanticUnit(
        unit_id=unit_id,
        requirement_type="REQUIRED_GROUP" if match_mode else "REQUIRED",
        text=label or query,
        alpha=alpha,
        source_index=int(unit_id.rsplit("-", 1)[-1]) if unit_id.rsplit("-", 1)[-1].isdigit() else 0,
        kind="group" if match_mode else "individual",
        label=label or query,
        scored=True,
        is_group=match_mode is not None,
        match_mode=match_mode,
        member_texts=list(member_queries or []),
        query_texts=query_texts,
        member_query_texts=member_query_texts,
    )


def _inputs(units, chunks, context_count=0):
    return SemanticInputs(
        units=units,
        chunks=chunks,
        chunk_stats={"generated": len(chunks), "retained": len(chunks), "omitted": 0, "overflow_policy": "tail_and_section_anchors_v1"},
        max_seq_length=256,
        token_limit=240,
        context_unit_count=context_count,
    )


def test_defaults_match_the_approved_plan():
    assert RELEVANCE_THRESHOLD == 0.25
    assert TOP_K == 3
    assert RANK_WEIGHTS == (1.00, 0.50, 0.25)
    assert MAX_SEMANTIC_DIAGNOSTICS == 8
    assert MAX_METADATA_TEXT_CHARS == 120


def test_one_qualifying_chunk_uses_one_chunk_denominator():
    inputs = _inputs([_unit("u-0", "query")], [_chunk()])
    result = RequirementSemanticService().score(
        inputs, MatrixProvider({"query": [0.78]})
    )

    assert result.score == pytest.approx(78.0)
    assert result.q_by_unit_id["u-0"] == pytest.approx(0.78)
    assert result.retrieval_status == "matched"


def test_two_and_three_qualifying_chunks_use_actual_weight_sums():
    service = RequirementSemanticService()

    two = service.score(
        _inputs([_unit("u-0", "query")], [_chunk(0), _chunk(1)]),
        MatrixProvider({"query": [0.80, 0.60]}),
    )
    three = service.score(
        _inputs([_unit("u-0", "query")], [_chunk(0), _chunk(1), _chunk(2)]),
        MatrixProvider({"query": [0.80, 0.60, 0.40]}),
    )

    assert two.q_by_unit_id["u-0"] == pytest.approx((0.80 + 0.5 * 0.60) / 1.50)
    assert three.q_by_unit_id["u-0"] == pytest.approx(
        (0.80 + 0.5 * 0.60 + 0.25 * 0.40) / 1.75
    )
    assert 0.0 <= three.score <= 100.0


def test_no_qualifying_chunk_is_zero_but_model_path_is_used():
    result = RequirementSemanticService().score(
        _inputs([_unit("u-0", "query")], [_chunk()]),
        MatrixProvider({"query": [0.24]}),
    )

    assert result.score == 0.0
    assert result.q_by_unit_id["u-0"] == 0.0
    assert result.retrieval_status == "no_relevant_chunks"
    assert result.details["retrieval_status"] == "no_relevant_chunks"


def test_worked_example_mixed_requirements_matches_expected_score():
    units = [
        _unit("u-0", "qa", alpha=1.0, label="Required A"),
        _unit("u-1", "qb", alpha=1.0, label="Required B"),
        _unit("u-2", "qc", alpha=0.5, label="Preferred C"),
        _unit("u-3", "qd", alpha=0.25, label="Responsibility D"),
    ]
    provider = MatrixProvider(
        {
            "qa": [0.82, 0.61, 0.30],
            "qb": [0.48, 0.10, 0.10],
            "qc": [0.74, 0.55, 0.10],
            "qd": [0.10, 0.10, 0.10],
        }
    )

    result = RequirementSemanticService().score(
        _inputs(units, [_chunk(0), _chunk(1), _chunk(2)], context_count=1), provider
    )

    assert result.q_by_unit_id["u-0"] == pytest.approx(0.6857142857)
    assert result.q_by_unit_id["u-1"] == pytest.approx(0.48)
    assert result.q_by_unit_id["u-2"] == pytest.approx(0.6766666667)
    assert result.q_by_unit_id["u-3"] == 0.0
    assert result.score == pytest.approx(54.69, abs=0.01)
    assert result.details["alpha_total"] == pytest.approx(2.75)
    assert result.details["context_requirement_count"] == 1


def test_any_group_uses_member_maximum_once():
    group = _unit(
        "g-0",
        "",
        member_queries=["aws", "azure", "gcp"],
        match_mode="ANY",
    )
    provider = MatrixProvider({"aws": [0.20], "azure": [0.73], "gcp": [0.41]})

    result = RequirementSemanticService().score(_inputs([group], [_chunk()]), provider)
    diagnostics = result.details["scored_requirements"]

    assert result.q_by_unit_id["g-0"] == pytest.approx(0.73)
    assert result.score == pytest.approx(73.0)
    assert result.details["alpha_total"] == 1.0
    assert diagnostics[0]["match_mode"] == "ANY"
    assert diagnostics[0]["member_count"] == 3


def test_all_group_average_keeps_missing_member_in_denominator():
    group = _unit(
        "g-0",
        "",
        member_queries=["docker", "kubernetes", "terraform"],
        match_mode="ALL",
    )
    provider = MatrixProvider(
        {"docker": [0.80], "kubernetes": [0.60], "terraform": [0.10]}
    )

    result = RequirementSemanticService().score(_inputs([group], [_chunk()]), provider)

    assert result.q_by_unit_id["g-0"] == pytest.approx((0.80 + 0.60 + 0.0) / 3.0)
    assert result.score == pytest.approx(46.67, abs=0.01)
    assert result.details["scored_requirements"][0]["match_mode"] == "ALL"


def test_top_k_ranking_uses_beta_sim_and_stable_tie_breakers():
    chunks = [
        _chunk(0, beta=0.4, section="SKILLS", offset=0),
        _chunk(1, beta=1.0, section="EXPERIENCE", offset=50),
        _chunk(2, beta=0.4, section="EDUCATION", offset=90),
    ]
    provider = MatrixProvider({"q": [0.90, 0.50, 0.90]})
    result = RequirementSemanticService().score(_inputs([_unit("u-0", "q")], chunks), provider)

    assert result.q_by_unit_id["u-0"] == pytest.approx(
        (1.00 * 0.50 + 0.50 * 0.90 + 0.25 * 0.90) / 1.75
    )
    diagnostic = result.details["scored_requirements"][0]
    assert diagnostic["best_section"] == "EXPERIENCE"
    assert diagnostic["best_offset"] == 50


def test_top_k_limits_contributing_chunks():
    chunks = [_chunk(index) for index in range(5)]
    provider = MatrixProvider({"q": [0.90, 0.80, 0.70, 0.60, 0.50]})

    result = RequirementSemanticService().score(_inputs([_unit("u-0", "q")], chunks), provider)

    assert result.q_by_unit_id["u-0"] == pytest.approx(
        (1.00 * 0.90 + 0.50 * 0.80 + 0.25 * 0.70) / 1.75
    )


def test_zero_beta_chunks_never_qualify():
    chunks = [_chunk(0, beta=0.0, section="PERSONAL_INFO")]
    result = RequirementSemanticService().score(
        _inputs([_unit("u-0", "q")], chunks), MatrixProvider({"q": [0.95]})
    )
    assert result.q_by_unit_id["u-0"] == 0.0


def test_no_requirements_returns_zero_without_crashing():
    result = RequirementSemanticService().score(_inputs([], [_chunk()]), MatrixProvider())
    assert result.score == 0.0
    assert result.details["alpha_total"] == 0.0
    assert result.retrieval_status == "no_relevant_chunks"


def test_aggregate_unit_scores_is_clamped():
    unit = _unit("u-0", "q")
    score, meta = aggregate_unit_scores([unit], {"u-0": 9.0})
    assert score == 100.0
    assert meta["scored_unit_count"] == 1


def test_matrix_failures_raise_semantic_scoring_error():
    service = RequirementSemanticService()
    with pytest.raises(SemanticScoringError):
        service.score(_inputs([_unit("u-0", "q")], [_chunk()]), MatrixProvider(error=None, raises=True))
    with pytest.raises(SemanticScoringError):
        service.score(_inputs([_unit("u-0", "q")], [_chunk()]), MatrixProvider(error=None))
    with pytest.raises(SemanticScoringError):
        service.score(
            _inputs([_unit("u-0", "q")], [_chunk()]),
            MatrixProvider(matrix=[[0.2, 0.3]]),
        )


def test_diagnostics_are_bounded_and_text_is_truncated():
    units = [_unit(f"u-{index}", f"q{index}", label="x" * 200) for index in range(10)]
    provider = MatrixProvider({f"q{index}": [0.5] for index in range(10)})

    result = RequirementSemanticService().score(_inputs(units, [_chunk()]), provider)
    details = result.details

    assert details["requirement_count"] == 10
    assert details["diagnostic_count"] <= MAX_SEMANTIC_DIAGNOSTICS
    assert details["omitted_diagnostic_count"] == 2
    assert len(details["scored_requirements"]) + len(details["missing_semantic_evidence"]) <= 8
    assert all(len(item["label_truncated"]) <= 120 for item in details["scored_requirements"])
    assert all(item["snippet"] is None for item in details["scored_requirements"])
    assert result.score == pytest.approx(50.0)


def test_repeated_scores_and_details_are_identical():
    units = [
        _unit("u-0", "qa", member_queries=None),
        _unit("g-1", "", member_queries=["a", "b"], match_mode="ALL"),
    ]
    provider = MatrixProvider({"qa": [0.61], "a": [0.72], "b": [0.33]})
    inputs = _inputs(units, [_chunk()])

    first = RequirementSemanticService().score(inputs, provider)
    second = RequirementSemanticService().score(inputs, provider)

    assert first.score == second.score
    assert first.q_by_unit_id == second.q_by_unit_id
    assert first.details == second.details
