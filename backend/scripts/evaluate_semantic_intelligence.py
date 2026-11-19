"""Baseline-vs-proposed ranking evaluation for Phase 11.4.

The script refuses to fabricate results. With no labelled dataset, or without
an explicit ``--allow-real-model`` opt-in, it emits a structured report whose
metrics are ``null`` and whose claim gate is closed.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.evaluation_metrics import RankingMetrics
from app.evaluation.semantic_intelligence_dataset import (
    DATASET_SCHEMA_VERSION,
    MIN_HELD_OUT_JDS_FOR_GENERAL_CLAIMS,
    PILOT_TARGET_PAIRS,
    RUBRIC_VERSION,
    BenchmarkDataset,
    BenchmarkSplit,
    RelevanceGrade,
    assign_jd_splits,
    cohens_kappa,
    empty_pilot_dataset,
    expansion_target_manifest,
    general_claim_gate,
    label_counts,
    load_benchmark_dataset,
    pilot_target_manifest,
)
from app.services.scoring_service import ScoringConfig, ScoringService
from app.services.semantic_matching_service import SemanticMatchingService


class _LegacySemanticAdapter:
    """Expose only the document-level API used by the Phase 11.3 baseline."""

    def __init__(self, delegate: SemanticMatchingService):
        self._delegate = delegate

    def is_available(self) -> bool:
        return self._delegate.is_available()

    def get_error_info(self):
        return self._delegate.get_error_info()

    def compute_similarity(self, text1: str, text2: str):
        return self._delegate.compute_similarity(text1, text2)


def _rank_values(values: Sequence[float]) -> List[float]:
    """Average ranks for ties, ascending (lowest value receives rank 1)."""
    indexed = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while (
            end + 1 < len(indexed)
            and indexed[end + 1][0] == indexed[position][0]
        ):
            end += 1
        average_rank = (position + end) / 2.0 + 1.0
        for cursor in range(position, end + 1):
            ranks[indexed[cursor][1]] = average_rank
        position = end + 1
    return ranks


def _spearman(scores: Sequence[float], labels: Sequence[int]) -> Optional[float]:
    if len(scores) < 2:
        return None
    score_ranks = _rank_values(scores)
    label_ranks = _rank_values(labels)
    mean_score = sum(score_ranks) / len(score_ranks)
    mean_label = sum(label_ranks) / len(label_ranks)
    numerator = sum(
        (score - mean_score) * (label - mean_label)
        for score, label in zip(score_ranks, label_ranks)
    )
    denominator = math.sqrt(
        sum((score - mean_score) ** 2 for score in score_ranks)
        * sum((label - mean_label) ** 2 for label in label_ranks)
    )
    if denominator == 0.0:
        return None
    return numerator / denominator


def ranking_metrics(labels: Sequence[int], scores: Sequence[float]) -> Dict[str, Any]:
    """Compute ranking metrics for one JD with stable pair-index item IDs."""
    if len(labels) != len(scores) or not labels:
        return {}
    item_ids = list(range(len(labels)))
    order = sorted(item_ids, key=lambda item: (-scores[item], item))
    relevant = [
        item for item in order if labels[item] >= int(RelevanceGrade.PARTIALLY_RELEVANT)
    ]
    highly_relevant = [
        item for item in order if labels[item] == int(RelevanceGrade.HIGHLY_RELEVANT)
    ]
    graded = {item: float(labels[item]) for item in item_ids}

    tier_scores: Dict[int, List[float]] = {int(grade): [] for grade in RelevanceGrade}
    for label, score in zip(labels, scores):
        tier_scores[int(label)].append(score)
    tier_means = {
        RelevanceGrade(grade).name.lower(): (
            sum(values) / len(values) if values else None
        )
        for grade, values in tier_scores.items()
    }
    monotonicity_violations = 0
    for lower, upper in zip(list(RelevanceGrade)[:-1], list(RelevanceGrade)[1:]):
        lower_values = tier_scores[int(lower)]
        upper_values = tier_scores[int(upper)]
        if lower_values and upper_values:
            lower_mean = sum(lower_values) / len(lower_values)
            upper_mean = sum(upper_values) / len(upper_values)
            if lower_mean > upper_mean:
                monotonicity_violations += 1

    return {
        "pairs": len(labels),
        "precision_at_3": RankingMetrics.precision_at_k(relevant, order, 3),
        "precision_at_5": RankingMetrics.precision_at_k(relevant, order, 5),
        "recall_at_3": RankingMetrics.recall_at_k(relevant, order, 3),
        "recall_at_5": RankingMetrics.recall_at_k(relevant, order, 5),
        "ndcg_at_3": RankingMetrics.ndcg_at_k(graded, order, 3),
        "ndcg_at_5": RankingMetrics.ndcg_at_k(graded, order, 5),
        "mrr_highly_relevant": RankingMetrics.mean_reciprocal_rank(
            highly_relevant, order
        ),
        "spearman": _spearman(scores, labels),
        "tier_mean_scores": tier_means,
        "monotonicity_violations": monotonicity_violations,
        "ranking": [
            {
                "pair_id": item + 1,
                "score": round(float(scores[item]), 6),
                "grade": int(labels[item]),
            }
            for item in order
        ],
    }


def fixed_parameter_manifest() -> Dict[str, Any]:
    """Return the implementation defaults frozen before any tuning."""
    return {
        "threshold": 0.25,
        "top_k": 3,
        "rank_weights": [1.0, 0.5, 0.25],
        "max_resume_chunks": 64,
        "max_tail_chunks": 8,
        "max_context_requirements": 8,
        "tuning_split": "development_only",
        "held_out_tuning": False,
    }


def _mean(values: Sequence[Optional[float]]) -> Optional[float]:
    numeric = [float(value) for value in values if value is not None]
    return sum(numeric) / len(numeric) if numeric else None


def aggregate_metrics(per_jd: Mapping[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Average per-JD metrics; JDs are the independent evaluation unit."""
    keys = (
        "precision_at_3",
        "precision_at_5",
        "recall_at_3",
        "recall_at_5",
        "ndcg_at_3",
        "ndcg_at_5",
        "mrr_highly_relevant",
        "spearman",
    )
    return {
        "jd_count": len(per_jd),
        "metrics": {
            key: _mean([metrics.get(key) for metrics in per_jd.values()])
            for key in keys
        },
        "monotonicity_violations": sum(
            int(metrics.get("monotonicity_violations", 0))
            for metrics in per_jd.values()
        ),
        "latency_mean_ms": _mean(
            [metrics.get("latency_ms") for metrics in per_jd.values()]
        ),
    }


