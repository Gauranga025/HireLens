"""Phase 11.5 human-annotation schema, rubric and validation.

This module contains **no labelled examples and no results**. It defines the
artifacts a human reviewer team must produce before any ranking-quality claim
can be made. Grades are assigned exclusively by humans; the model under test is
never used to generate or suggest a grade.

Personal data is deliberately minimized: benchmarks store only anonymized
candidate identifiers, reviewer identifiers, and the text needed to score.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ANNOTATION_SCHEMA_VERSION = "phase11_5_annotation_v1"
RUBRIC_VERSION = "phase11_5_relevance_v1"

# Frozen before any evaluation: grades >= this value count as "relevant" for
# binary precision/recall. Changing it after tuning would invalidate results.
BINARY_RELEVANCE_THRESHOLD = 2
# The grade used for Mean Reciprocal Rank (first strong-or-better candidate).
MRR_TARGET_GRADE = 3


class RelevanceGrade5(IntEnum):
    """Ordinal, human-assigned relevance scale."""

    NOT_RELEVANT = 0
    WEAK_MATCH = 1
    PARTIAL_MATCH = 2
    STRONG_MATCH = 3
    EXCELLENT_MATCH = 4


RELEVANCE_RUBRIC: Dict[int, str] = {
    int(RelevanceGrade5.NOT_RELEVANT): (
        "Different role or no required stack. Text is boilerplate, unrelated, "
        "or actively misleading. No evidence that the candidate could perform "
        "the core work."
    ),
    int(RelevanceGrade5.WEAK_MATCH): (
        "Adjacent domain or generic terminology overlap only. Multiple key "
        "requirements are missing and evidence is not demonstrated."
    ),
    int(RelevanceGrade5.PARTIAL_MATCH): (
        "Satisfies the core stack with partial or indirect evidence, or meets "
        "most requirements but has one important gap (e.g. no demonstrated "
        "project for a named skill)."
    ),
    int(RelevanceGrade5.STRONG_MATCH): (
        "Satisfies nearly all required skills with demonstrated experience or "
        "projects. Preferred skills and depth are a bonus but not required."
    ),
    int(RelevanceGrade5.EXCELLENT_MATCH): (
        "Satisfies all required skills with clear, demonstrated, recent "
        "evidence, plus most preferred skills and relevant impact/ownership. "
        "Would be prioritized for immediate interview."
    ),
}

RUBRIC_EXAMPLES: Dict[int, str] = {
    0: "Frontend-only portfolio reviewed against a backend/PostgreSQL role.",
    1: "General 'software engineer' resume with no Python/FastAPI evidence for a Python API role.",
    2: "Python developer with Django but no FastAPI or async API experience for a FastAPI role.",
    3: "Python developer with FastAPI and PostgreSQL projects; missing optional AWS.",
    4: "Python/FastAPI/PostgreSQL engineer with deployed services, tests, and clear ownership.",
}

ADJUDICATION_STATUSES = ("pending", "adjudicated", "waived")


@dataclass(frozen=True)
class JobRecord:
    """An anonymized job description used in the benchmark."""

    jd_id: str
    role_category: str
    job_text: str
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    structured_requirements: List[Dict[str, Any]] = field(default_factory=list)
    stratum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResumeRecord:
    """An anonymized candidate resume used in the benchmark."""

    candidate_id: str
    resume_text: str
    resume_skills: List[str] = field(default_factory=list)
    identity_key: Optional[str] = None
    experience_metadata: List[Dict[str, Any]] = field(default_factory=list)
    project_metadata: List[Dict[str, Any]] = field(default_factory=list)
    strata: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnnotationRecord:
    """One human relevance judgement for one (JD, candidate) pair."""

    jd_id: str
    candidate_id: str
    reviewer_id: str
    grade: int
    rationale: str
    strengths: List[str] = field(default_factory=list)
    missing_qualifications: List[str] = field(default_factory=list)
    reviewed_at: str = ""
    adjudication_status: str = "pending"
    adjudicated_grade: Optional[int] = None
    evidence_reference: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LabelledBenchmark:
    """Container for jobs, anonymized resumes and human annotations."""

    name: str
    jobs: Tuple[JobRecord, ...] = ()
    resumes: Tuple[ResumeRecord, ...] = ()
    annotations: Tuple[AnnotationRecord, ...] = ()
    reviewers: Tuple[str, ...] = ()
    schema_version: str = ANNOTATION_SCHEMA_VERSION
    rubric_version: str = RUBRIC_VERSION
    notes: str = ""

    @property
    def jd_ids(self) -> List[str]:
        return sorted(job.jd_id for job in self.jobs)

    @property
    def candidate_ids(self) -> List[str]:
        return sorted(resume.candidate_id for resume in self.resumes)

    @property
    def is_empty(self) -> bool:
        return not self.annotations

    @property
    def pairs(self) -> List[Tuple[str, str]]:
        seen = {(ann.jd_id, ann.candidate_id) for ann in self.annotations}
        return sorted(seen)

    def annotations_for(self, jd_id: str, candidate_id: str) -> List[AnnotationRecord]:
        return [
            ann
            for ann in self.annotations
            if ann.jd_id == jd_id and ann.candidate_id == candidate_id
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema_version": self.schema_version,
            "rubric_version": self.rubric_version,
            "reviewers": list(self.reviewers),
            "notes": self.notes,
            "jobs": [job.to_dict() for job in self.jobs],
            "resumes": [resume.to_dict() for resume in self.resumes],
            "annotations": [ann.to_dict() for ann in self.annotations],
        }


def consensus_grade(annotations: Sequence[AnnotationRecord]) -> Optional[int]:
    """Return the usable human grade for a pair, or None when unresolved.

    An explicitly adjudicated grade always wins. Otherwise all reviewers must
    agree; unresolved disagreements return None and block tuning/evaluation.
    """
    if not annotations:
        return None
    adjudicated = [ann.adjudicated_grade for ann in annotations if ann.adjudicated_grade is not None]
    if adjudicated:
        if len(set(adjudicated)) != 1:
            return None
        return int(adjudicated[0])
    grades = {int(ann.grade) for ann in annotations}
    if len(grades) != 1:
        return None
    return int(grades.pop())


def _is_pii_like(identifier: str) -> bool:
    return bool(re.search(r"@", identifier)) or bool(re.match(r"^\d{10,}$", identifier.strip()))


def validate_benchmark(benchmark: LabelledBenchmark) -> List[Dict[str, str]]:
    """Return a list of validation issues; an empty list means valid.

    Issues are dictionaries with ``code``, ``message`` and ``severity`` where
    severity is ``fatal`` (structure/correctness) or ``warning`` (label quality
    that may still block a specific claim).
    """
    issues: List[Dict[str, str]] = []

    def add(code: str, message: str, severity: str = "fatal") -> None:
        issues.append({"code": code, "message": message, "severity": severity})

    job_ids = [job.jd_id for job in benchmark.jobs]
    candidate_ids = [resume.candidate_id for resume in benchmark.resumes]
    for code, values in (("duplicate_jd_id", job_ids), ("duplicate_candidate_id", candidate_ids)):
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        for value in duplicates:
            add(code, f"Duplicate identifier: {value}")

    jobs_by_id = {job.jd_id: job for job in benchmark.jobs}
    resumes_by_id = {resume.candidate_id: resume for resume in benchmark.resumes}
    for jd_id, job in jobs_by_id.items():
        if not job.job_text.strip():
            add("missing_jd_text", f"JD {jd_id} has no description text")
        if not job.role_category.strip():
            add("missing_role_category", f"JD {jd_id} has no role category")
    for candidate_id, resume in resumes_by_id.items():
        if not resume.resume_text.strip():
            add("missing_resume_text", f"Candidate {candidate_id} has no resume text")
        if _is_pii_like(candidate_id):
            add("pii_like_identifier", f"Candidate identifier is not anonymized: {candidate_id}")
        if resume.identity_key and _is_pii_like(resume.identity_key):
            add("pii_like_identity_key", f"Identity key is not anonymized: {candidate_id}")

    declared_reviewers = set(benchmark.reviewers)
    seen_annotations: Dict[Tuple[str, str, str], AnnotationRecord] = {}
    for ann in benchmark.annotations:
        key = (ann.jd_id, ann.candidate_id, ann.reviewer_id)
        if key in seen_annotations:
            if seen_annotations[key].grade != ann.grade:
                add("conflicting_annotation", f"Conflicting grades for {key}")
            else:
                add("duplicate_annotation", f"Duplicate annotation for {key}")
        seen_annotations[key] = ann
        if ann.jd_id not in jobs_by_id:
            add("unknown_jd", f"Annotation references unknown JD {ann.jd_id}")
        if ann.candidate_id not in resumes_by_id:
            add("unknown_candidate", f"Annotation references unknown candidate {ann.candidate_id}")
        if declared_reviewers and ann.reviewer_id not in declared_reviewers:
            add("unknown_reviewer", f"Undeclared reviewer {ann.reviewer_id}")
        if ann.grade not in [int(g) for g in RelevanceGrade5]:
            add("invalid_grade", f"Invalid grade {ann.grade!r} for {key}")
        if not ann.rationale.strip():
            add("missing_rationale", f"Missing rationale for {key}")
        if ann.adjudication_status not in ADJUDICATION_STATUSES:
            add("invalid_adjudication_status", f"Invalid adjudication status for {key}")
        if ann.adjudicated_grade is not None and ann.adjudicated_grade not in [int(g) for g in RelevanceGrade5]:
            add("invalid_adjudicated_grade", f"Invalid adjudicated grade for {key}")

    # Reviewer completeness: every annotated pair should have every declared
    # reviewer when two or more reviewers are declared.
    annotations_by_pair: Dict[Tuple[str, str], set] = defaultdict(set)
    for jd_id, candidate_id, reviewer_id in seen_annotations:
        annotations_by_pair[(jd_id, candidate_id)].add(reviewer_id)
    if len(declared_reviewers) >= 2:
        for pair, reviewers in sorted(annotations_by_pair.items()):
            missing = sorted(declared_reviewers - reviewers)
            if missing:
                add(
                    "incomplete_reviewers",
                    f"Pair {pair} is missing reviewer(s): {', '.join(missing)}",
                    severity="warning",
                )

    # Every job/candidate combination intended for evaluation must be labelled.
    if benchmark.jobs and benchmark.resumes:
        for jd_id in benchmark.jd_ids:
            for candidate_id in benchmark.candidate_ids:
                if (jd_id, candidate_id) not in annotations_by_pair:
                    add(
                        "missing_label",
                        f"No annotation for JD {jd_id} / candidate {candidate_id}",
                    )

    return issues


def require_valid(benchmark: LabelledBenchmark) -> None:
    """Raise ValueError when fatal structural validation issues exist."""
    fatal = [issue for issue in validate_benchmark(benchmark) if issue["severity"] == "fatal"]
    if fatal:
        raise ValueError("; ".join(issue["message"] for issue in fatal[:10]))


def disagreement_summary(benchmark: LabelledBenchmark) -> Dict[str, Any]:
    """Count unresolved and adjudicated disagreements per pair."""
    unresolved: List[Tuple[str, str]] = []
    adjudicated: List[Tuple[str, str]] = []
    for jd_id, candidate_id in benchmark.pairs:
        anns = benchmark.annotations_for(jd_id, candidate_id)
        grades = {int(ann.grade) for ann in anns}
        if len(grades) > 1:
            if consensus_grade(anns) is not None:
                adjudicated.append((jd_id, candidate_id))
            else:
                unresolved.append((jd_id, candidate_id))
    return {
        "pair_count": len(benchmark.pairs),
        "disagreement_count": len(unresolved) + len(adjudicated),
        "unresolved_count": len(unresolved),
        "adjudicated_count": len(adjudicated),
        "unresolved_pairs": [list(pair) for pair in unresolved],
        "adjudicated_pairs": [list(pair) for pair in adjudicated],
    }


def tuning_readiness(benchmark: LabelledBenchmark) -> Dict[str, Any]:
    """Report whether labels are complete enough to freeze and begin tuning."""
    issues = validate_benchmark(benchmark)
    fatal = [issue for issue in issues if issue["severity"] == "fatal"]
    disagreements = disagreement_summary(benchmark)
    if benchmark.is_empty:
        ready = False
        reasons = ["no_annotations"]
    else:
        reasons = sorted({issue["code"] for issue in issues})
        if disagreements["unresolved_count"]:
            reasons.append("unresolved_disagreements")
        ready = not reasons
    return {
        "ready": ready,
        "reasons": reasons,
        "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
        "fatal_count": len(fatal),
        "disagreements": disagreements,
    }


def cohens_kappa(pairs: Sequence[Sequence[int]], quadratic: bool = False) -> Optional[float]:
    """Unweighted or quadratically weighted Cohen's kappa for two raters."""
    ratings = [(int(first), int(second)) for first, second in pairs if first is not None and second is not None]
    if len(ratings) < 2:
        return None
    n = len(ratings)
    categories = [int(grade) for grade in RelevanceGrade5]
    observed_matrix = Counter(ratings)
    first_counts = Counter(first for first, _ in ratings)
    second_counts = Counter(second for _, second in ratings)

    def weight(a: int, b: int) -> float:
        """Agreement weight: 1 for identical ratings, 0 for maximal distance."""
        if not quadratic:
            return 1.0 if a == b else 0.0
        return 1.0 - ((a - b) ** 2) / ((len(categories) - 1) ** 2)

    observed = sum(weight(a, b) * observed_matrix.get((a, b), 0) for a in categories for b in categories) / n
    expected = sum(
        weight(a, b) * (first_counts[a] / n) * (second_counts[b] / n)
        for a in categories
        for b in categories
    )
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def reviewer_ratings(benchmark: LabelledBenchmark) -> Dict[str, Dict[Tuple[str, str], int]]:
    ratings: Dict[str, Dict[Tuple[str, str], int]] = defaultdict(dict)
    for ann in benchmark.annotations:
        ratings[ann.reviewer_id][(ann.jd_id, ann.candidate_id)] = int(ann.grade)
    return dict(ratings)


