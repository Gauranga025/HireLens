"""Requirement-to-chunk semantic scoring for Phase 11.4.

The scorer consumes only verified inputs from ``SemanticInputService`` and
never writes back to Phase 11.3 coverage, evidence, group, or status outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.services.semantic_input_service import (
    MAX_METADATA_TEXT_CHARS,
    MAX_SEMANTIC_DIAGNOSTICS,
    RANK_WEIGHTS,
    RELEVANCE_THRESHOLD,
    SEMANTIC_ALGORITHM,
    TOP_K,
    SemanticInputs,
    SemanticUnit,
)


class SemanticScoringError(RuntimeError):
    """Raised when requirement-to-chunk scoring cannot be trusted."""


@dataclass
class SemanticScoreResult:
    """Scalar score plus bounded, additive diagnostics."""

    score: float
    details: Dict[str, Any]
    q_by_unit_id: Dict[str, float] = field(default_factory=dict)
    retrieval_status: str = "no_relevant_chunks"


def _truncate_label(text: Any) -> str:
    value = str(text or "").strip()
    if len(value) <= MAX_METADATA_TEXT_CHARS:
        return value
    return value[: MAX_METADATA_TEXT_CHARS - 1] + "\u2026"


def aggregate_unit_scores(
    units: Sequence[SemanticUnit],
    q_by_unit_id: Dict[str, float],
) -> Tuple[float, Dict[str, Any]]:
    """Convert per-unit scores into the final 0-100 semantic scalar."""
    scored_units = [unit for unit in units if unit.scored and unit.alpha > 0.0]
    alpha_total = sum(unit.alpha for unit in scored_units)
    if alpha_total <= 0.0:
        return 0.0, {
            "alpha_total": 0.0,
            "weighted_sum": 0.0,
            "scored_unit_count": 0,
        }

    weighted_sum = sum(
        unit.alpha * float(q_by_unit_id.get(unit.unit_id, 0.0))
        for unit in scored_units
    )
    score = 100.0 * weighted_sum / alpha_total
    score = max(0.0, min(100.0, score))
    return score, {
        "alpha_total": alpha_total,
        "weighted_sum": weighted_sum,
        "scored_unit_count": len(scored_units),
    }


class RequirementSemanticService:
    """Score verified requirement units against verified resume chunks."""

    def score(
        self,
        inputs: SemanticInputs,
        similarity_provider: Any,
    ) -> SemanticScoreResult:
        """Compute the semantic score using batched cosine retrieval."""
        scored_units = [
            unit
            for unit in inputs.units
            if unit.scored and unit.alpha > 0.0
        ]
        q_by_unit_id = {unit.unit_id: 0.0 for unit in inputs.units}

        if not scored_units or not inputs.chunks:
            score, aggregation = aggregate_unit_scores(inputs.units, q_by_unit_id)
            details = self._build_details(
                inputs,
                q_by_unit_id,
                {},
                aggregation,
                retrieval_status="no_relevant_chunks",
            )
            return SemanticScoreResult(
                score=score,
                details=details,
                q_by_unit_id=q_by_unit_id,
                retrieval_status="no_relevant_chunks",
            )

        queries: List[str] = []
        seen_queries = set()
        for unit in scored_units:
            for text in unit.query_texts:
                if text not in seen_queries:
                    seen_queries.add(text)
                    queries.append(text)

        chunk_texts = [chunk.text for chunk in inputs.chunks]
        if not queries:
            score, aggregation = aggregate_unit_scores(inputs.units, q_by_unit_id)
            details = self._build_details(
                inputs,
                q_by_unit_id,
                {},
                aggregation,
                retrieval_status="no_relevant_chunks",
            )
            return SemanticScoreResult(
                score=score,
                details=details,
                q_by_unit_id=q_by_unit_id,
                retrieval_status="no_relevant_chunks",
            )

        try:
            matrix = similarity_provider.compute_similarity_matrix(
                queries, chunk_texts
            )
        except Exception as exc:
            raise SemanticScoringError(str(exc)) from exc
        if matrix is None:
            raise SemanticScoringError("Similarity matrix computation returned no result.")

        try:
            similarities = np.asarray(matrix, dtype=float)
        except (TypeError, ValueError) as exc:
            raise SemanticScoringError("Similarity matrix is not numeric.") from exc
        expected_shape = (len(queries), len(chunk_texts))
        if similarities.shape != expected_shape:
            raise SemanticScoringError(
                f"Similarity matrix shape {similarities.shape} != {expected_shape}."
            )
        similarities = np.clip(similarities, 0.0, 1.0)

        q_by_query: Dict[str, float] = {}
        best_by_query: Dict[str, Tuple[Any, float]] = {}

        for query_index, query in enumerate(queries):
            eligible: List[Tuple[Any, float]] = []
            for chunk_index, chunk in enumerate(inputs.chunks):
                similarity = float(similarities[query_index, chunk_index])
                if chunk.beta > 0.0 and similarity >= RELEVANCE_THRESHOLD:
                    eligible.append((chunk, similarity))

            eligible.sort(
                key=lambda item: (
                    -(item[0].beta * item[1]),
                    -item[1],
                    item[0].offset,
                    item[0].chunk_id,
                )
            )
            selected = eligible[:TOP_K]
            if not selected:
                q_by_query[query] = 0.0
                best_by_query[query] = (None, 0.0)
                continue

            used_weights = RANK_WEIGHTS[: len(selected)]
            numerator = sum(
                float(weight) * similarity
                for weight, (_, similarity) in zip(used_weights, selected)
            )
            q = numerator / sum(used_weights)
            q_by_query[query] = max(0.0, min(1.0, q))
            best_by_query[query] = selected[0]
            if not 0.0 <= q <= 1.0:
                raise SemanticScoringError("Rank-weighted aggregation escaped [0, 1].")

        for unit in inputs.units:
            if not unit.scored or unit.alpha <= 0.0:
                q_by_unit_id[unit.unit_id] = 0.0
                continue

            if unit.is_group:
                member_scores: List[float] = []
                for segments in unit.member_query_texts:
                    segment_scores = [
                        float(q_by_query.get(segment, 0.0)) for segment in segments
                    ]
                    member_scores.append(max(segment_scores, default=0.0))
                if not member_scores:
                    q = 0.0
                elif (unit.match_mode or "ANY").upper() == "ALL":
                    q = sum(member_scores) / len(member_scores)
                else:
                    q = max(member_scores)
            else:
                segment_scores = [
                    float(q_by_query.get(segment, 0.0))
                    for segment in unit.query_texts
                ]
                q = max(segment_scores, default=0.0)

            q_by_unit_id[unit.unit_id] = max(0.0, min(1.0, q))

        score, aggregation = aggregate_unit_scores(inputs.units, q_by_unit_id)
        retrieval_status = (
            "matched"
            if any(q_by_unit_id.get(unit.unit_id, 0.0) > 0.0 for unit in scored_units)
            else "no_relevant_chunks"
        )
        details = self._build_details(
            inputs,
            q_by_unit_id,
            best_by_query,
            aggregation,
            retrieval_status=retrieval_status,
        )
        return SemanticScoreResult(
            score=score,
            details=details,
            q_by_unit_id=q_by_unit_id,
            retrieval_status=retrieval_status,
        )

    def _build_details(
        self,
        inputs: SemanticInputs,
        q_by_unit_id: Dict[str, float],
        best_by_query: Dict[str, Tuple[Any, float]],
        aggregation: Dict[str, Any],
        retrieval_status: str,
    ) -> Dict[str, Any]:
        diagnostics: List[Dict[str, Any]] = []
        for unit in sorted(inputs.units, key=lambda item: item.source_index):
            if not unit.scored or unit.alpha <= 0.0:
                continue
            q = float(q_by_unit_id.get(unit.unit_id, 0.0))
            best_chunk: Any = None
            best_similarity = 0.0
            for query in unit.query_texts:
                candidate = best_by_query.get(query)
                if candidate and candidate[0] is not None and candidate[1] > best_similarity:
                    best_chunk, best_similarity = candidate

            diagnostics.append(
                {
                    "requirement_type": unit.requirement_type,
                    "requirement_kind": unit.kind,
                    "label_truncated": _truncate_label(unit.label or unit.text),
                    "q": round(q, 6),
                    "status": "matched" if q > 0.0 else "missing_semantic_evidence",
                    "importance": round(unit.alpha, 6),
                    "match_mode": unit.match_mode,
                    "member_count": len(unit.member_texts) if unit.is_group else None,
                    "best_section": best_chunk.section_type if best_chunk else None,
                    "best_offset": best_chunk.offset if best_chunk else None,
                    "best_similarity": round(best_similarity, 6),
                    "best_token_count": best_chunk.token_count if best_chunk else None,
                    "chunk_token_count": best_chunk.token_count if best_chunk else None,
                    "snippet": None,
                }
            )

        total_diagnostics = len(diagnostics)
        kept = diagnostics[:MAX_SEMANTIC_DIAGNOSTICS]
        scored = [item for item in kept if item["status"] == "matched"]
        missing = [item for item in kept if item["status"] == "missing_semantic_evidence"]

        return {
            "algorithm": SEMANTIC_ALGORITHM,
            "parameters": {
                "threshold": RELEVANCE_THRESHOLD,
                "top_k": TOP_K,
                "rank_weights": list(RANK_WEIGHTS),
            },
            "requirement_count": total_diagnostics,
            "scored_unit_count": aggregation["scored_unit_count"],
            "diagnostic_count": len(kept),
            "omitted_diagnostic_count": max(
                0, total_diagnostics - MAX_SEMANTIC_DIAGNOSTICS
            ),
            "context_requirement_count": inputs.context_unit_count,
            "retrieval_status": retrieval_status,
            "alpha_total": round(aggregation["alpha_total"], 6),
            "weighted_sum": round(aggregation["weighted_sum"], 6),
            "max_seq_length": inputs.max_seq_length,
            "token_limit": inputs.token_limit,
            "chunk_stats": dict(inputs.chunk_stats),
            "scored_requirements": scored,
            "missing_semantic_evidence": missing,
        }
