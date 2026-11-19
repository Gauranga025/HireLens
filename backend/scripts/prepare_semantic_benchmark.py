"""Prepare and validate a genuine Phase 11.5 human-labelled benchmark.

The script never generates labels. It can create an empty annotation workbook
from human-supplied job/resume records, validate a completed workbook, and
freeze a deterministic JD-level split before any tuning begins.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.annotation_schema import (
    ANNOTATION_SCHEMA_VERSION,
    RUBRIC_VERSION,
    AnnotationRecord,
    JobRecord,
    LabelledBenchmark,
    ResumeRecord,
    agreement_summary,
    build_annotation_template,
    disagreement_summary,
    load_benchmark,
    tuning_readiness,
    validate_benchmark,
)
from app.evaluation.semantic_dataset_split import dataset_hash, freeze_splits, validate_split

DEFAULT_TEMPLATE = Path(__file__).parent.parent / "evaluation" / "datasets" / "annotation_template.json"


def _read_json_records(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("jobs", "resumes", "items", "records"):
            if key in payload:
                return list(payload[key])
    if isinstance(payload, list):
        return list(payload)
    raise ValueError(f"Unsupported record file shape: {path}")


def create_template(args: argparse.Namespace) -> Dict[str, Any]:
    jobs = [JobRecord(**record) for record in _read_json_records(args.jobs)] if args.jobs else []
    resumes = (
        [ResumeRecord(**record) for record in _read_json_records(args.resumes)]
        if args.resumes
        else []
    )
    reviewers = [value.strip() for value in args.reviewers.split(",") if value.strip()]
    workbook = build_annotation_template(jobs, resumes, reviewers)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.force:
        raise FileExistsError(f"Refusing to overwrite {output}; pass --force to replace it.")
    output.write_text(json.dumps(workbook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "status": "template_created",
        "output": str(output),
        "job_count": len(jobs),
        "resume_count": len(resumes),
        "annotation_rows": len(workbook["annotations"]),
        "notes": "All grades are null. Human reviewers must supply every grade.",
    }


def readiness_report(benchmark: LabelledBenchmark) -> Dict[str, Any]:
    issues = validate_benchmark(benchmark)
    readiness = tuning_readiness(benchmark)
    split = freeze_splits(benchmark)
    fatal = [issue for issue in issues if issue["severity"] == "fatal"]
    if benchmark.is_empty:
        status = "blocked_no_labelled_data"
    elif fatal:
        status = "blocked_validation"
    elif not readiness["ready"]:
        status = "blocked_labels_not_frozen"
    else:
        status = "ready_for_parameter_tuning"
    return {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "status": status,
        "dataset_hash": dataset_hash(benchmark),
        "counts": {
            "distinct_jd_count": len(benchmark.jd_ids),
            "resume_count": len(benchmark.candidate_ids),
            "labelled_pair_count": len(benchmark.pairs),
            "annotation_count": len(benchmark.annotations),
            "reviewer_count": len(benchmark.reviewers),
        },
        "validation": {
            "fatal_count": len(fatal),
            "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
            "issues": issues[:50],
        },
        "label_readiness": readiness,
        "disagreements": disagreement_summary(benchmark),
        "agreement": agreement_summary(benchmark),
        "split": split,
        "split_validation_errors": validate_split(benchmark, split["jd_assignment"]),
        "claim_permitted": False,
        "notes": (
            "No accuracy claim is permitted until real human labels are complete, "
            "the split is frozen, parameters are tuned on development only, and a "
            "held-out evaluation is performed."
        ),
    }


def inspect_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    benchmark = load_benchmark(args.benchmark)
    report = readiness_report(benchmark)
    if args.split_output:
        output = Path(args.split_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report["split"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        report["split_output"] = str(output)
    if args.readiness_output:
        output = Path(args.readiness_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        report["readiness_output"] = str(output)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", help="Completed human-labelled benchmark JSON")
    parser.add_argument("--create-template", action="store_true")
    parser.add_argument("--jobs", type=Path, help="Human-supplied anonymized jobs JSON")
    parser.add_argument("--resumes", type=Path, help="Human-supplied anonymized resumes JSON")
    parser.add_argument("--reviewers", default="", help="Comma-separated anonymized reviewer IDs")
    parser.add_argument("--output", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--split-output")
    parser.add_argument("--readiness-output")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.create_template:
        result = create_template(args)
    elif args.benchmark:
        result = inspect_benchmark(args)
    else:
        build_parser().print_help()
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
