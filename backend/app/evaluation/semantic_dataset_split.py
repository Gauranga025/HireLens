"""Deterministic, leakage-aware JD-level split freezing for Phase 11.5.

The split is defined by a stable hash of the JD identifier and a fixed seed,
so it can be reproduced without inspecting labels or rankings. Candidate
overlap is resolved conservatively by moving every JD touched by a shared
candidate to the held-out side.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from app.evaluation.annotation_schema import (
    LabelledBenchmark,
    require_valid,
)

SPLIT_ALGORITHM_VERSION = "phase11_5_jd_hash_split_v1"
SPLIT_SEED = 20261119
DEVELOPMENT = "development"
HELD_OUT = "held_out"
MIN_PILOT_JDS = 12
TARGET_HELD_OUT_JDS = 6
TARGET_TOTAL_JDS = 20


def dataset_hash(benchmark: LabelledBenchmark) -> str:
    """Return a stable hash of the frozen human-authored dataset content."""
    payload = json.dumps(
        benchmark.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _jd_sort_key(jd_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}|{jd_id}".encode("utf-8")).hexdigest()


def _candidate_key(jd_id: str, candidate_id: str) -> str:
    return f"{jd_id}::{candidate_id}"


def freeze_splits(
    benchmark: LabelledBenchmark, *, seed: int = SPLIT_SEED
) -> Dict[str, Any]:
    """Create a frozen, deterministic JD-level development/held-out split."""
    require_valid(benchmark)
    jobs = {job.jd_id: job for job in benchmark.jobs}
    all_jd_ids = sorted(jobs)
    assignment: Dict[str, str] = {jd_id: DEVELOPMENT for jd_id in all_jd_ids}
    warnings: List[str] = []

    if len(all_jd_ids) < MIN_PILOT_JDS:
        warnings.append(
            f"only_{len(all_jd_ids)}_distinct_jds_pilot_or_development_only"
        )
    else:
        roles: Dict[str, List[str]] = {}
        for jd_id in all_jd_ids:
            roles.setdefault(jobs[jd_id].role_category, []).append(jd_id)
        for role, jd_ids in sorted(roles.items()):
            ordered = sorted(jd_ids, key=lambda jd_id: _jd_sort_key(jd_id, seed))
            held_out_count = len(ordered) // 3
            if held_out_count < 1 and len(ordered) >= 3:
                held_out_count = 1
            for jd_id in ordered[:held_out_count]:
                assignment[jd_id] = HELD_OUT
            if held_out_count == 0:
                warnings.append(f"role_{role}_too_small_for_held_out")

    # Candidate leakage resolution: any candidate seen on both sides forces all
    # of its JDs to the held-out side. This can increase the held-out count.
    candidate_jds: Dict[str, Set[str]] = {}
    for ann in benchmark.annotations:
        key = ann.candidate_id
        candidate_jds.setdefault(key, set()).add(ann.jd_id)
    moved: List[str] = []
    for candidate_id, jd_ids in sorted(candidate_jds.items()):
        sides = {assignment[jd_id] for jd_id in jd_ids if jd_id in assignment}
        if len(sides) > 1:
            for jd_id in sorted(jd_ids):
                if assignment.get(jd_id) == DEVELOPMENT:
                    assignment[jd_id] = HELD_OUT
                    moved.append(f"{jd_id}:{candidate_id}")
    if moved:
        warnings.append(f"candidate_overlap_moved_{len(moved)}_jd_candidate_pairs_to_held_out")

    held_out_jds = sorted(jd_id for jd_id, value in assignment.items() if value == HELD_OUT)
    development_jds = sorted(jd_id for jd_id, value in assignment.items() if value == DEVELOPMENT)
    if len(held_out_jds) < TARGET_HELD_OUT_JDS:
        warnings.append("fewer_than_six_held_out_jds_exploratory_only")
    if len(all_jd_ids) < TARGET_TOTAL_JDS:
        warnings.append("fewer_than_twenty_total_jds_general_claim_not_supported")

    role_counts: Dict[str, Dict[str, int]] = {}
    for role in sorted({job.role_category for job in benchmark.jobs}):
        role_counts[role] = {
            "development": sum(
                1 for jd_id in development_jds if jobs[jd_id].role_category == role
            ),
            "held_out": sum(
                1 for jd_id in held_out_jds if jobs[jd_id].role_category == role
            ),
        }

    manifest: Dict[str, Any] = {
        "split_algorithm": SPLIT_ALGORITHM_VERSION,
        "seed": seed,
        "dataset_hash": dataset_hash(benchmark),
        "jd_assignment": assignment,
        "development_jd_count": len(development_jds),
        "held_out_jd_count": len(held_out_jds),
        "development_jds": development_jds,
        "held_out_jds": held_out_jds,
        "held_out_jds_by_role": {
            role: counts["held_out"] for role, counts in role_counts.items()
        },
        "role_counts": role_counts,
        "candidate_overlap_moves": moved,
        "warnings": warnings,
    }
    payload = json.dumps(
        {
            "split_algorithm": manifest["split_algorithm"],
            "seed": manifest["seed"],
            "dataset_hash": manifest["dataset_hash"],
            "jd_assignment": assignment,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    manifest["split_hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return manifest


def validate_split(
    benchmark: LabelledBenchmark, assignment: Mapping[str, str]
) -> List[str]:
    """Validate a split manifest; an empty list means the split is safe."""
    errors: List[str] = []
    job_ids = {job.jd_id for job in benchmark.jobs}
    unknown = sorted(set(assignment) - job_ids)
    if unknown:
        errors.append(f"unknown_jds_in_split: {unknown}")
    missing = sorted(job_ids - set(assignment))
    if missing:
        errors.append(f"unassigned_jds: {missing}")
    invalid = sorted(
        jd_id for jd_id, value in assignment.items() if value not in (DEVELOPMENT, HELD_OUT)
    )
    if invalid:
        errors.append(f"invalid_split_values: {invalid}")

    candidate_sides: Dict[str, Set[str]] = {}
    for ann in benchmark.annotations:
        if ann.jd_id not in assignment:
            continue
        candidate_sides.setdefault(ann.candidate_id, set()).add(assignment[ann.jd_id])
    leaked = sorted(
        candidate for candidate, sides in candidate_sides.items() if len(sides) > 1
    )
    if leaked:
        errors.append(f"candidate_leakage: {leaked}")

    missing_labels = sorted(
        f"{ann.jd_id}:{ann.candidate_id}"
        for ann in benchmark.annotations
        if ann.jd_id not in assignment
    )
    if missing_labels:
        errors.extend(f"annotation_outside_split: {value}" for value in missing_labels)
    return errors


def apply_benchmark_split(
    benchmark: LabelledBenchmark, assignment: Mapping[str, str], split: str
) -> LabelledBenchmark:
    """Return a benchmark restricted to one frozen split."""
    if split not in (DEVELOPMENT, HELD_OUT):
        raise ValueError(f"Unknown split: {split!r}")
    errors = validate_split(benchmark, assignment)
    if errors:
        raise ValueError("; ".join(errors[:5]))
    selected_jds = {jd_id for jd_id, value in assignment.items() if value == split}
    selected_pairs = {
        (ann.jd_id, ann.candidate_id)
        for ann in benchmark.annotations
        if ann.jd_id in selected_jds
    }
    selected_candidates = {candidate_id for _, candidate_id in selected_pairs}
    return replace(
        benchmark,
        jobs=tuple(job for job in benchmark.jobs if job.jd_id in selected_jds),
        resumes=tuple(
            resume for resume in benchmark.resumes if resume.candidate_id in selected_candidates
        ),
        annotations=tuple(
            ann
            for ann in benchmark.annotations
            if (ann.jd_id, ann.candidate_id) in selected_pairs
        ),
        notes=f"{benchmark.notes} | split={split}".strip(" |"),
    )


def claim_gate(
    benchmark: LabelledBenchmark,
    assignment: Mapping[str, str],
    bootstrap_lower_bound: Optional[float],
    *,
    reviewer_agreement_reported: bool = False,
    scoring_failures: int = 0,
) -> Dict[str, Any]:
    """Report whether a general held-out ranking-quality claim is permitted."""
    errors = validate_split(benchmark, assignment)
    held_out_jds = sorted(
        jd_id for jd_id, value in assignment.items() if value == HELD_OUT
    )
    roles: Dict[str, Set[str]] = {}
    jobs = {job.jd_id: job for job in benchmark.jobs}
    for jd_id in held_out_jds:
        job = jobs.get(jd_id)
        if job is not None:
            roles.setdefault(job.role_category, set()).add(jd_id)
    reasons: List[str] = []
    if errors:
        reasons.append("invalid_split")
    if len(held_out_jds) < TARGET_HELD_OUT_JDS:
        reasons.append("too_few_held_out_jds")
    if len(jobs) < TARGET_TOTAL_JDS:
        reasons.append("too_few_total_jds")
    if any(len(jds) < 2 for jds in roles.values()):
        reasons.append("sparse_role_categories")
    if bootstrap_lower_bound is None or bootstrap_lower_bound <= 0.0:
        reasons.append("bootstrap_lower_bound_not_positive")
    if not reviewer_agreement_reported:
        reasons.append("reviewer_agreement_unavailable")
    if scoring_failures:
        reasons.append("scoring_failures_present")
    return {
        "permitted": not reasons,
        "reasons": reasons,
        "held_out_jd_count": len(held_out_jds),
        "total_jd_count": len(jobs),
        "held_out_jds_by_role": {
            role: len(jds) for role, jds in sorted(roles.items())
        },
        "validation_errors": errors,
    }