def role_metrics(
    pairs: Sequence[Any], per_jd: Mapping[str, Dict[str, Any]]
) -> Dict[str, Any]:
    role_jds: Dict[str, set] = {}
    role_pairs: Dict[str, int] = {}
    for pair in pairs:
        role_jds.setdefault(pair.role_category, set()).add(pair.jd_id)
        role_pairs[pair.role_category] = role_pairs.get(pair.role_category, 0) + 1
    return {
        role: {
            "jd_count": len(jds),
            "pair_count": role_pairs[role],
            "metrics": _mean(
                [per_jd.get(jd_id, {}).get("ndcg_at_3") for jd_id in sorted(jds)]
            ),
            "exploratory": len(jds) < 2,
        }
        for role, jds in sorted(role_jds.items())
    }


def strata_metrics(
    pairs: Sequence[Any], per_jd: Mapping[str, Dict[str, Any]]
) -> Dict[str, Any]:
    stratum_jds: Dict[str, set] = {}
    stratum_pairs: Dict[str, int] = {}
    for pair in pairs:
        for stratum in pair.strata or ["unspecified"]:
            stratum_jds.setdefault(stratum, set()).add(pair.jd_id)
            stratum_pairs[stratum] = stratum_pairs.get(stratum, 0) + 1
    return {
        stratum: {
            "jd_count": len(jds),
            "pair_count": stratum_pairs[stratum],
            "mean_ndcg_at_3": _mean(
                [per_jd.get(jd_id, {}).get("ndcg_at_3") for jd_id in sorted(jds)]
            ),
        }
        for stratum, jds in sorted(stratum_jds.items())
    }