def krippendorff_alpha(benchmark: LabelledBenchmark) -> Optional[float]:
    """Interval-level Krippendorff's alpha across all available reviewers."""
    by_reviewer = reviewer_ratings(benchmark)
    reviewer_ids = sorted(by_reviewer)
    if len(reviewer_ids) < 2:
        return None
    pairs = sorted({pair for ratings in by_reviewer.values() for pair in ratings})
    units: List[List[Optional[float]]] = []
    for pair in pairs:
        values = [by_reviewer[reviewer].get(pair) for reviewer in reviewer_ids]
        observed = [float(value) for value in values if value is not None]
        if len(observed) >= 2:
            units.append(values)
    if len(units) < 2:
        return None

    all_values = [float(value) for unit in units for value in unit if value is not None]
    if not all_values:
        return None
    grand_mean = statistics.fmean(all_values)
    coincidence_total = 0.0
    for unit in units:
        observed = [float(value) for value in unit if value is not None]
        m = len(observed)
        if m < 2:
            continue
        unit_mean = statistics.fmean(observed)
        coincidence_total += sum((value - unit_mean) ** 2 for value in observed) / (m - 1)

    n = len(all_values)
    variance = sum((value - grand_mean) ** 2 for value in all_values) / (n - 1)
    if variance == 0.0:
        return None
    Do = coincidence_total / len(units)
    De = variance
    return 1.0 - Do / De


