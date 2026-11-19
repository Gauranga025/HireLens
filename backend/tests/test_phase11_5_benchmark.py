"""Phase 11.5 framework tests.

All data in this file is synthetic and exists only to verify schema, split,
metric, isolation, determinism, and pipeline correctness. It is not benchmark
evidence and must never be reported as a ranking-quality result.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import replace
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pytest

from app.evaluation.annotation_schema import (
    ANNOTATION_SCHEMA_VERSION,
    AnnotationRecord,
    JobRecord,
    LabelledBenchmark,
    ResumeRecord,
    agreement_summary,
    build_annotation_template,
    cohens_kappa,
    consensus_grade,
    disagreement_summary,
    krippendorff_alpha,
    require_valid,
    tuning_readiness,
    validate_benchmark,
)
from app.evaluation.semantic_benchmark import (
    BASELINE_SYSTEM,
    PROPOSED_SYSTEM,
    _common_kwargs,
    evaluate_benchmark,
)
from app.evaluation.semantic_calibration import (
    CANDIDATE_PARAMETERS,
    DEFAULT_PARAMETERS,
    calibrate,
    candidate_parameter_labels,
    experimental_score,
    production_parity_check,
    require_development_split,
)
from app.evaluation.semantic_dataset_split import (
    apply_benchmark_split,
    claim_gate,
    freeze_splits,
    validate_split,
)
from app.evaluation.semantic_intelligence_dataset import LabelledPair
from app.evaluation.semantic_metrics import (
    average_ties,
    describe,
    kendall_tau_b,
    ndcg_at_k,
    paired_bootstrap_ci,
    precision_at_k,
    ranking_metrics,
    recall_at_k,
)
from app.services.scoring_service import ScoringConfig, ScoringService
from app.services.semantic_input_service import build_semantic_inputs
from scripts.analyze_semantic_errors import analyze_report
from scripts.evaluate_semantic_benchmark import build_report
from scripts.prepare_semantic_benchmark import readiness_report

REVIEWERS = ("reviewer_a", "reviewer_b")
ROLES = ("backend", "frontend", "data_ml")


class WordTokenizer:
    """Minimal deterministic tokenizer for synthetic unit tests only."""

    def __init__(self) -> None:
        self.vocab: Dict[str, int] = {}
        self.inverse: Dict[int, str] = {}

    def _id(self, word: str) -> int:
        if word not in self.vocab:
            token_id = len(self.vocab) + 1
            self.vocab[word] = token_id
            self.inverse[token_id] = word
        return self.vocab[word]

    def __call__(self, text: str, add_special_tokens: bool = True) -> Dict[str, List[int]]:
        return {"input_ids": [self._id(word) for word in text.split()]}

    def decode(self, ids: Sequence[int], skip_special_tokens: bool = True) -> str:
        return " ".join(self.inverse.get(int(token_id), "") for token_id in ids)


class OverlapMatrixProvider:
    """Deterministic cosine-like matrix for synthetic parity tests only."""

    def compute_similarity_matrix(self, queries: Sequence[str], chunks: Sequence[str]) -> np.ndarray:
        rows: List[List[float]] = []
        for query in queries:
            query_words = set(query.lower().split())
            row: List[float] = []
            for chunk in chunks:
                chunk_words = set(chunk.lower().split())
                union = query_words | chunk_words
                row.append(len(query_words & chunk_words) / len(union) if union else 0.0)
            rows.append(row)
        return np.asarray(rows, dtype=float)


def _requirement() -> List[Dict[str, Any]]:
    return [
        {
            "requirement_type": "REQUIRED",
            "data": {"skill": "python fastapi"},
            "original_text": "Required: python fastapi",
        },
        {
            "requirement_type": "PREFERRED",
            "data": {"skill": "aws"},
            "original_text": "Preferred: aws",
        },
        {
            "requirement_type": "REQUIRED_GROUP",
            "data": {
                "skills": [{"skill": "postgres"}, {"skill": "mysql"}],
                "match_mode": "ANY",
                "group_name": "SQL database",
            },
            "original_text": "Required: postgres or mysql",
        },
    ]


def _benchmark(
    jd_count: int = 12,
    pairs_per_jd: int = 2,
    *,
    disagreement: bool = True,
    shared_candidate: bool = False,
) -> LabelledBenchmark:
    jobs: List[JobRecord] = []
    resumes: List[ResumeRecord] = []
    annotations: List[AnnotationRecord] = []
    for index in range(jd_count):
        jd_id = f"jd_{index:03d}"
        role = ROLES[index % len(ROLES)]
        jobs.append(
            JobRecord(
                jd_id=jd_id,
                role_category=role,
                job_text=(
                    f"Synthetic {role} role. Required: python fastapi. "
                    "Preferred: aws. Responsibilities: build and maintain APIs."
                ),
                required_skills=["python", "fastapi"],
                preferred_skills=["aws"],
                structured_requirements=_requirement(),
                stratum="synthetic",
            )
        )
        if not shared_candidate:
            for pair_index in range(pairs_per_jd):
                candidate_id = f"c_{index:03d}_{pair_index}"
                resumes.append(
                    ResumeRecord(
                        candidate_id=candidate_id,
                        resume_text=(
                            "EXPERIENCE\nBuilt synthetic python fastapi services. "
                            "Used postgres and mysql. Deployed on aws."
                        ),
                        resume_skills=["python", "fastapi", "postgres"],
                        identity_key=f"anon_{candidate_id}",
                        strata=["synthetic"],
                    )
                )
    if shared_candidate:
        resumes.append(
            ResumeRecord(
                candidate_id="shared_candidate",
                resume_text=(
                    "EXPERIENCE\nBuilt synthetic python fastapi services. "
                    "Used postgres and mysql. Deployed on aws."
                ),
                resume_skills=["python", "fastapi", "postgres"],
                identity_key="anon_shared",
                strata=["synthetic"],
            )
        )

    # The annotation workbook has one row per JD x candidate pair. Every row
    # is reviewed by every declared reviewer.
    for jd_index, job in enumerate(jobs):
        for resume_index, resume in enumerate(resumes):
            grade = (jd_index + resume_index) % 5
            has_disagreement = (
                disagreement and jd_index == 0 and resume_index == 0
            )
            for reviewer_index, reviewer in enumerate(REVIEWERS):
                reviewer_grade = (
                    (grade + 1) % 5
                    if has_disagreement and reviewer_index == 1
                    else grade
                )
                annotations.append(
                    AnnotationRecord(
                        jd_id=job.jd_id,
                        candidate_id=resume.candidate_id,
                        reviewer_id=reviewer,
                        grade=reviewer_grade,
                        rationale="Synthetic rationale for framework validation only.",
                        strengths=["synthetic python evidence"],
                        missing_qualifications=["synthetic depth evidence"],
                        reviewed_at="2026-11-19T00:00:00Z",
                        adjudication_status="adjudicated" if has_disagreement else "pending",
                        adjudicated_grade=grade if has_disagreement else None,
                        evidence_reference="synthetic-experience-section",
                    )
                )
    return LabelledBenchmark(
        name="synthetic_framework_validation_only",
        jobs=tuple(jobs),
        resumes=tuple(resumes),
        annotations=tuple(annotations),
        reviewers=REVIEWERS,
        notes="Synthetic data; not benchmark evidence.",
    )


def _empty_benchmark() -> LabelledBenchmark:
    return LabelledBenchmark(name="synthetic_empty")


def _write_benchmark(path: Any, benchmark: LabelledBenchmark) -> Any:
    path.write_text(json.dumps(benchmark.to_dict()), encoding="utf-8")
    return path


def _args(tmp_path: Any, **overrides: Any) -> argparse.Namespace:
    values: Dict[str, Any] = {
        "benchmark": str(tmp_path / "benchmark.json"),
        "split": "development",
        "split_file": None,
        "frozen_parameters": None,
        "tune_development": False,
        "freeze_output": None,
        "allow_real_model": False,
        "no_ablations": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


# --- Annotation schema and validation -------------------------------------------------

def test_synthetic_benchmark_is_valid_and_ready() -> None:
    benchmark = _benchmark()
    assert validate_benchmark(benchmark) == []
    assert tuning_readiness(benchmark)["ready"] is True
    assert disagreement_summary(benchmark)["adjudicated_count"] == 1
    assert consensus_grade(benchmark.annotations_for("jd_000", "c_000_0")) == 0


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    [
        (lambda b: replace(b.annotations[1], grade=9), "invalid_grade"),
        (lambda b: replace(b.annotations[1], rationale=""), "missing_rationale"),
        (
            lambda b: replace(b.annotations[1], reviewer_id=b.annotations[0].reviewer_id),
            "conflicting_annotation",
        ),
        (
            lambda b: replace(b.annotations[1], adjudication_status="unknown"),
            "invalid_adjudication_status",
        ),
    ],
)
def test_annotation_validation_rejects_invalid_records(mutator: Any, expected_code: str) -> None:
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    annotations = list(benchmark.annotations)
    annotations[1] = mutator(benchmark)
    broken = replace(benchmark, annotations=tuple(annotations))
    codes = {issue["code"] for issue in validate_benchmark(broken)}
    assert expected_code in codes


def test_missing_label_and_reviewer_completeness_are_detected() -> None:
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    target = (benchmark.jd_ids[0], benchmark.candidate_ids[0])
    without_one = replace(
        benchmark,
        annotations=tuple(
            ann
            for ann in benchmark.annotations
            if (ann.jd_id, ann.candidate_id) != target
        ),
    )
    codes = {issue["code"] for issue in validate_benchmark(without_one)}
    assert "missing_label" in codes

    incomplete = replace(benchmark, annotations=benchmark.annotations[:-1])
    warnings = {
        issue["code"]
        for issue in validate_benchmark(incomplete)
        if issue["severity"] == "warning"
    }
    assert "incomplete_reviewers" in warnings


def test_personal_data_minimization_validation() -> None:
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    resumes = tuple(
        replace(resume, candidate_id="candidate@example.com") if index == 0 else resume
        for index, resume in enumerate(benchmark.resumes)
    )
    annotations = tuple(
        replace(ann, candidate_id="candidate@example.com")
        if ann.candidate_id == benchmark.resumes[0].candidate_id
        else ann
        for ann in benchmark.annotations
    )
    broken = replace(benchmark, resumes=resumes, annotations=annotations)
    codes = {issue["code"] for issue in validate_benchmark(broken)}
    assert "pii_like_identifier" in codes


def test_annotation_template_has_no_labels() -> None:
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    workbook = build_annotation_template(benchmark.jobs, benchmark.resumes, REVIEWERS)
    assert workbook["schema_version"] == ANNOTATION_SCHEMA_VERSION
    assert len(workbook["annotations"]) == 1
    assert all(row["grade"] is None for row in workbook["annotations"])
    assert any("Never use the model under test" in text for text in workbook["instructions"])


def test_reviewer_agreement_metrics_are_supported_only_when_structure_allows() -> None:
    ratings = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
    assert cohens_kappa(ratings) == pytest.approx(1.0)
    assert cohens_kappa(ratings, quadratic=True) == pytest.approx(1.0)
    assert cohens_kappa([(0, 4), (4, 0)]) < 0.0

    benchmark = _benchmark(jd_count=1, pairs_per_jd=5, disagreement=False)
    summary = agreement_summary(benchmark)
    assert summary["reported"] is True
    assert summary["complete_two_reviewer_pairs"] == 5
    assert summary["cohens_kappa"] == pytest.approx(1.0)

    perfect = _benchmark(jd_count=5, pairs_per_jd=5, disagreement=False)
    assert krippendorff_alpha(perfect) == pytest.approx(1.0)


# --- Split freezing and leakage -------------------------------------------------------

def test_split_is_deterministic_and_leakage_free() -> None:
    benchmark = _benchmark()
    first = freeze_splits(benchmark)
    second = freeze_splits(benchmark)
    assert first["split_hash"] == second["split_hash"]
    assert first["jd_assignment"] == second["jd_assignment"]
    assert validate_split(benchmark, first["jd_assignment"]) == []
    assert set(first["jd_assignment"]) == set(benchmark.jd_ids)

    sides: Dict[str, set] = {}
    for ann in benchmark.annotations:
        sides.setdefault(ann.candidate_id, set()).add(
            first["jd_assignment"][ann.jd_id]
        )
    assert all(len(values) == 1 for values in sides.values())


def test_candidate_overlap_forces_all_touched_jds_to_held_out() -> None:
    shared = _benchmark(jd_count=12, pairs_per_jd=1, shared_candidate=True)
    require_valid(shared)
    manifest = freeze_splits(shared)
    assert validate_split(shared, manifest["jd_assignment"]) == []
    assert manifest["candidate_overlap_moves"]
    assert manifest["held_out_jd_count"] == len(shared.jd_ids)
    assert set(manifest["development_jds"]) == set()


def test_apply_split_keeps_each_jd_wholly_on_one_side() -> None:
    benchmark = _benchmark()
    manifest = freeze_splits(benchmark)
    development = apply_benchmark_split(benchmark, manifest["jd_assignment"], "development")
    held_out = apply_benchmark_split(benchmark, manifest["jd_assignment"], "held_out")
    assert not (set(development.jd_ids) & set(held_out.jd_ids))
    assert set(development.jd_ids) | set(held_out.jd_ids) == set(benchmark.jd_ids)
    assert not (set(development.candidate_ids) & set(held_out.candidate_ids))


def test_claim_gate_blocks_small_or_unsupported_benchmarks() -> None:
    benchmark = _benchmark()
    manifest = freeze_splits(benchmark)
    gate = claim_gate(benchmark, manifest["jd_assignment"], 0.01, reviewer_agreement_reported=True)
    assert gate["permitted"] is False
    assert "too_few_total_jds" in gate["reasons"]


# --- Ranking metrics -------------------------------------------------------------------

def test_ndcg_and_binary_metric_edge_cases() -> None:
    grades = [4, 3, 2, 1, 0]
    assert ndcg_at_k(grades, [5, 4, 3, 2, 1], 3) == pytest.approx(1.0)
    assert ndcg_at_k(grades, [1, 2, 3, 4, 5], 3) < 1.0
    assert ndcg_at_k([0, 0, 0], [3, 2, 1], 3) == 0.0
    assert ndcg_at_k([], [], 3) == 0.0
    assert precision_at_k([3, 3, 0, 0], [4, 3, 2, 1], 2, threshold=2) == 1.0
    assert recall_at_k([3, 3, 0, 0], [4, 3, 2, 1], 2, threshold=2) == 1.0
    assert precision_at_k([3, 3, 0, 0], [4, 3, 2, 1], 5, threshold=2) == 0.4
    assert recall_at_k([0, 0, 0], [3, 2, 1], 3, threshold=2) == 0.0


def test_ties_missing_candidates_and_correlation_metrics() -> None:
    assert average_ties([1, 1, 2]) == [1.5, 1.5, 3.0]
    metrics = ranking_metrics([4, 3, 2, 1], [4.0, None, 2.0, 1.0])
    assert metrics["missing_score_count"] == 1
    assert metrics["ordered_candidate_indices"][-1] == 1
    assert metrics["ndcg_at_3"] <= 1.0
    assert kendall_tau_b([1, 1, 1], [1, 2, 3]) is None
    assert kendall_tau_b([3, 2, 1], [3, 2, 1]) == pytest.approx(1.0)


def test_bootstrap_and_describe_are_deterministic() -> None:
    baseline = {"a": {"ndcg_at_3": 0.4}, "b": {"ndcg_at_3": 0.5}, "c": {"ndcg_at_3": 0.6}}
    proposed = {"a": {"ndcg_at_3": 0.45}, "b": {"ndcg_at_3": 0.55}, "c": {"ndcg_at_3": 0.65}}
    first = paired_bootstrap_ci(baseline, proposed, samples=128, seed=7)
    second = paired_bootstrap_ci(baseline, proposed, samples=128, seed=7)
    assert first == second
    assert first["lower"] <= first["observed_mean"] <= first["upper"]
    stats = describe([0.1, 0.2, 0.3, 0.4])
    assert stats["count"] == 4
    assert stats["mean"] == pytest.approx(0.25)
    assert stats["ci_lower"] < stats["ci_upper"]


# --- Experimental scorer parity and calibration ---------------------------------------

def test_experimental_defaults_match_production_scorer() -> None:
    tokenizer = WordTokenizer()
    inputs = build_semantic_inputs(
        "Required: python fastapi. Preferred: aws. Responsibilities: build APIs.",
        "EXPERIENCE\nBuilt python fastapi services with postgres and mysql on aws.",
        _requirement(),
        tokenizer,
        256,
    )
    parity = production_parity_check(inputs, OverlapMatrixProvider())
    assert parity["delta"] == pytest.approx(0.0)


def test_ablation_configuration_preserves_non_context_units() -> None:
    tokenizer = WordTokenizer()
    inputs = build_semantic_inputs(
        "Required: python fastapi. Preferred: aws.",
        "EXPERIENCE\nBuilt python fastapi services with postgres on aws.",
        _requirement(),
        tokenizer,
        256,
    )
    before = len(inputs.units)
    no_context = replace(
        inputs,
        units=[
            replace(unit, alpha=0.0, scored=False) if unit.kind == "context" else unit
            for unit in inputs.units
        ],
    )
    assert len(no_context.units) == before
    assert sum(1 for unit in no_context.units if unit.kind == "context" and unit.scored) == 0


def test_parameter_selection_is_reproducible_and_development_only() -> None:
    with pytest.raises(ValueError):
        require_development_split("held_out")
    scores = {"approved_defaults": 0.51, "tau_0.2": 0.55, "top_k_1": 0.49}
    first = calibrate(scores)
    second = calibrate(scores)
    assert first == second
    assert first["selected"] == "tau_0.2"
    assert first["held_out_used"] is False
    labels = candidate_parameter_labels(CANDIDATE_PARAMETERS)
    assert labels[0] == "approved_defaults"
    assert len(set(labels)) == len(labels)


# --- Evaluation pipeline ---------------------------------------------------------------

def _install_fake_scoring(monkeypatch: Any, calls: List[Dict[str, Any]]) -> None:
    def fake_compute_match(self: Any, **kwargs: Any) -> Dict[str, Any]:
        calls.append(dict(kwargs))
        seed = float(len(kwargs["resume_text"]) % 17)
        semantic = 40.0 + seed
        return {
            "overall_score": 50.0 + seed,
            "semantic_score": semantic,
            "scoring_strategy": {
                "semantic_details": {"retrieval_status": "matched"},
                "semantic_status": "used",
            },
        }

    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.ScoringService.compute_match",
        fake_compute_match,
    )
    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.SemanticMatchingService.get_model_context",
        lambda self: {"tokenizer": WordTokenizer(), "max_seq_length": 256},
    )
    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.SemanticMatchingService.get_cache_stats",
        lambda self: {},
    )
    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.SemanticMatchingService._revision_from_model",
        lambda self: "synthetic_revision",
    )


def test_common_kwargs_are_identical_for_both_systems() -> None:
    pair = LabelledPair(
        pair_id="synthetic:pair",
        jd_id="jd_synthetic",
        role_category="backend",
        candidate_id="c_synthetic",
        job_text="Synthetic job",
        resume_text="Synthetic resume",
        required_skills=["python"],
        grade=3,
        rationale="Synthetic rationale",
        preferred_skills=["aws"],
        resume_skills=["python"],
    )
    first = _common_kwargs(pair)
    second = _common_kwargs(pair)
    assert first == second
    assert first["resume_skills"] == ["python"]
    assert first["required_skills"] == ["python"]


def test_evaluate_benchmark_uses_identical_inputs_and_is_deterministic(monkeypatch: Any) -> None:
    calls: List[Dict[str, Any]] = []
    _install_fake_scoring(monkeypatch, calls)
    benchmark = _benchmark(jd_count=2, pairs_per_jd=1)
    first = evaluate_benchmark(benchmark, allow_real_model=True, include_ablations=False)
    second = evaluate_benchmark(benchmark, allow_real_model=True, include_ablations=False)
    assert first["status"] == "measured"
    assert first["records"] == second["records"]
    assert first["per_jd"] == second["per_jd"]
    assert len(calls) == 16
    for index in range(0, len(calls), 2):
        assert calls[index] == calls[index + 1]


def test_evaluation_records_scoring_failures(monkeypatch: Any) -> None:
    def failing_compute(self: Any, **kwargs: Any) -> Dict[str, Any]:
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.ScoringService.compute_match",
        failing_compute,
    )
    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.SemanticMatchingService.get_model_context",
        lambda self: {"tokenizer": WordTokenizer(), "max_seq_length": 256},
    )
    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.SemanticMatchingService.get_cache_stats",
        lambda self: {},
    )
    monkeypatch.setattr(
        "app.evaluation.semantic_benchmark.SemanticMatchingService._revision_from_model",
        lambda self: "synthetic_revision",
    )
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    result = evaluate_benchmark(benchmark, allow_real_model=True, include_ablations=False)
    assert all(record["status"] == "failed" for record in result["records"])
    assert result["performance"]["scoring_failure_count"] == 2
    assert len(result["failures"]) >= 2


def test_real_model_flag_is_required() -> None:
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    result = evaluate_benchmark(benchmark, allow_real_model=False, include_ablations=False)
    assert result["status"] == "real_model_not_enabled"
    assert result["records"] == []


class _LegacyFake:
    def __init__(self) -> None:
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def get_error_info(self) -> Dict[str, str]:
        return {}

    def compute_similarity(self, text1: str, text2: str) -> float:
        self.calls += 1
        return 0.5


class _ModernFake:
    def __init__(self) -> None:
        self.document_calls = 0

    def is_available(self) -> bool:
        return True

    def get_error_info(self) -> Dict[str, str]:
        return {}

    def get_model_context(self) -> Dict[str, Any]:
        return {"tokenizer": WordTokenizer(), "max_seq_length": 256}

    def compute_similarity_matrix(self, queries: Sequence[str], chunks: Sequence[str]) -> np.ndarray:
        return np.ones((len(queries), len(chunks)), dtype=float)

    def compute_similarity(self, text1: str, text2: str) -> float:
        self.document_calls += 1
        raise AssertionError("Modern path must not call document-level similarity")


def test_baseline_and_production_paths_are_isolated() -> None:
    kwargs = dict(
        resume_text="EXPERIENCE\nBuilt python fastapi services with postgres.",
        job_text="Required: python fastapi. Preferred: aws.",
        resume_skills=["python", "fastapi"],
        required_skills=["python", "fastapi"],
        preferred_skills=["aws"],
        use_semantic=True,
        experience_metadata=[],
        project_metadata=[],
        structured_requirements=_requirement(),
    )
    legacy = _LegacyFake()
    legacy_result = ScoringService(semantic_service=legacy).compute_match(**kwargs)
    assert legacy.calls == 1
    assert legacy_result["scoring_strategy"]["semantic_details"] is None

    modern = _ModernFake()
    modern_result = ScoringService(semantic_service=modern).compute_match(**kwargs)
    assert modern.document_calls == 0
    assert modern_result["scoring_strategy"]["semantic_details"] is not None
    assert modern_result["scoring_strategy"]["semantic_details"]["retrieval_status"] == "matched"


def test_production_weights_are_unchanged() -> None:
    config = ScoringConfig()
    assert (
        config.required_skill_weight,
        config.preferred_skill_weight,
        config.semantic_weight,
        config.evidence_weight,
        config.tfidf_weight,
    ) == (0.35, 0.15, 0.30, 0.20, 0.0)


# --- CLI/report fail-closed behaviour --------------------------------------------------

def test_prepare_and_evaluate_block_without_real_labels(tmp_path: Any) -> None:
    benchmark = _empty_benchmark()
    assert readiness_report(benchmark)["status"] == "blocked_no_labelled_data"
    path = _write_benchmark(tmp_path / "benchmark.json", benchmark)
    report = build_report(_args(tmp_path, benchmark=str(path)))
    assert report["status"] == "blocked_no_labelled_data"
    assert report["accuracy_claim"] == "not_permitted"
    assert report["metrics"] is None


def test_held_out_evaluation_requires_frozen_parameters(tmp_path: Any) -> None:
    benchmark = _benchmark(jd_count=12, pairs_per_jd=1)
    path = _write_benchmark(tmp_path / "benchmark.json", benchmark)
    report = build_report(
        _args(
            tmp_path,
            benchmark=str(path),
            split="held_out",
            allow_real_model=True,
        )
    )
    assert report["status"] == "blocked_parameters_not_frozen"
    assert report["metrics"] is None
    assert report["accuracy_claim"] == "not_permitted"


def test_invalid_benchmark_blocks_evaluation(tmp_path: Any) -> None:
    benchmark = _benchmark(jd_count=1, pairs_per_jd=1)
    invalid = replace(benchmark, annotations=(replace(benchmark.annotations[0], grade=99),))
    path = _write_benchmark(tmp_path / "benchmark.json", invalid)
    report = build_report(_args(tmp_path, benchmark=str(path), allow_real_model=True))
    assert report["status"] == "blocked_validation"
    assert report["accuracy_claim"] == "not_permitted"


# --- Error analysis --------------------------------------------------------------------

def test_error_analysis_is_blocked_without_measurements() -> None:
    analysis = analyze_report({"status": "blocked_no_labelled_data"})
    assert analysis["status"] == "blocked"
    assert analysis["finding_count"] == 0


def test_error_analysis_groups_synthetic_findings() -> None:
    candidates = [f"anon_{index}" for index in range(6)]
    grades = [3, 3, 1, 1, 0, 0]
    semantic = [10.0, 20.0, 95.0, 90.0, 80.0, 70.0]
    overall = [60.0, 55.0, 50.0, 45.0, 40.0, 35.0]
    records: List[Dict[str, Any]] = []
    for system, scores in (
        (BASELINE_SYSTEM, semantic),
        (PROPOSED_SYSTEM, semantic),
    ):
        for kind, values in (("semantic", scores), ("overall", overall)):
            for candidate_id, grade, value in zip(candidates, grades, values):
                records.append(
                    {
                        "jd_id": "jd_synthetic",
                        "candidate_id": candidate_id,
                        "role_category": "backend",
                        "grade": grade,
                        "system": system,
                        "score_kind": kind,
                        "semantic_score": value if kind == "semantic" else None,
                        "overall_score": value if kind == "overall" else None,
                        "status": "ok",
                        "error_type": "",
                        "resume_length_chars": 9000,
                        "requirement_types": ["REQUIRED_GROUP"],
                        "strata": ["boilerplate"],
                        "semantic_status": "matched",
                    }
                )
    analysis = analyze_report({"status": "measured", "records": records})
    assert analysis["status"] == "analyzed"
    assert analysis["finding_count"] > 0
    assert "relevant_candidate_ranked_too_low" in analysis["by_category"]
    assert "irrelevant_candidate_ranked_too_high" in analysis["by_category"]
    assert "long" in str(analysis["by_resume_length"])
    assert "REQUIRED_GROUP" in str(analysis["by_requirement_type"])