def paired_bootstrap_ci(
    baseline: Mapping[str, Dict[str, Any]],
    proposed: Mapping[str, Dict[str, Any]],
    metric: str = "ndcg_at_3",
    samples: int = 1000,
    seed: int = 20261119,
) -> Dict[str, Any]:
    """Paired bootstrap over JDs; returns null bounds when data is absent."""
    jd_ids = sorted(set(baseline) & set(proposed))
    if not jd_ids:
        return {"metric": metric, "lower": None, "upper": None, "jd_count": 0}
    deltas = [
        float(proposed[jd_id].get(metric) or 0.0)
        - float(baseline[jd_id].get(metric) or 0.0)
        for jd_id in jd_ids
    ]
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(samples):
        draws = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        means.append(sum(draws) / len(draws))
    means.sort()
    lower_index = max(0, int(0.025 * len(means)) - 1)
    upper_index = min(len(means) - 1, int(0.975 * len(means)))
    return {
        "metric": metric,
        "lower": means[lower_index],
        "upper": means[upper_index],
        "observed_mean": sum(deltas) / len(deltas),
        "jd_count": len(jd_ids),
    }


def _evaluate_pipeline(
    dataset: BenchmarkDataset, allow_real_model: bool
) -> Tuple[Dict[str, Any], Dict[str, List[float]], Dict[str, List[int]]]:
    per_jd: Dict[str, Dict[str, Any]] = {}
    scores: Dict[str, List[float]] = {}
    labels: Dict[str, List[int]] = {}

    if dataset.is_empty:
        return per_jd, scores, labels
    if not allow_real_model:
        return per_jd, scores, labels

    semantic_service = SemanticMatchingService()
    config = ScoringConfig()
    baseline_service = ScoringService(
        config=config, semantic_service=_LegacySemanticAdapter(semantic_service)
    )
    proposed_service = ScoringService(config=config, semantic_service=semantic_service)

    for jd_id in dataset.jd_ids:
        pairs = [pair for pair in dataset.pairs if pair.jd_id == jd_id]
        baseline_scores: List[float] = []
        proposed_scores: List[float] = []
        common_kwargs = []
        for pair in pairs:
            common_kwargs.append(
                dict(
                    resume_text=pair.resume_text,
                    job_text=pair.job_text,
                    resume_skills=pair.resume_skills,
                    required_skills=pair.required_skills,
                    preferred_skills=pair.preferred_skills,
                    use_semantic=True,
                    experience_metadata=pair.experience_metadata,
                    project_metadata=pair.project_metadata,
                    structured_requirements=pair.structured_requirements,
                )
            )

        baseline_started = time.perf_counter()
        for common in common_kwargs:
            baseline_scores.append(
                float(baseline_service.compute_match(**common)["overall_score"])
            )
        baseline_latency_ms = (time.perf_counter() - baseline_started) * 1000.0

        proposed_started = time.perf_counter()
        for common in common_kwargs:
            proposed_scores.append(
                float(proposed_service.compute_match(**common)["overall_score"])
            )
        proposed_latency_ms = (time.perf_counter() - proposed_started) * 1000.0

        pair_labels = [int(pair.grade) for pair in pairs]
        labels[jd_id] = pair_labels
        per_jd[jd_id] = {
            "baseline": {
                **ranking_metrics(pair_labels, baseline_scores),
                "latency_ms": round(baseline_latency_ms, 3),
            },
            "proposed": {
                **ranking_metrics(pair_labels, proposed_scores),
                "latency_ms": round(proposed_latency_ms, 3),
            },
        }
        scores[jd_id] = proposed_scores

    return per_jd, scores, labels