def agreement_summary(benchmark: LabelledBenchmark) -> Dict[str, Any]:
    """Compute only agreement metrics supported by the sample structure."""
    by_reviewer = reviewer_ratings(benchmark)
    reviewer_ids = sorted(by_reviewer)
    pairs = sorted({pair for ratings in by_reviewer.values() for pair in ratings})
    complete_two = []
    if len(reviewer_ids) == 2:
        for pair in pairs:
            values = [by_reviewer[reviewer].get(pair) for reviewer in reviewer_ids]
            if all(value is not None for value in values):
                complete_two.append(values)
    return {
        "reviewer_count": len(reviewer_ids),
        "pair_count": len(pairs),
        "complete_two_reviewer_pairs": len(complete_two),
        "cohens_kappa": cohens_kappa(complete_two),
        "quadratic_weighted_kappa": cohens_kappa(complete_two, quadratic=True),
        "krippendorff_alpha": krippendorff_alpha(benchmark),
        "reported": bool(complete_two) and len(reviewer_ids) == 2,
    }


def build_annotation_template(
    jobs: Sequence[JobRecord],
    resumes: Sequence[ResumeRecord],
    reviewers: Sequence[str] = (),
) -> Dict[str, Any]:
    """Create an empty annotation workbook with one row per JD/candidate pair.

    No grade or rationale is filled in: human reviewers must supply them.
    """
    annotations = [
        {
            "jd_id": job.jd_id,
            "candidate_id": resume.candidate_id,
            "reviewer_id": "",
            "grade": None,
            "strengths": [],
            "missing_qualifications": [],
            "rationale": "",
            "reviewed_at": "",
            "adjudication_status": "pending",
            "adjudicated_grade": None,
            "evidence_reference": "",
        }
        for job in jobs
        for resume in resumes
    ]
    return {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "binary_relevance_threshold": BINARY_RELEVANCE_THRESHOLD,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instructions": [
            "Assign grades independently before discussing with other reviewers.",
            "Never use the model under test, its score, or its rank to assign a grade.",
            "Every row needs a short evidence-based rationale and reviewer id.",
            "Resolve disagreements with an explicit adjudicated_grade.",
            "Use anonymized identifiers only; do not add names, emails or phone numbers.",
        ],
        "reviewers": list(reviewers),
        "rubric": [
            {"grade": grade, "meaning": meaning, "example": RUBRIC_EXAMPLES[grade]}
            for grade, meaning in sorted(RELEVANCE_RUBRIC.items())
        ],
        "jobs": [job.to_dict() for job in jobs],
        "resumes": [resume.to_dict() for resume in resumes],
        "annotations": annotations,
    }


def load_benchmark(path: str) -> LabelledBenchmark:
    """Load a benchmark JSON file produced by the annotation workflow."""
    import json
    from pathlib import Path

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return benchmark_from_dict(payload)


def benchmark_from_dict(payload: Mapping[str, Any]) -> LabelledBenchmark:
    return LabelledBenchmark(
        name=str(payload.get("name", "phase11_5_benchmark")),
        jobs=tuple(JobRecord(**job) for job in payload.get("jobs", [])),
        resumes=tuple(ResumeRecord(**resume) for resume in payload.get("resumes", [])),
        annotations=tuple(AnnotationRecord(**ann) for ann in payload.get("annotations", [])),
        reviewers=tuple(payload.get("reviewers", [])),
        schema_version=str(payload.get("schema_version", ANNOTATION_SCHEMA_VERSION)),
        rubric_version=str(payload.get("rubric_version", RUBRIC_VERSION)),
        notes=str(payload.get("notes", "")),
    )
