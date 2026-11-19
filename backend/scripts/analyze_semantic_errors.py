"""Generate an evidence-based error analysis from a Phase 11.5 results file.

The analyzer only reads records produced by ``evaluate_semantic_benchmark.py``.
It never invents examples and it reports anonymized candidate IDs only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.semantic_benchmark import BASELINE_SYSTEM, PROPOSED_SYSTEM
from app.evaluation.semantic_metrics import rank_order

DEFAULT_OUTPUT = Path(__file__).parent.parent / "evaluation" / "reports" / "PHASE11_5_ERROR_ANALYSIS.md"


def _rank_map(records: Sequence[Mapping[str, Any]], system: str, score_kind: str) -> Dict[str, int]:
    selected = [
        record
        for record in records
        if record.get("system") == system and record.get("score_kind") == score_kind
    ]
    scores = [
        float("-inf") if record.get("semantic_score" if score_kind == "semantic" else "overall_score") is None
        else float(record["semantic_score" if score_kind == "semantic" else "overall_score"])
        for record in selected
    ]
    order = rank_order(scores)
    return {str(selected[index].get("candidate_id")): position + 1 for position, index in enumerate(order)}


def _length_bucket(chars: int) -> str:
    if chars < 3000:
        return "short"
    if chars > 8000:
        return "long"
    return "medium"


def analyze_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    status = report.get("status")
    if status != "measured":
        return {
            "status": "blocked",
            "reason": status or "unknown_status",
            "finding_count": 0,
            "findings": [],
            "note": "No ranking results were produced; error analysis requires genuine labels and measured rankings.",
        }

    records = list(report.get("records", []))
    findings: List[Dict[str, Any]] = []
    for jd_id in sorted({record.get("jd_id", "") for record in records}):
        jd_records = [record for record in records if record.get("jd_id") == jd_id]
        semantic_ranks = _rank_map(jd_records, PROPOSED_SYSTEM, "semantic")
        overall_ranks = _rank_map(jd_records, PROPOSED_SYSTEM, "overall")
        baseline_ranks = _rank_map(jd_records, BASELINE_SYSTEM, "semantic")
        unique: Dict[str, Mapping[str, Any]] = {}
        for record in jd_records:
            unique.setdefault(str(record.get("candidate_id")), record)
        for candidate_id, record in sorted(unique.items()):
            grade = int(record.get("grade", -1))
            semantic_rank = semantic_ranks.get(candidate_id, -1)
            overall_rank = overall_ranks.get(candidate_id, -1)
            baseline_rank = baseline_ranks.get(candidate_id, -1)
            strata = set(record.get("strata", ()) or ())
            requirement_types = set(record.get("requirement_types", ()) or ())
            length_bucket = _length_bucket(int(record.get("resume_length_chars", 0) or 0))
            categories: List[str] = []
            if grade >= 3 and semantic_rank > 5:
                categories.append("relevant_candidate_ranked_too_low")
            if grade <= 1 and semantic_rank <= 3:
                categories.append("irrelevant_candidate_ranked_too_high")
            if strata & {"paraphrase", "related_technology"} and grade >= 3 and semantic_rank > 5:
                categories.append("unfamiliar_or_related_terminology")
            if strata & {"token_boundary", "long_resume"} and grade >= 3 and semantic_rank > 5:
                categories.append("late_or_boundary_evidence")
            if strata & {"missing_requirement"} and grade <= 1 and semantic_rank <= 3:
                categories.append("missing_requirement_overvalued")
            if strata & {"boilerplate"} and grade <= 1 and semantic_rank <= 3:
                categories.append("boilerplate_overvalued")
            if "REQUIRED_GROUP" in requirement_types and grade >= 3 and semantic_rank > 5:
                categories.append("required_group_alternatives_mishandled")
            if baseline_rank > 0 and semantic_rank > 0 and grade >= 3 and semantic_rank > baseline_rank:
                categories.append("semantic_worse_than_baseline_for_relevant_candidate")
            if semantic_rank > 0 and overall_rank > 0 and abs(semantic_rank - overall_rank) >= 3:
                categories.append("semantic_final_ranking_disagreement")
            for category in categories:
                findings.append(
                    {
                        "category": category,
                        "jd_id": jd_id,
                        "candidate_id": candidate_id,
                        "role_category": str(record.get("role_category", "")),
                        "grade": grade,
                        "semantic_rank": semantic_rank,
                        "overall_rank": overall_rank,
                        "baseline_semantic_rank": baseline_rank,
                        "resume_length_bucket": length_bucket,
                        "requirement_types": sorted(requirement_types),
                        "strata": sorted(strata),
                        "semantic_status": str(record.get("semantic_status", "")),
                    }
                )

        proposed_semantic = [
            float(record["semantic_score"])
            for record in jd_records
            if record.get("system") == PROPOSED_SYSTEM
            and record.get("score_kind") == "semantic"
            and record.get("semantic_score") is not None
        ]
        if len(proposed_semantic) > 1:
            std = statistics.pstdev(proposed_semantic)
            if std < 2.0:
                findings.append(
                    {
                        "category": "score_compression",
                        "jd_id": jd_id,
                        "candidate_id": "",
                        "role_category": str(jd_records[0].get("role_category", "")),
                        "grade": -1,
                        "semantic_score_std": round(std, 6),
                        "candidate_count": len(proposed_semantic),
                        "requirement_types": [],
                        "strata": [],
                        "semantic_status": "",
                    }
                )
            ties = len(proposed_semantic) - len(set(round(value, 6) for value in proposed_semantic))
            if ties:
                findings.append(
                    {
                        "category": "indistinguishable_scores",
                        "jd_id": jd_id,
                        "candidate_id": "",
                        "role_category": str(jd_records[0].get("role_category", "")),
                        "grade": -1,
                        "tie_count": ties,
                        "candidate_count": len(proposed_semantic),
                        "requirement_types": [],
                        "strata": [],
                        "semantic_status": "",
                    }
                )

    by_category = Counter(finding["category"] for finding in findings)
    by_role = Counter(
        (finding["category"], finding["role_category"]) for finding in findings
    )
    by_requirement_type = Counter(
        (finding["category"], req_type)
        for finding in findings
        for req_type in finding["requirement_types"]
    )
    by_length = Counter(
        (finding["category"], finding["resume_length_bucket"]) for finding in findings
    )
    by_evidence = Counter(
        (finding["category"], "present" if finding["grade"] >= 3 else "missing_or_weak")
        for finding in findings
        if finding["grade"] >= 0
    )
    return {
        "status": "analyzed",
        "finding_count": len(findings),
        "by_category": dict(sorted(by_category.items())),
        "by_role": {f"{cat}|{role}": count for (cat, role), count in sorted(by_role.items())},
        "by_requirement_type": {
            f"{cat}|{req_type}": count
            for (cat, req_type), count in sorted(by_requirement_type.items())
        },
        "by_resume_length": {
            f"{cat}|{bucket}": count for (cat, bucket), count in sorted(by_length.items())
        },
        "by_evidence_state": {
            f"{cat}|{state}": count for (cat, state), count in sorted(by_evidence.items())
        },
        "findings": findings,
        "privacy_note": "Only anonymized candidate IDs from the benchmark are reported.",
    }


def render_markdown(analysis: Mapping[str, Any]) -> str:
    lines = ["# Phase 11.5 Ranking Error Analysis", ""]
    if analysis.get("status") != "analyzed":
        lines.extend(
            [
                "## Status: BLOCKED",
                "",
                f"- Reason: `{analysis.get('reason')}`",
                f"- {analysis.get('note', '')}",
                "",
                "No error cases are listed because no genuine measured rankings were available.",
            ]
        )
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            f"Total findings: **{analysis['finding_count']}**",
            "",
            "## By failure category",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
    )
    for category, count in analysis["by_category"].items():
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Grouped patterns", ""])
    for name in ("by_role", "by_requirement_type", "by_resume_length", "by_evidence_state"):
        lines.append(f"### {name.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Group | Count |")
        lines.append("|---|---:|")
        for key, count in analysis[name].items():
            lines.append(f"| {key} | {count} |")
        lines.append("")
    lines.extend(["## Evidence references", ""])
    for finding in analysis["findings"][:100]:
        lines.append(
            f"- `{finding['jd_id']}` / `{finding['candidate_id'] or 'jd-level'}`: "
            f"{finding['category']} (grade={finding['grade']}, "
            f"semantic_rank={finding.get('semantic_rank', 'n/a')}, "
            f"overall_rank={finding.get('overall_rank', 'n/a')}, "
            f"role={finding['role_category']})"
        )
    lines.extend(
        [
            "",
            analysis["privacy_note"],
            "",
            "Isolated examples are not used to change the production algorithm; only systematic patterns are actionable.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    report = json.loads(Path(args.results).read_text(encoding="utf-8"))
    analysis = analyze_report(report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({"status": analysis["status"], "finding_count": analysis.get("finding_count", 0), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