def build_report(
    dataset: Optional[BenchmarkDataset] = None,
    split: BenchmarkSplit = BenchmarkSplit.HELD_OUT,
    split_assignment: Optional[Mapping[str, str]] = None,
    split_source: str = "derived",
    allow_real_model: bool = False,
) -> Dict[str, Any]:
    """Build a structured evaluation report without inventing data."""
    benchmark = dataset or empty_pilot_dataset()
    caveats = [
        "No accuracy improvement is claimed unless a frozen held-out benchmark supports it.",
        "Pilot-only results are exploratory and cannot support broad claims.",
        "Model revision is unpinned in this phase; cross-environment determinism is not guaranteed.",
        "Latency timings are local measurements only and do not establish a speed improvement.",
    ]

    if benchmark.is_empty:
        return {
            "schema_version": DATASET_SCHEMA_VERSION,
            "status": "no_labelled_benchmark",
            "rubric_version": RUBRIC_VERSION,
            "pilot_target": pilot_target_manifest(),
            "expansion_target": expansion_target_manifest(),
            "parameters": fixed_parameter_manifest(),
            "split": {
                "requested": split.value,
                "source": split_source,
                "jd_assignment": split_assignment or {},
                "rules": [
                    "Split by JD, never by resume within a JD.",
                    "Sort JDs by stable identifier within role category and assign every third JD to held-out.",
                    "Keep candidates appearing in multiple JDs on the same side of the split.",
                    "Freeze the split and rubric before any parameter tuning.",
                ],
            },
            "label_counts": label_counts(benchmark),
            "reviewer_agreement": {"cohens_kappa": None},
            "baseline": None,
            "proposed": None,
            "paired_comparison": None,
            "claim_gate": general_claim_gate(benchmark, split, None),
            "accuracy_claim": "not_permitted",
            "caveats": caveats,
        }

    assignment = dict(split_assignment or assign_jd_splits(benchmark))
    selected = (
        BenchmarkDataset(
            name=f"{benchmark.name}:external_split",
            pairs=tuple(
                pair for pair in benchmark.pairs if assignment.get(pair.jd_id) == split.value
            ),
            rubric_version=benchmark.rubric_version,
            schema_version=benchmark.schema_version,
            split_version=benchmark.split_version,
            reviewers=benchmark.reviewers,
            notes=benchmark.notes,
        )
        if split_assignment is not None
        else _apply_assignment(benchmark, assignment, split)
    )

    if not allow_real_model:
        caveats.append("Real-model evaluation was not enabled; no metrics were computed.")
        return {
            "schema_version": DATASET_SCHEMA_VERSION,
            "status": "real_model_not_enabled",
            "rubric_version": RUBRIC_VERSION,
            "dataset": {
                "name": benchmark.name,
                "jd_count": len(benchmark.jd_ids),
                "pair_count": len(benchmark.pairs),
                "selected_jd_count": len(selected.jd_ids),
                "selected_pair_count": len(selected.pairs),
            },
            "pilot_target": pilot_target_manifest(),
            "expansion_target": expansion_target_manifest(),
            "parameters": fixed_parameter_manifest(),
            "split": {
                "requested": split.value,
                "source": split_source,
                "jd_assignment": assignment,
                "frozen": split_source == "file",
            },
            "label_counts": label_counts(selected),
            "reviewer_agreement": {"cohens_kappa": cohens_kappa(selected)},
            "baseline": None,
            "proposed": None,
            "paired_comparison": None,
            "claim_gate": general_claim_gate(selected, split, None),
            "accuracy_claim": "not_permitted",
            "caveats": caveats,
        }

    per_jd, _, _ = _evaluate_pipeline(selected, allow_real_model=True)
    baseline_by_jd = {jd: values["baseline"] for jd, values in per_jd.items()}
    proposed_by_jd = {jd: values["proposed"] for jd, values in per_jd.items()}
    bootstrap = paired_bootstrap_ci(baseline_by_jd, proposed_by_jd)
    gate = general_claim_gate(selected, split, bootstrap["lower"])

    caveats.append(
        "Paired bootstrap confidence intervals are reported over JDs, not individual resumes."
    )
    if len(selected.jd_ids) < MIN_HELD_OUT_JDS_FOR_GENERAL_CLAIMS:
        caveats.append("Fewer than six held-out JDs; results are exploratory only.")
    if split_source != "file":
        caveats.append("Split was derived at runtime rather than loaded from a frozen file.")

    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "status": "measured",
        "rubric_version": RUBRIC_VERSION,
        "dataset": {
            "name": benchmark.name,
            "jd_count": len(benchmark.jd_ids),
            "pair_count": len(benchmark.pairs),
            "selected_jd_count": len(selected.jd_ids),
            "selected_pair_count": len(selected.pairs),
        },
        "pilot_target": pilot_target_manifest(),
        "expansion_target": expansion_target_manifest(),
        "split": {
            "requested": split.value,
            "source": split_source,
            "jd_assignment": assignment,
            "frozen": split_source == "file",
        },
        "parameters": fixed_parameter_manifest(),
        "label_counts": label_counts(selected),
        "reviewer_agreement": {"cohens_kappa": cohens_kappa(selected)},
        "baseline": {
            "per_jd": baseline_by_jd,
            "aggregate": aggregate_metrics(baseline_by_jd),
            "by_role": role_metrics(selected.pairs, baseline_by_jd),
            "by_stratum": strata_metrics(selected.pairs, baseline_by_jd),
        },
        "proposed": {
            "per_jd": proposed_by_jd,
            "aggregate": aggregate_metrics(proposed_by_jd),
            "by_role": role_metrics(selected.pairs, proposed_by_jd),
            "by_stratum": strata_metrics(selected.pairs, proposed_by_jd),
        },
        "paired_comparison": {
            "ndcg_at_3_bootstrap": bootstrap,
            "precision_at_3_bootstrap": paired_bootstrap_ci(
                baseline_by_jd, proposed_by_jd, metric="precision_at_3"
            ),
        },
        "claim_gate": gate,
        "accuracy_claim": (
            "permitted_but_not_asserted" if gate["permitted"] else "not_permitted"
        ),
        "caveats": caveats,
    }


