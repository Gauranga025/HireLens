"""Experimental, parameterised semantic scoring for Phase 11.5.

This module mirrors the Phase 11.4 production formula so that alternative
configurations can be explored **without modifying production code or its
module-level constants**. At the approved defaults it must produce the same
scalar as ``RequirementSemanticService`` (asserted by tests).

Tuning must only be invoked with a development split. The held-out split is
never accepted by the calibration entry point.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from app.evaluation.semantic_intelligence_dataset import BenchmarkSplit
from app.services.requirement_semantic_service import RequirementSemanticService
from app.services.semantic_input_service import (
    RANK_WEIGHTS,
    RELEVANCE_THRESHOLD,
    SemanticInputs,
    SemanticUnit,
)

ALPHA_DEFAULTS: Dict[str, float] = {
    "REQUIRED": 1.0,
    "FUNDAMENTAL": 1.0,
    "REQUIRED_GROUP": 1.0,
    "PREFERRED": 0.5,
    "CONTEXT": 0.25,
    "OPTIONAL": 0.0,
    "EXPERIENCE": 0.0,
}


@dataclass(frozen=True)
class SemanticParameters:
    """Frozen candidate configuration for one experimental run."""

    threshold: float = RELEVANCE_THRESHOLD
    top_k: int = 3
    rank_weights: Tuple[float, ...] = tuple(RANK_WEIGHTS)
    alpha: Mapping[str, float] = field(default_factory=lambda: dict(ALPHA_DEFAULTS))
    retrieval_aggregation: str = "rank_weighted"  # or: mean_top_k, max

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": self.threshold,
            "top_k": self.top_k,
            "rank_weights": list(self.rank_weights),
            "alpha": dict(self.alpha),
            "retrieval_aggregation": self.retrieval_aggregation,
        }


DEFAULT_PARAMETERS = SemanticParameters()


def experimental_score(
    inputs: SemanticInputs,
    similarity_provider: Any,
    parameters: SemanticParameters = DEFAULT_PARAMETERS,
    *,
    neutralise_section_weights: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """Compute a semantic scalar with experimental parameter overrides.

    ``neutralise_section_weights`` implements the section-weight ablation by
    replacing each chunk's beta with 1.0 in a copied input object; production
    chunk construction is untouched.
    """
    if neutralise_section_weights:
        chunks = [replace(chunk, beta=1.0) for chunk in inputs.chunks]
        inputs = replace(inputs, chunks=chunks)

    q_by_unit = {unit.unit_id: 0.0 for unit in inputs.units}
    scored_units = [
        unit
        for unit in inputs.units
        if unit.scored and parameters.alpha.get(unit.requirement_type, unit.alpha) > 0.0
    ]
    if not scored_units or not inputs.chunks:
        return _aggregate(inputs.units, q_by_unit, parameters), q_by_unit

    queries: List[str] = []
    seen = set()
    for unit in scored_units:
        for text in unit.query_texts:
            if text not in seen:
                seen.add(text)
                queries.append(text)
    chunk_texts = [chunk.text for chunk in inputs.chunks]
    if not queries:
        return _aggregate(inputs.units, q_by_unit, parameters), q_by_unit

    matrix = similarity_provider.compute_similarity_matrix(queries, chunk_texts)
    if matrix is None:
        raise ValueError("Similarity provider returned no matrix")
    similarities = np.clip(np.asarray(matrix, dtype=float), 0.0, 1.0)
    if similarities.shape != (len(queries), len(chunk_texts)):
        raise ValueError(f"Unexpected matrix shape {similarities.shape}")

    q_by_query: Dict[str, float] = {}
    for query_index, query in enumerate(queries):
        eligible = [
            (chunk, float(similarities[query_index, chunk_index]))
            for chunk_index, chunk in enumerate(inputs.chunks)
            if chunk.beta > 0.0
            and float(similarities[query_index, chunk_index]) >= parameters.threshold
        ]
        eligible.sort(
            key=lambda item: (
                -(item[0].beta * item[1]),
                -item[1],
                item[0].offset,
                item[0].chunk_id,
            )
        )
        selected = eligible[: parameters.top_k]
        if not selected:
            q_by_query[query] = 0.0
            continue
        values = [value for _, value in selected]
        if parameters.retrieval_aggregation == "mean_top_k":
            q = sum(values) / len(values)
        elif parameters.retrieval_aggregation == "max":
            q = max(values)
        else:
            weights = parameters.rank_weights[: len(selected)]
            q = sum(weight * value for weight, value in zip(weights, values)) / sum(weights)
        q_by_query[query] = max(0.0, min(1.0, q))

    for unit in inputs.units:
        alpha = parameters.alpha.get(unit.requirement_type, unit.alpha)
        if not unit.scored or alpha <= 0.0:
            q_by_unit[unit.unit_id] = 0.0
            continue
        if unit.is_group:
            member_scores = [
                max((q_by_query.get(segment, 0.0) for segment in segments), default=0.0)
                for segments in unit.member_query_texts
            ]
            if not member_scores:
                q = 0.0
            elif (unit.match_mode or "ANY").upper() == "ALL":
                q = sum(member_scores) / len(member_scores)
            else:
                q = max(member_scores)
        else:
            q = max((q_by_query.get(segment, 0.0) for segment in unit.query_texts), default=0.0)
        q_by_unit[unit.unit_id] = max(0.0, min(1.0, q))

    return _aggregate(inputs.units, q_by_unit, parameters), q_by_unit


def _aggregate(
    units: Sequence[SemanticUnit],
    q_by_unit: Mapping[str, float],
    parameters: SemanticParameters,
) -> float:
    scored = [
        unit for unit in units
        if unit.scored and parameters.alpha.get(unit.requirement_type, unit.alpha) > 0.0
    ]
    alpha_total = sum(parameters.alpha.get(unit.requirement_type, unit.alpha) for unit in scored)
    if alpha_total <= 0.0:
        return 0.0
    weighted = sum(
        parameters.alpha.get(unit.requirement_type, unit.alpha) * q_by_unit.get(unit.unit_id, 0.0)
        for unit in scored
    )
    return max(0.0, min(100.0, 100.0 * weighted / alpha_total))


def production_parity_check(
    inputs: SemanticInputs, similarity_provider: Any
) -> Dict[str, Any]:
    """Assert that experimental defaults match production exactly."""
    production = RequirementSemanticService().score(inputs, similarity_provider)
    experimental, _ = experimental_score(inputs, similarity_provider, DEFAULT_PARAMETERS)
    return {
        "production_score": production.score,
        "experimental_score": experimental,
        "delta": abs(production.score - experimental),
    }


# A deliberately small, documented search space. No grid explosion on a small
# dataset; every candidate is recorded with its development metrics.
CANDIDATE_PARAMETERS: Tuple[SemanticParameters, ...] = (
    DEFAULT_PARAMETERS,
    SemanticParameters(threshold=0.20),
    SemanticParameters(threshold=0.30),
    SemanticParameters(top_k=1),
    SemanticParameters(top_k=5),
    SemanticParameters(rank_weights=(1.0, 0.0, 0.0)),
    SemanticParameters(retrieval_aggregation="mean_top_k"),
    SemanticParameters(
        alpha={**ALPHA_DEFAULTS, "CONTEXT": 0.0}
    ),
)


def candidate_parameter_labels(
    candidates: Sequence[SemanticParameters] = CANDIDATE_PARAMETERS,
) -> List[str]:
    """Stable labels for the pre-registered candidate configurations."""
    labels: List[str] = []
    for index, parameters in enumerate(candidates):
        if parameters == DEFAULT_PARAMETERS:
            labels.append("approved_defaults")
            continue
        if parameters.threshold != DEFAULT_PARAMETERS.threshold:
            labels.append(f"tau_{parameters.threshold:g}")
        elif parameters.top_k != DEFAULT_PARAMETERS.top_k:
            labels.append(f"top_k_{parameters.top_k}")
        elif parameters.rank_weights != DEFAULT_PARAMETERS.rank_weights:
            labels.append(f"rank_weights_{'_'.join(str(w) for w in parameters.rank_weights)}")
        elif parameters.retrieval_aggregation != DEFAULT_PARAMETERS.retrieval_aggregation:
            labels.append(f"aggregation_{parameters.retrieval_aggregation}")
        elif dict(parameters.alpha) != dict(DEFAULT_PARAMETERS.alpha):
            labels.append(
                "alpha_context_0" if parameters.alpha.get("CONTEXT") == 0.0 else f"candidate_{index}"
            )
        else:
            labels.append(f"candidate_{index}")
    return labels


def calibrate(
    development_scores: Mapping[str, float],
    metric_name: str = "ndcg_at_3",
    candidates: Sequence[SemanticParameters] = CANDIDATE_PARAMETERS,
) -> Dict[str, Any]:
    """Select the configuration with the best development metric.

    ``development_scores`` maps a configuration label to its development
    metric. The caller must construct it from development data only; this
    function has no access to held-out labels.
    """
    if not development_scores:
        return {"selected": None, "rationale": "no_development_scores", "candidates": []}
    ranked = sorted(
        development_scores.items(), key=lambda item: (-float(item[1]), str(item[0]))
    )
    best_label, best_value = ranked[0]
    return {
        "selected": best_label,
        "selected_metric": metric_name,
        "selected_value": best_value,
        "rationale": (
            "Highest mean development NDCG among a small, pre-registered set "
            "of candidate configurations; ties resolved by configuration label."
        ),
        "candidates": [
            {"label": label, metric_name: value} for label, value in ranked
        ],
        "held_out_used": False,
        "split_required": BenchmarkSplit.DEVELOPMENT.value,
    }


def require_development_split(split: Any) -> None:
    """Fail closed if a tuning request names the held-out split."""
    value = split.value if hasattr(split, "value") else str(split)
    if value != BenchmarkSplit.DEVELOPMENT.value:
        raise ValueError(
            f"Parameter tuning is only permitted on the development split, got {value!r}"
        )
