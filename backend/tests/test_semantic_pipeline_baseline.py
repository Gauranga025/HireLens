"""Frozen characterization of the pre-Phase-11.4 document-level semantic path.

These tests deliberately model the legacy calculation locally. They preserve a
record of the baseline without asserting that the live pipeline still uses the
legacy call pattern after Stage 3.
"""
import json

import pytest

from app.evaluation.semantic_intelligence_dataset import (
    PILOT_TARGET_PAIRS,
    empty_pilot_dataset,
    expansion_target_manifest,
    pilot_target_manifest,
)


class LegacyDocumentSemanticService:
    """Records the exact call pattern used by the old implementation."""

    def __init__(self, score):
        self.score = score
        self.calls = []

    def compute_similarity(self, text1, text2):
        self.calls.append((text1, text2))
        return self.score


def _legacy_score(service, job_text, resume_text):
    similarity = service.compute_similarity(job_text, resume_text)
    return None if similarity is None else similarity * 100.0


def test_baseline_embedded_whole_raw_documents_once():
    job_text = "Required: Python REST API development"
    resume_text = "EXPERIENCE: Built Python REST APIs"
    service = LegacyDocumentSemanticService(0.724)

    score = _legacy_score(service, job_text, resume_text)

    assert score == pytest.approx(72.4)
    assert service.calls == [(job_text, resume_text)]


def test_baseline_no_similarity_stays_none():
    service = LegacyDocumentSemanticService(None)
    assert _legacy_score(service, "job", "resume") is None


def test_baseline_semantic_contribution_uses_thirty_percent_weight():
    score = 72.4
    contribution = 0.30 * (score / 100.0) * 100.0
    assert contribution == pytest.approx(21.72)


def test_benchmark_scaffold_records_targets_without_fabricated_data():
    dataset = empty_pilot_dataset()
    pilot = pilot_target_manifest()
    expansion = expansion_target_manifest()

    assert dataset.is_empty
    assert pilot["target_pairs"] == PILOT_TARGET_PAIRS == 60
    assert pilot["labelled_pairs"] == 0
    assert pilot["results"] is None
    assert pilot["claim_permitted"] is False
    assert expansion["min_distinct_jds"] == 20
    assert expansion["max_distinct_jds"] == 30


def test_benchmark_script_emits_no_fabricated_results(tmp_path):
    from scripts.evaluate_semantic_intelligence import build_report, write_report

    report = build_report()
    output = write_report(report, tmp_path / "evaluation.json")
    written = json.loads(output.read_text(encoding="utf-8"))

    assert report["status"] == "no_labelled_benchmark"
    assert report["baseline"] is None
    assert report["proposed"] is None
    assert report["paired_comparison"] is None
    assert report["accuracy_claim"] == "not_permitted"
    assert report["parameters"]["threshold"] == 0.25
    assert report["parameters"]["top_k"] == 3
    assert written == report


def test_benchmark_ranking_metrics_are_deterministic():
    from scripts.evaluate_semantic_intelligence import ranking_metrics

    labels = [3, 2, 1, 0]
    scores = [81.0, 70.0, 55.0, 40.0]

    first = ranking_metrics(labels, scores)
    second = ranking_metrics(labels, scores)

    assert first == second
    assert first["ndcg_at_3"] > 0
    assert first["precision_at_3"] == pytest.approx(2.0 / 3.0)
    assert first["monotonicity_violations"] == 0