def _apply_assignment(
    dataset: BenchmarkDataset,
    assignment: Mapping[str, str],
    split: BenchmarkSplit,
) -> BenchmarkDataset:
    from app.evaluation.semantic_intelligence_dataset import apply_split

    return apply_split(dataset, assignment, split)


def write_report(report: Mapping[str, Any], output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", help="Path to external labelled JSON/JSONL dataset")
    parser.add_argument(
        "--split-file",
        help="Optional frozen JSON mapping of jd_id to development/held_out",
    )
    parser.add_argument(
        "--split",
        choices=[split.value for split in BenchmarkSplit],
        default=BenchmarkSplit.HELD_OUT.value,
    )
    parser.add_argument("--held-out-count", type=int, default=None)
    parser.add_argument(
        "--allow-real-model",
        action="store_true",
        help="Explicitly load the configured model and compute measured metrics",
    )
    parser.add_argument(
        "--output",
        default="PHASE11_4_SEMANTIC_EVALUATION_RESULTS.json",
        help="Destination for the JSON report",
    )
    args = parser.parse_args(argv)

    dataset = load_benchmark_dataset(args.dataset) if args.dataset else empty_pilot_dataset()
    split_assignment: Optional[Dict[str, str]] = None
    split_source = "derived"
    if args.split_file:
        split_assignment = {
            str(key): str(value)
            for key, value in json.loads(
                Path(args.split_file).read_text(encoding="utf-8")
            ).items()
        }
        split_source = "file"
    elif not dataset.is_empty:
        split_assignment = assign_jd_splits(dataset, args.held_out_count)

    report = build_report(
        dataset=dataset,
        split=BenchmarkSplit(args.split),
        split_assignment=split_assignment,
        split_source=split_source,
        allow_real_model=args.allow_real_model,
    )
    output_path = write_report(report, args.output)
    print(f"Wrote {output_path} (status={report['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
