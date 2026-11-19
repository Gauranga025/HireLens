"""Reproducible baseline-vs-Phase-11.4 ranking evaluation runner.

The baseline is forced onto the original whole-document semantic API, while
the proposed system uses the actual production ``ScoringService`` with the
real ``SemanticMatchingService``. Both receive byte-identical inputs and the
same human grades. Failed evaluations are recorded, never dropped.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from app.evaluation.annotation_schema import (
    BINARY_RELEVANCE_THRESHOLD,
    MRR_TARGET_GRADE,
    LabelledBenchmark,
    consensus_grade,
    require_valid,
)
from app.evaluation.semantic_calibration import (
    ALPHA_DEFAULTS,
    DEFAULT_PARAMETERS,
    SemanticParameters,
    experimental_score,
)
from app.evaluation.semantic_intelligence_dataset import LabelledPair
from app.evaluation.semantic_metrics import ranking_metrics
from app.services.scoring_service import ScoringConfig, ScoringService
from app.services.semantic_input_service import build_semantic_inputs
from app.services.semantic_matching_service import SemanticMatchingService

EVALUATION_SCHEMA_VERSION = "phase11_5_evaluation_v1"

BASELINE_SYSTEM = "baseline_whole_document"
PROPOSED_SYSTEM = "phase11_4_requirement_chunk"


class _DocumentLevelSemanticAdapter:
    """Expose only the pre-Phase-11.4 document-level semantic API."""

    def __init__(self, delegate: SemanticMatchingService):
        self._delegate = delegate

    def is_available(self) -> bool:
        return self._delegate.is_available()

    def get_error_info(self):
        return self._delegate.get_error_info()

    def compute_similarity(self, text1: str, text2: str):
        return self._delegate.compute_similarity(text1, text2)


@dataclass(frozen=True)
class EvaluationRecord:
    jd_id: str
    candidate_id: str
    role_category: str
    grade: int
    system: str
    score_kind: str
    semantic_score: Optional[float]
    overall_score: Optional[float]
    status: str
    error_type: str = ""
    resume_length_chars: int = 0
    requirement_types: Tuple[str, ...] = ()
    strata: Tuple[str, ...] = ()
    semantic_status: str = ""


def _common_kwargs(pair: LabelledPair) -> Dict[str, Any]:
    """Return the exact same scoring inputs for every evaluated system."""
    return {
        "resume_text": pair.resume_text,
        "job_text": pair.job_text,
        "resume_skills": list(pair.resume_skills),
        "required_skills": list(pair.required_skills),
        "preferred_skills": list(pair.preferred_skills),
        "use_semantic": True,
        "experience_metadata": list(pair.experience_metadata),
        "project_metadata": list(pair.project_metadata),
        "structured_requirements": list(pair.structured_requirements),
    }


def benchmark_pairs(benchmark: LabelledBenchmark) -> Tuple[List[LabelledPair], List[Dict[str, str]]]:
    """Convert human annotations into scorer-ready pairs and label failures."""
    jobs = {job.jd_id: job for job in benchmark.jobs}
    resumes = {resume.candidate_id: resume for resume in benchmark.resumes}
    pairs: List[LabelledPair] = []
    failures: List[Dict[str, str]] = []
    for jd_id, candidate_id in benchmark.pairs:
        grade = consensus_grade(benchmark.annotations_for(jd_id, candidate_id))
        job = jobs.get(jd_id)
        resume = resumes.get(candidate_id)
        if grade is None:
            failures.append({
                "jd_id": jd_id,
                "candidate_id": candidate_id,
                "reason": "unresolved_label",
            })
            continue
        if job is None or resume is None:
            failures.append({
                "jd_id": jd_id,
                "candidate_id": candidate_id,
                "reason": "missing_job_or_resume",
            })
            continue
        pairs.append(
            LabelledPair(
                pair_id=f"{jd_id}:{candidate_id}",
                jd_id=jd_id,
                role_category=job.role_category,
                candidate_id=candidate_id,
                job_text=job.job_text,
                resume_text=resume.resume_text,
                required_skills=list(job.required_skills),
                preferred_skills=list(job.preferred_skills),
                grade=int(grade),
                rationale="; ".join(
                    ann.rationale for ann in benchmark.annotations_for(jd_id, candidate_id)
                    if ann.rationale.strip()
                ),
                structured_requirements=[dict(req) for req in job.structured_requirements],
                experience_metadata=[dict(item) for item in resume.experience_metadata],
                project_metadata=[dict(item) for item in resume.project_metadata],
                candidate_identity_key=resume.identity_key,
                strata=list(resume.strata),
                reviewer_grades={
                    ann.reviewer_id: int(ann.grade)
                    for ann in benchmark.annotations_for(jd_id, candidate_id)
                },
                resume_skills=list(resume.resume_skills),
            )
        )
    return pairs, failures


def _safe_score(service: ScoringService, kwargs: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        result = service.compute_match(**dict(kwargs))
        semantic = result.get("semantic_score")
        overall = result.get("overall_score")
        strategy = result.get("scoring_strategy") or {}
        details = strategy.get("semantic_details") or {}
        semantic_status = str(details.get("retrieval_status") or strategy.get("semantic_status") or "")
        status = "ok"
        error_type = ""
    except Exception as exc:  # record failures rather than excluding them
        semantic = None
        overall = None
        semantic_status = ""
        status = "failed"
        error_type = type(exc).__name__
    return {
        "semantic_score": None if semantic is None else float(semantic),
        "overall_score": None if overall is None else float(overall),
        "semantic_status": semantic_status,
        "status": status,
        "error_type": error_type,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }


def evaluate_benchmark(
    benchmark: LabelledBenchmark,
    *,
    allow_real_model: bool = True,
    include_ablations: bool = True,
) -> Dict[str, Any]:
    """Evaluate all systems on identical inputs and return structured results."""
    require_valid(benchmark)
    pairs, label_failures = benchmark_pairs(benchmark)
    empty_result = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "status": "no_labelled_benchmark" if benchmark.is_empty else "real_model_not_enabled",
        "records": [],
        "failures": label_failures,
        "per_jd": {},
        "human_grades": {},
        "performance": {},
        "systems": [BASELINE_SYSTEM, PROPOSED_SYSTEM],
    }
    if benchmark.is_empty or not pairs:
        return empty_result
    if not allow_real_model:
        return empty_result

    semantic_service = SemanticMatchingService()
    config = ScoringConfig()
    baseline_service = ScoringService(
        config=config, semantic_service=_DocumentLevelSemanticAdapter(semantic_service)
    )
    proposed_service = ScoringService(config=config, semantic_service=semantic_service)

    load_started = time.perf_counter()
    try:
        context = semantic_service.get_model_context()
        model_load_ms = (time.perf_counter() - load_started) * 1000.0
        model_error = ""
    except Exception as exc:
        context = None
        model_load_ms = (time.perf_counter() - load_started) * 1000.0
        model_error = f"{type(exc).__name__}: {exc}"

    records: List[EvaluationRecord] = []
    failures: List[Dict[str, str]] = list(label_failures)
    per_jd: Dict[str, Dict[str, Any]] = {}
    human_grades: Dict[str, List[int]] = {}
    performance: Dict[str, Any] = {
        "model_load_ms": round(model_load_ms, 3),
        "model_load_error": model_error,
        "model_name": semantic_service.model_name,
        "model_revision": semantic_service._revision_from_model(),
        "max_seq_length": context.get("max_seq_length") if context else None,
        "per_candidate_latency_ms": [],
        "per_jd_batch_latency_ms": {},
        "cache_stats_after": {},
        "embedding_calls": {},
        "scoring_failure_count": 0,
    }

    ablation_configs: Dict[str, SemanticParameters] = {
        "ablation_no_context": SemanticParameters(
            **{**DEFAULT_PARAMETERS.to_dict(), "alpha": {**ALPHA_DEFAULTS, "CONTEXT": 0.0}}
        ),
        "ablation_mean_top_k": SemanticParameters(retrieval_aggregation="mean_top_k"),
    }

    for jd_id in sorted({pair.jd_id for pair in pairs}):
        jd_pairs = [pair for pair in pairs if pair.jd_id == jd_id]
        grades = [int(pair.grade) for pair in jd_pairs]
        human_grades[jd_id] = grades
        jd_metrics: Dict[str, Dict[str, Any]] = {}
        score_vectors: Dict[str, List[Optional[float]]] = {
            f"{BASELINE_SYSTEM}:semantic": [],
            f"{BASELINE_SYSTEM}:overall": [],
            f"{PROPOSED_SYSTEM}:semantic": [],
            f"{PROPOSED_SYSTEM}:overall": [],
        }
        for ablation_name in ablation_configs:
            score_vectors[f"{ablation_name}:semantic"] = []

        batch_started = time.perf_counter()
        for pair in jd_pairs:
            kwargs = _common_kwargs(pair)
            baseline = _safe_score(baseline_service, kwargs)
            proposed = _safe_score(proposed_service, kwargs)
            performance["per_candidate_latency_ms"].extend(
                [
                    {"system": BASELINE_SYSTEM, "jd_id": jd_id, "candidate_id": pair.candidate_id,
                     "latency_ms": round(baseline["latency_ms"], 3)},
                    {"system": PROPOSED_SYSTEM, "jd_id": jd_id, "candidate_id": pair.candidate_id,
                     "latency_ms": round(proposed["latency_ms"], 3)},
                ]
            )
            for system, result in (
                (BASELINE_SYSTEM, baseline),
                (PROPOSED_SYSTEM, proposed),
            ):
                if result["status"] != "ok":
                    performance["scoring_failure_count"] += 1
                    failures.append({
                        "jd_id": jd_id,
                        "candidate_id": pair.candidate_id,
                        "system": system,
                        "reason": result["error_type"],
                    })
                for kind in ("semantic", "overall"):
                    records.append(
                        EvaluationRecord(
                            jd_id=jd_id,
                            candidate_id=pair.candidate_id,
                            role_category=pair.role_category,
                            grade=int(pair.grade),
                            system=system,
                            score_kind=kind,
                            semantic_score=result["semantic_score"],
                            overall_score=result["overall_score"],
                            status=result["status"],
                            error_type=result["error_type"],
                            resume_length_chars=len(pair.resume_text),
                            requirement_types=tuple(
                                sorted({
                                    str(req.get("requirement_type", ""))
                                    for req in pair.structured_requirements
                                    if req.get("requirement_type")
                                })
                            ),
                            strata=tuple(pair.strata),
                            semantic_status=result["semantic_status"],
                        )
                    )
            score_vectors[f"{BASELINE_SYSTEM}:semantic"].append(baseline["semantic_score"])
            score_vectors[f"{BASELINE_SYSTEM}:overall"].append(baseline["overall_score"])
            score_vectors[f"{PROPOSED_SYSTEM}:semantic"].append(proposed["semantic_score"])
            score_vectors[f"{PROPOSED_SYSTEM}:overall"].append(proposed["overall_score"])

            if include_ablations and context is not None:
                for ablation_name, parameters in ablation_configs.items():
                    try:
                        inputs = build_semantic_inputs(
                            pair.job_text,
                            pair.resume_text,
                            pair.structured_requirements,
                            context["tokenizer"],
                            context["max_seq_length"],
                        )
                        if ablation_name == "ablation_no_context":
                            from dataclasses import replace
                            inputs = replace(
                                inputs,
                                units=[
                                    (
                                        replace(unit, alpha=0.0, scored=False)
                                        if unit.kind == "context"
                                        else unit
                                    )
                                    for unit in inputs.units
                                ],
                            )
                        score, _ = experimental_score(inputs, semantic_service, parameters)
                        score_vectors[f"{ablation_name}:semantic"].append(float(score))
                    except Exception as exc:
                        score_vectors[f"{ablation_name}:semantic"].append(None)
                        failures.append({
                            "jd_id": jd_id,
                            "candidate_id": pair.candidate_id,
                            "system": ablation_name,
                            "reason": type(exc).__name__,
                        })

        performance["per_jd_batch_latency_ms"][jd_id] = round(
            (time.perf_counter() - batch_started) * 1000.0, 3
        )
        for key, scores in score_vectors.items():
            jd_metrics[key] = ranking_metrics(
                grades,
                scores,
                relevance_threshold=BINARY_RELEVANCE_THRESHOLD,
                mrr_target_grade=MRR_TARGET_GRADE,
            )
        per_jd[jd_id] = jd_metrics

    stats = semantic_service.get_cache_stats()
    performance["cache_stats_after"] = stats
    performance["embedding_calls"] = {
        kind: {
            "hits": values.get("hits", 0),
            "misses": values.get("misses", 0),
            "evictions": values.get("evictions", 0),
            "size": values.get("size", 0),
        }
        for kind, values in stats.items()
    }

    return {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "status": "measured",
        "records": [asdict(record) for record in records],
        "failures": failures,
        "per_jd": per_jd,
        "human_grades": human_grades,
        "performance": performance,
        "systems": [BASELINE_SYSTEM, PROPOSED_SYSTEM] + list(ablation_configs),
        "metric_config": {
            "binary_relevance_threshold": BINARY_RELEVANCE_THRESHOLD,
            "mrr_target_grade": MRR_TARGET_GRADE,
            "gain": "2**grade - 1",
        },
        "parameters_at_evaluation": DEFAULT_PARAMETERS.to_dict(),
    }
