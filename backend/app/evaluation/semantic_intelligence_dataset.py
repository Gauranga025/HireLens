"""Labelled benchmark schema for Phase 11.4 semantic intelligence.

This module intentionally contains **no benchmark examples and no results**.
It defines the frozen schema, rubric, pilot targets, expansion gate, and
JD-level split rules needed before a benchmark can be measured. External
labelled data must be supplied explicitly via ``load_benchmark_dataset``.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


RUBRIC_VERSION = "phase11_4_relevance_v1"
DATASET_SCHEMA_VERSION = "phase11_4_benchmark_v1"

PILOT_ROLE_CATEGORIES: Tuple[str, ...] = (
    "backend",
    "frontend",
    "data_ml",
    "devops_cloud",
    "mixed_paraphrase",
)
PILOT_JDS_PER_CATEGORY = 1
PILOT_PAIRS_PER_JD = 12
PILOT_TARGET_PAIRS = len(PILOT_ROLE_CATEGORIES) * PILOT_PAIRS_PER_JD

EXPANSION_MIN_JDS = 20
EXPANSION_MAX_JDS = 30
MIN_HELD_OUT_JDS_FOR_GENERAL_CLAIMS = 6
MIN_TOTAL_JDS_FOR_GENERAL_CLAIMS = EXPANSION_MIN_JDS
MIN_HELD_OUT_JDS_PER_ROLE = 2


class RelevanceGrade(IntEnum):
    """Graded relevance rubric; higher is better."""

    NOT_RELEVANT = 0
    WEAKLY_RELEVANT = 1
    PARTIALLY_RELEVANT = 2
    HIGHLY_RELEVANT = 3


RELEVANCE_RUBRIC: Dict[int, str] = {
    int(RelevanceGrade.HIGHLY_RELEVANT): (
        "Satisfies nearly all required skills with demonstrated "
        "experience/projects; preferred skills are a bonus."
    ),
    int(RelevanceGrade.PARTIALLY_RELEVANT): (
        "Satisfies core stack but has partial evidence, missing preferred "
        "skills, or one important gap."
    ),
    int(RelevanceGrade.WEAKLY_RELEVANT): (
        "Adjacent domain or generic similarity; multiple key requirements missing."
    ),
    int(RelevanceGrade.NOT_RELEVANT): (
        "Different role/no required stack; boilerplate-only or misleading text."
    ),
}


class BenchmarkSplit(str, Enum):
    DEVELOPMENT = "development"
    HELD_OUT = "held_out"


class BenchmarkStratum(str, Enum):
    NORMAL_LENGTH = "normal_length"
    LONG_RESUME = "long_resume"
    PARAPHRASE = "paraphrase"
    BOILERPLATE = "boilerplate"
    MISSING_REQUIREMENT = "missing_requirement"
    RELATED_TECHNOLOGY = "related_technology"
    GROUP_ANY = "group_any"
    GROUP_ALL = "group_all"
    TOKEN_BOUNDARY = "token_boundary"


@dataclass(frozen=True)
class LabelledPair:
    """One manually labelled JD/resume pair."""

    pair_id: str
    jd_id: str
    role_category: str
    candidate_id: str
    job_text: str
    resume_text: str
    required_skills: List[str]
    grade: int
    rationale: str
    preferred_skills: List[str] = field(default_factory=list)
    structured_requirements: List[Dict[str, Any]] = field(default_factory=list)
    experience_metadata: List[Dict[str, Any]] = field(default_factory=list)
    project_metadata: List[Dict[str, Any]] = field(default_factory=list)
    candidate_identity_key: Optional[str] = None
    strata: List[str] = field(default_factory=list)
    reviewer_grades: Dict[str, int] = field(default_factory=dict)
    split: Optional[str] = None
    # Phase 11.5: the candidate's own extracted skills. This is deliberately
    # distinct from ``required_skills`` so non-semantic scoring components are
    # not accidentally given perfect lexical coverage for every candidate.
    resume_skills: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkDataset:
    """A labelled benchmark with provenance and split metadata."""

    name: str
    pairs: Tuple[LabelledPair, ...] = ()
    rubric_version: str = RUBRIC_VERSION
    schema_version: str = DATASET_SCHEMA_VERSION
    split_version: Optional[str] = None
    reviewers: Tuple[str, ...] = ()
    notes: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.pairs

    @property
    def jd_ids(self) -> List[str]:
        return sorted({pair.jd_id for pair in self.pairs})

    @property
    def role_categories(self) -> List[str]:
        return sorted({pair.role_category for pair in self.pairs})

    def filtered(self, jd_ids: Iterable[str]) -> "BenchmarkDataset":
        allowed = set(jd_ids)
        return BenchmarkDataset(
            name=self.name,
            pairs=tuple(pair for pair in self.pairs if pair.jd_id in allowed),
            rubric_version=self.rubric_version,
            schema_version=self.schema_version,
            split_version=self.split_version,
            reviewers=self.reviewers,
            notes=self.notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["pairs"] = [pair.to_dict() for pair in self.pairs]
        return payload


def empty_pilot_dataset() -> BenchmarkDataset:
    """Return the documented 60-pair pilot *template* with zero examples."""
    return BenchmarkDataset(
        name="phase11_4_pilot_template",
        pairs=(),
        rubric_version=RUBRIC_VERSION,
        schema_version=DATASET_SCHEMA_VERSION,
        split_version=None,
        reviewers=(),
        notes=(
            "Template only. Target: 5 JDs x 12 resumes = 60 labelled pairs. "
            "No labelled examples or results are included in source control."
        ),
    )


def pilot_target_manifest() -> Dict[str, Any]:
    """Describe the exploratory pilot without fabricating labels or results."""
    return {
        "name": "phase11_4_pilot_target",
        "status": "not_collected",
        "role_categories": list(PILOT_ROLE_CATEGORIES),
        "jds_per_category": PILOT_JDS_PER_CATEGORY,
        "pairs_per_jd": PILOT_PAIRS_PER_JD,
        "target_pairs": PILOT_TARGET_PAIRS,
        "labelled_pairs": 0,
        "results": None,
        "claim_permitted": False,
        "rubric_version": RUBRIC_VERSION,
    }


def expansion_target_manifest() -> Dict[str, Any]:
    """Describe the held-out gate for general ranking-accuracy claims."""
    return {
        "status": "target_only",
        "min_distinct_jds": EXPANSION_MIN_JDS,
        "max_distinct_jds": EXPANSION_MAX_JDS,
        "candidate_resumes_per_jd": "8-12",
        "development_target": 16,
        "held_out_target": 8,
        "minimum_held_out_jds_for_general_claims": MIN_HELD_OUT_JDS_FOR_GENERAL_CLAIMS,
        "minimum_total_jds_for_general_claims": MIN_TOTAL_JDS_FOR_GENERAL_CLAIMS,
        "minimum_held_out_jds_per_role": MIN_HELD_OUT_JDS_PER_ROLE,
        "results": None,
    }


def _read_records(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, Mapping) and "pairs" in payload:
        return list(payload["pairs"])
    if isinstance(payload, list):
        return list(payload)
    raise ValueError("Benchmark JSON must be a list of pairs or contain a 'pairs' key.")


def load_benchmark_dataset(path: str | Path) -> BenchmarkDataset:
    """Load an externally supplied labelled benchmark file."""
    dataset_path = Path(path)
    records = _read_records(dataset_path)
    pairs = tuple(LabelledPair(**record) for record in records)
    dataset = BenchmarkDataset(
        name=dataset_path.stem,
        pairs=pairs,
        rubric_version=RUBRIC_VERSION,
        schema_version=DATASET_SCHEMA_VERSION,
        notes=f"Loaded from {dataset_path}",
    )
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: BenchmarkDataset) -> None:
    """Validate labels, identifiers, and split hygiene."""
    pair_ids = [pair.pair_id for pair in dataset.pairs]
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("Duplicate pair_id values are not allowed.")

    for pair in dataset.pairs:
        if pair.grade not in [int(grade) for grade in RelevanceGrade]:
            raise ValueError(f"Invalid grade for pair {pair.pair_id}: {pair.grade}")
        if not pair.job_text.strip() or not pair.resume_text.strip():
            raise ValueError(f"Pair {pair.pair_id} is missing job/resume text.")
        if not pair.rationale.strip():
            raise ValueError(f"Pair {pair.pair_id} is missing a label rationale.")
        if pair.split not in (None, *[split.value for split in BenchmarkSplit]):
            raise ValueError(f"Invalid split for pair {pair.pair_id}: {pair.split}")

    pairs_by_jd: Dict[str, set] = defaultdict(set)
    for pair in dataset.pairs:
        pairs_by_jd[pair.jd_id].add(pair.split)
    for jd_id, splits in pairs_by_jd.items():
        if None not in splits and len(splits) > 1:
            raise ValueError(f"JD {jd_id} is split across development and held-out.")

    pairs_by_candidate: Dict[str, set] = defaultdict(set)
    for pair in dataset.pairs:
        key = pair.candidate_identity_key or pair.candidate_id
        pairs_by_candidate[key].add(pair.split)
    for candidate, splits in pairs_by_candidate.items():
        if None not in splits and len(splits) > 1:
            raise ValueError(
                f"Candidate {candidate} appears in both development and held-out splits."
            )


def assign_jd_splits(
    dataset: BenchmarkDataset,
    held_out_count: Optional[int] = None,
) -> Dict[str, str]:
    """Assign JDs to held-out using deterministic stratified selection.

    JDs are sorted by identifier within each role category; approximately
    every third JD is assigned to held-out until ``held_out_count`` is met.
    Candidates appearing in multiple JDs are kept entirely on the held-out
    side to prevent candidate leakage.
    """
    assignment: Dict[str, str] = {}
    for role in sorted({pair.role_category for pair in dataset.pairs}):
        jd_ids = sorted(
            {pair.jd_id for pair in dataset.pairs if pair.role_category == role}
        )
        for index, jd_id in enumerate(jd_ids):
            assignment[jd_id] = (
                BenchmarkSplit.HELD_OUT.value
                if index % 3 == 2
                else BenchmarkSplit.DEVELOPMENT.value
            )

    if held_out_count is not None:
        ranked = sorted(
            assignment,
            key=lambda jd_id: (
                assignment[jd_id] != BenchmarkSplit.HELD_OUT.value,
                jd_id,
            ),
        )
        desired = max(0, min(held_out_count, len(ranked)))
        for jd_id in ranked[desired:]:
            assignment[jd_id] = BenchmarkSplit.DEVELOPMENT.value
        for jd_id in ranked[:desired]:
            assignment[jd_id] = BenchmarkSplit.HELD_OUT.value

    candidate_jds: Dict[str, List[str]] = defaultdict(list)
    for pair in dataset.pairs:
        key = pair.candidate_identity_key or pair.candidate_id
        candidate_jds[key].append(pair.jd_id)
    for jd_ids in candidate_jds.values():
        if any(assignment[jd_id] == BenchmarkSplit.HELD_OUT.value for jd_id in jd_ids):
            for jd_id in jd_ids:
                assignment[jd_id] = BenchmarkSplit.HELD_OUT.value

    return assignment


def apply_split(
    dataset: BenchmarkDataset,
    assignment: Mapping[str, str],
    split: BenchmarkSplit,
) -> BenchmarkDataset:
    """Return the pairs belonging to one frozen JD split."""
    selected_ids = {
        jd_id for jd_id, value in assignment.items() if value == split.value
    }
    pairs = tuple(
        LabelledPair(**{**pair.to_dict(), "split": split.value})
        for pair in dataset.pairs
        if pair.jd_id in selected_ids
    )
    return BenchmarkDataset(
        name=f"{dataset.name}:{split.value}",
        pairs=pairs,
        rubric_version=dataset.rubric_version,
        schema_version=dataset.schema_version,
        split_version=dataset.split_version,
        reviewers=dataset.reviewers,
        notes=dataset.notes,
    )


def label_counts(dataset: BenchmarkDataset) -> Dict[str, int]:
    """Count labels by grade name."""
    counts = Counter(int(pair.grade) for pair in dataset.pairs)
    return {
        RelevanceGrade(grade).name.lower(): counts.get(grade, 0)
        for grade in RelevanceGrade
    }


def cohens_kappa(dataset: BenchmarkDataset) -> Optional[float]:
    """Compute two-reviewer agreement when exactly two ratings are complete."""
    ratings: List[Tuple[int, int]] = []
    for pair in dataset.pairs:
        if len(pair.reviewer_grades) != 2:
            return None
        values = sorted(pair.reviewer_grades.items())
        ratings.append((int(values[0][1]), int(values[1][1])))
    if not ratings:
        return None

    n = len(ratings)
    observed = sum(1 for first, second in ratings if first == second) / n
    first_counts = Counter(first for first, _ in ratings)
    second_counts = Counter(second for _, second in ratings)
    expected = sum(
        (first_counts[grade] / n) * (second_counts[grade] / n)
        for grade in RelevanceGrade
    )
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def general_claim_gate(
    dataset: BenchmarkDataset,
    split: BenchmarkSplit,
    ndcg_improvement_lower_bound: Optional[float] = None,
) -> Dict[str, Any]:
    """Report whether held-out evidence is sufficient for a broad claim."""
    held_out_jds = {
        pair.jd_id for pair in dataset.pairs if pair.split == split.value
    }
    role_counts: Dict[str, set] = defaultdict(set)
    for pair in dataset.pairs:
        if pair.split == split.value:
            role_counts[pair.role_category].add(pair.jd_id)

    all_jds = set(dataset.jd_ids)
    reasons: List[str] = []
    if len(held_out_jds) < MIN_HELD_OUT_JDS_FOR_GENERAL_CLAIMS:
        reasons.append("too_few_held_out_jds")
    if len(all_jds) < MIN_TOTAL_JDS_FOR_GENERAL_CLAIMS:
        reasons.append("too_few_total_jds")
    if any(
        len(jds) < MIN_HELD_OUT_JDS_PER_ROLE for jds in role_counts.values()
    ):
        reasons.append("role_category_too_sparse")
    if ndcg_improvement_lower_bound is None or ndcg_improvement_lower_bound <= 0.0:
        reasons.append("confidence_interval_not_positive")
    if cohens_kappa(dataset) is None:
        reasons.append("reviewer_agreement_unavailable")

    return {
        "permitted": not reasons,
        "reasons": reasons,
        "held_out_jd_count": len(held_out_jds),
        "total_jd_count": len(all_jds),
        "held_out_jds_by_role": {
            role: len(jds) for role, jds in sorted(role_counts.items())
        },
    }
