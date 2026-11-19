"""Evaluate baseline vs Phase 11.4 ranking quality on a real labelled benchmark.

The script is fail-closed. It refuses to compute or report ranking metrics when
human labels are absent, invalid, unfrozen, or when a held-out request has no
frozen development-selected parameter file.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.annotation_schema import (
    ANNOTATION_SCHEMA_VERSION,
    agreement_summary,
    load_benchmark,
    tuning_readiness,
    validate_benchmark,
)
from app.evaluation.semantic_benchmark import (
    BASELINE_SYSTEM,
    EVALUATION_SCHEMA_VERSION,
    PROPOSED_SYSTEM,
    evaluate_benchmark,
)
from app.evaluation.semantic_calibration import (
    CANDIDATE_PARAMETERS,
    DEFAULT_PARAMETERS,
    SemanticParameters,
    calibrate,
    candidate_parameter_labels,
    experimental_score,
    require_development_split,
)
from app.evaluation.semantic_dataset_split import (
    apply_benchmark_split,
    claim_gate,
    dataset_hash,
    freeze_splits,
    validate_split,
)
from app.evaluation.semantic_intelligence_dataset import expansion_target_manifest, pilot_target_manifest
from app.evaluation.semantic_metrics import describe, paired_bootstrap_ci, ranking_metrics
from app.evaluation.annotation_schema import BINARY_RELEVANCE_THRESHOLD, MRR_TARGET_GRADE
from app.services.semantic_input_service import build_semantic_inputs
from app.services.semantic_matching_service import SemanticMatchingService

DEFAULT_OUTPUT = Path(__file__).parent.parent / "evaluation" / "reports" / "PHASE11_5_EVALUATION_RESULTS.json"
DEVELOPMENT = "development"
HELD_OUT = "held_out"
AGGREGATED_METRICS = (
    "ndcg_at_1",
    "ndcg_at_3",
    "ndcg_at_5",
    "ndcg_at_10",
    "precision_at_3",
    "precision_at_5",
    "recall_at_3",
    "recall_at_5",
    "mrr",
    "spearman",
    "kendall_tau",
)
PAIRED_METRICS = ("ndcg_at_3", "ndcg_at_5", "mrr", "precision_at_3", "recall_at_3")


def _load_json(path: str) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _dependency_versions() -> Dict[str, str]:
    result: Dict[str, str] = {}
    for package in ("numpy", "torch", "sentence-transformers", "pytest", "pytest-asyncio"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "not_installed"
    return result


def _code_version() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout.strip() or "unavailable"
    except Exception:
        return "unavailable"


def _split_manifest(benchmark: Any, args: argparse.Namespace) -> Dict[str, Any]:
    if args.split_file:
        manifest = _load_json(args.split_file)
        if manifest.get("dataset_hash") and manifest["dataset_hash"] != dataset_hash(benchmark):
            raise ValueError("Frozen split does not match the benchmark dataset hash.")
        errors = validate_split(benchmark, manifest.get("jd_assignment", {}))
        if errors:
            raise ValueError("; ".join(errors[:5]))
        return manifest
    return freeze_splits(benchmark)


def _frozen_parameters(path: str) -> Dict[str, Any]:
    payload = _load_json(path)
    config = payload.get("parameters", payload)
    if payload.get("held_out_used") is True:
        raise ValueError("Parameter file records held-out tuning.")
    if payload.get("split_required") not in (None, DEVELOPMENT):
        raise ValueError("Parameter file does not declare development-only tuning.")
    return {
        "selected_label": payload.get("selected_label"),
        "parameters": SemanticParameters(
            threshold=float(config["threshold"]),
            top_k=int(config["top_k"]),
            rank_weights=tuple(float(value) for value in config["rank_weights"]),
            alpha={str(key): float(value) for key, value in config["alpha"].items()},
            retrieval_aggregation=str(
                config.get("retrieval_aggregation", DEFAULT_PARAMETERS.retrieval_aggregation)
            ),
        ).to_dict(),
        "source": path,
    }


def _aggregate_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    per_jd = result.get("per_jd", {})
    systems = [BASELINE_SYSTEM, PROPOSED_SYSTEM]
    for key in per_jd.get(next(iter(per_jd), ""), {}):
        system = key.split(":", 1)[0]
        if system not in systems and system not in systems:
            systems.append(system)
    aggregate: Dict[str, Any] = {}
    for system in systems:
        for score_kind in ("semantic", "overall"):
            key = f"{system}:{score_kind}"
            if not any(key in metrics for metrics in per_jd.values()):
                continue
            aggregate[key] = {
                metric: describe(
                    [metrics.get(key, {}).get(metric) for metrics in per_jd.values()]
                )
                for metric in AGGREGATED_METRICS
            }
    paired: Dict[str, Any] = {}
    for score_kind in ("semantic", "overall"):
        baseline = {
            jd_id: metrics.get(f"{BASELINE_SYSTEM}:{score_kind}", {})
            for jd_id, metrics in per_jd.items()
        }
        proposed = {
            jd_id: metrics.get(f"{PROPOSED_SYSTEM}:{score_kind}", {})
            for jd_id, metrics in per_jd.items()
        }
        paired[score_kind] = {
            metric: paired_bootstrap_ci(baseline, proposed, metric=metric)
            for metric in PAIRED_METRICS
        }
    return {"per_system": aggregate, "paired_bootstrap": paired}


def _development_calibration(
    benchmark: Any,
    assignment: Mapping[str, str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    require_development_split(args.split)
    selected_jds = {
        jd_id for jd_id, value in assignment.items() if value == DEVELOPMENT
    }
    pairs = [
        pair
        for pair in benchmark.pairs
        if pair.jd_id in selected_jds
    ]
    if not pairs:
        return {"status": "blocked_no_development_pairs"}
    if not args.allow_real_model:
        return {"status": "real_model_not_enabled"}

    semantic_service = SemanticMatchingService()
    context = semantic_service.get_model_context()
    labels = candidate_parameter_labels(CANDIDATE_PARAMETERS)
    development_scores: Dict[str, float] = {}
    sensitivity: Dict[str, Dict[str, Any]] = {}
    for label, parameters in zip(labels, CANDIDATE_PARAMETERS):
        per_jd: Dict[str, Dict[str, Any]] = {}
        for jd_id in sorted({pair.jd_id for pair in pairs}):
            jd_pairs = [pair for pair in pairs if pair.jd_id == jd_id]
            grades = [int(pair.grade) for pair in jd_pairs]
            scores: List[float] = []
            for pair in jd_pairs:
                inputs = build_semantic_inputs(
                    pair.job_text,
                    pair.resume_text,
                    pair.structured_requirements,
                    context["tokenizer"],
                    context["max_seq_length"],
                )
                score, _ = experimental_score(inputs, semantic_service, parameters)
                scores.append(float(score))
            per_jd[jd_id] = ranking_metrics(
                grades,
                scores,
                relevance_threshold=BINARY_RELEVANCE_THRESHOLD,
                mrr_target_grade=MRR_TARGET_GRADE,
            )
        ndcg_values = [
            float(metrics["ndcg_at_3"]) for metrics in per_jd.values()
        ]
        mean_ndcg = statistics.fmean(ndcg_values) if ndcg_values else 0.0
        development_scores[label] = mean_ndcg
        sensitivity[label] = {
            "parameters": parameters.to_dict(),
            "mean_ndcg_at_3": mean_ndcg,
            "per_jd": per_jd,
        }
    selection = calibrate(development_scores)
    frozen = {
        "status": "development_parameters_frozen",
        "selected_label": selection["selected"],
        "selection": selection,
        "parameters": sensitivity[selection["selected"]]["parameters"]
        if selection["selected"] in sensitivity
        else DEFAULT_PARAMETERS.to_dict(),
        "split_required": DEVELOPMENT,
        "held_out_used": False,
        "dataset_hash": dataset_hash(benchmark),
        "split_hash": (args.split_file and _load_json(args.split_file).get("split_hash")) or None,
    }
    if args.freeze_output:
        output = Path(args.freeze_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(frozen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        frozen["freeze_output"] = str(output)
    return {
        "status": "development_tuning_completed",
        "development_scores": development_scores,
        "sensitivity": sensitivity,
        "selection": selection,
        "frozen": frozen,
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    benchmark = load_benchmark(args.benchmark)
    issues = validate_benchmark(benchmark)
    fatal = [issue for issue in issues if issue["severity"] == "fatal"]
    base: Dict[str, Any] = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "annotation_schema_version": ANNOTATION_SCHEMA_VERSION,
        "status": "not_started",
        "code_version": _code_version(),
        "dependency_versions": _dependency_versions(),
        "dataset": {
            "name": benchmark.name,
            "hash": dataset_hash(benchmark),
            "reviewers": list(benchmark.reviewers),
            "distinct_jd_count": len(benchmark.jd_ids),
            "resume_count": len(benchmark.candidate_ids),
            "labelled_pair_count": len(benchmark.pairs),
        },
        "validation": {"fatal_count": len(fatal), "issues": issues[:50]},
        "readiness": tuning_readiness(benchmark),
        "agreement": agreement_summary(benchmark),
        "split_requested": args.split,
        "split_source": "file" if args.split_file else "derived",
        "pilot_target": pilot_target_manifest(),
        "expansion_target": expansion_target_manifest(),
        "parameter_candidates": [
            {"label": label, "parameters": parameters.to_dict()}
            for label, parameters in zip(
                candidate_parameter_labels(CANDIDATE_PARAMETERS), CANDIDATE_PARAMETERS
            )
        ],
        "selected_parameters": DEFAULT_PARAMETERS.to_dict(),
        "accuracy_claim": "not_permitted",
        "claim_gate": claim_gate(benchmark, {}, None),
        "metrics": None,
        "records": [],
        "failures": [],
        "performance": {},
    }

    if fatal:
        base["status"] = "blocked_validation"
        base["blocker"] = "fatal_dataset_validation_issues"
        return base
    manifest = _split_manifest(benchmark, args)
    base["split_manifest"] = manifest
    base["claim_gate"] = claim_gate(benchmark, manifest.get("jd_assignment", {}), None)

    if benchmark.is_empty:
        base["status"] = "blocked_no_labelled_data"
        base["blocker"] = "no_genuine_human_labels"
        return base
    if args.split == HELD_OUT and not args.frozen_parameters:
        base["status"] = "blocked_parameters_not_frozen"
        base["blocker"] = "held_out_requires_frozen_development_parameters"
        return base

    selected = apply_benchmark_split(benchmark, manifest["jd_assignment"], args.split)
    base["split_counts"] = {
        "jd_count": len(selected.jd_ids),
        "resume_count": len(selected.candidate_ids),
        "pair_count": len(selected.pairs),
    }

    if args.tune_development:
        tuning = _development_calibration(benchmark, manifest["jd_assignment"], args)
        base["development_tuning"] = tuning
        if tuning.get("status") != "development_tuning_completed":
            base["status"] = tuning.get("status", "blocked_tuning")
            return base
        frozen = tuning["frozen"]
        base["selected_parameters"] = frozen["parameters"]
        base["selected_parameters_label"] = frozen["selected_label"]
        base["status"] = "development_tuning_report"
        return base

    if not args.allow_real_model:
        base["status"] = "real_model_not_enabled"
        base["blocker"] = "pass_--allow_real_model_to_compute_metrics"
        return base

    if args.frozen_parameters:
        frozen = _frozen_parameters(args.frozen_parameters)
        base["selected_parameters"] = frozen["parameters"]
        base["selected_parameters_label"] = frozen["selected_label"]

    try:
        result = evaluate_benchmark(
            selected,
            allow_real_model=True,
            include_ablations=not args.no_ablations,
        )
    except Exception as exc:
        base["status"] = "failed_evaluation"
        base["blocker"] = f"{type(exc).__name__}: {exc}"
        return base
    if result.get("status") != "measured":
        base["status"] = result.get("status", "failed_evaluation")
        base["blocker"] = "evaluation_did_not_produce_metrics"
        return base

    aggregated = _aggregate_result(result)
    bootstrap = aggregated["paired_bootstrap"]["semantic"].get("ndcg_at_3", {})
    lower = bootstrap.get("lower")
    gate = claim_gate(
        benchmark,
        manifest["jd_assignment"],
        lower,
        reviewer_agreement_reported=bool(agreement_summary(benchmark)["reported"]),
        scoring_failures=len(result.get("failures", [])),
    )
    base.update(
        {
            "status": "measured",
            "metrics": aggregated,
            "records": result["records"],
            "failures": result["failures"],
            "performance": result["performance"],
            "metric_config": result["metric_config"],
            "parameters_at_evaluation": result["parameters_at_evaluation"],
            "systems_evaluated": result["systems"],
            "claim_gate": gate,
            "accuracy_claim": "permitted" if gate["permitted"] else "not_permitted",
        }
    )
    if gate["permitted"] and args.split == HELD_OUT:
        base["accuracy_claim"] = "held_out_claim_permitted"
    return base


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True, help="Completed human-labelled benchmark JSON")
    parser.add_argument("--split", choices=(DEVELOPMENT, HELD_OUT), default=DEVELOPMENT)
    parser.add_argument("--split-file", help="Frozen split manifest from prepare_semantic_benchmark.py")
    parser.add_argument("--frozen-parameters", help="Frozen development-selected parameters (required for held-out)")
    parser.add_argument("--tune-development", action="store_true")
    parser.add_argument("--freeze-output", help="Where to write selected development parameters")
    parser.add_argument("--allow-real-model", action="store_true")
    parser.add_argument("--no-ablations", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_report(args)
    except Exception as exc:
        report = {
            "schema_version": EVALUATION_SCHEMA_VERSION,
            "status": "failed_evaluation",
            "blocker": f"{type(exc).__name__}: {exc}",
            "accuracy_claim": "not_permitted",
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "blocker": report.get("blocker"),
                "accuracy_claim": report.get("accuracy_claim"),
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
