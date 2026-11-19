"""Ranking metrics and uncertainty estimates for Phase 11.5.

All functions are deterministic, tolerate missing candidates and tied scores,
and return ``None`` (rather than inventing a number) when a metric is
undefined. The gain function for graded NDCG is frozen as ``2**grade - 1``.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

DEFAULT_K_VALUES = (1, 3, 5, 10)


def graded_gain(grade: int) -> float:
    """Exponential gain for graded relevance (0 -> 0, 4 -> 15)."""
    return float(2 ** max(0, int(grade)) - 1)


def average_ties(values: Sequence[float]) -> List[float]:
    """Return ascending ranks with average ranks assigned to ties."""
    indexed = sorted((float(value), index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and indexed[end + 1][0] == indexed[position][0]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for cursor in range(position, end + 1):
            ranks[indexed[cursor][1]] = average
        position = end + 1
    return ranks


def rank_order(scores: Sequence[float]) -> List[int]:
    """Stable descending ranking; lower original index breaks score ties."""
    return sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))


def ndcg_at_k(
    grades: Sequence[int], scores: Sequence[float], k: int, gain=graded_gain
) -> float:
    """Gain-based NDCG@k; returns 0.0 when the ideal gain is zero."""
    if k <= 0 or len(grades) != len(scores) or not grades:
        return 0.0
    order = rank_order(scores)[:k]
    dcg = sum(gain(grades[index]) / math.log2(rank + 2) for rank, index in enumerate(order))
    ideal = sorted((gain(grade) for grade in grades), reverse=True)[:k]
    idcg = sum(value / math.log2(rank + 2) for rank, value in enumerate(ideal))
    if idcg <= 0.0:
        return 0.0
    return min(1.0, max(0.0, dcg / idcg))


def precision_at_k(
    grades: Sequence[int], scores: Sequence[float], k: int, threshold: int
) -> float:
    if k <= 0 or len(grades) != len(scores) or not grades:
        return 0.0
    order = rank_order(scores)[:k]
    return sum(1 for index in order if grades[index] >= threshold) / k


def recall_at_k(
    grades: Sequence[int], scores: Sequence[float], k: int, threshold: int
) -> float:
    if k <= 0 or len(grades) != len(scores) or not grades:
        return 0.0
    relevant = sum(1 for grade in grades if grade >= threshold)
    if relevant == 0:
        return 0.0
    order = rank_order(scores)[:k]
    return sum(1 for index in order if grades[index] >= threshold) / relevant


def reciprocal_rank(
    grades: Sequence[int], scores: Sequence[float], target_grade: int
) -> float:
    order = rank_order(scores)
    for rank, index in enumerate(order):
        if grades[index] >= target_grade:
            return 1.0 / (rank + 1)
    return 0.0


def spearman(scores: Sequence[float], grades: Sequence[int]) -> Optional[float]:
    if len(scores) < 2 or len(scores) != len(grades):
        return None
    score_ranks = average_ties(scores)
    grade_ranks = average_ties(grades)
    mean_s = statistics.fmean(score_ranks)
    mean_g = statistics.fmean(grade_ranks)
    numerator = sum((s - mean_s) * (g - mean_g) for s, g in zip(score_ranks, grade_ranks))
    denominator = math.sqrt(
        sum((s - mean_s) ** 2 for s in score_ranks)
        * sum((g - mean_g) ** 2 for g in grade_ranks)
    )
    if denominator == 0.0:
        return None
    return numerator / denominator


def kendall_tau_b(scores: Sequence[float], grades: Sequence[int]) -> Optional[float]:
    """Kendall's tau-b with ties in either variable; None when undefined."""
    n = len(scores)
    if n < 2 or n != len(grades):
        return None
    concordant = discordant = score_ties = grade_ties = both_ties = 0
    for i in range(n):
        for j in range(i + 1, n):
            s_diff = (float(scores[i]) > float(scores[j])) - (float(scores[i]) < float(scores[j]))
            g_diff = (grades[i] > grades[j]) - (grades[i] < grades[j])
            if s_diff == 0 and g_diff == 0:
                both_ties += 1
            elif s_diff == 0:
                score_ties += 1
            elif g_diff == 0:
                grade_ties += 1
            elif s_diff == g_diff:
                concordant += 1
            else:
                discordant += 1
    score_pairs = n * (n - 1) / 2.0
    denominator = math.sqrt(
        (score_pairs - score_ties - both_ties)
        * (score_pairs - grade_ties - both_ties)
    )
    if denominator == 0.0:
        return None
    return (concordant - discordant) / denominator


def ranking_metrics(
    grades: Sequence[int],
    scores: Sequence[Optional[float]],
    *,
    k_values: Sequence[int] = DEFAULT_K_VALUES,
    relevance_threshold: int = 2,
    mrr_target_grade: int = 3,
) -> Dict[str, Any]:
    """Compute all ranking metrics for one JD.

    Missing scores are replaced by -inf for ranking and counted separately so
    failed candidates are never silently excluded from the denominator.
    """
    if len(grades) != len(scores) or not grades:
        return {"pair_count": 0, "missing_score_count": len(scores), "metrics": {}}
    missing = [index for index, score in enumerate(scores) if score is None]
    clean_grades = [int(grade) for grade in grades]
    rankable_scores = [float("-inf") if score is None else float(score) for score in scores]
    metrics: Dict[str, Any] = {
        "pair_count": len(clean_grades),
        "missing_score_count": len(missing),
        "relevance_threshold": relevance_threshold,
        "ordered_candidate_indices": rank_order(rankable_scores),
    }
    for k in k_values:
        metrics[f"ndcg_at_{k}"] = ndcg_at_k(clean_grades, rankable_scores, k)
    for k in (3, 5):
        metrics[f"precision_at_{k}"] = precision_at_k(
            clean_grades, rankable_scores, k, relevance_threshold
        )
        metrics[f"recall_at_{k}"] = recall_at_k(
            clean_grades, rankable_scores, k, relevance_threshold
        )
    metrics["mrr"] = reciprocal_rank(clean_grades, rankable_scores, mrr_target_grade)
    metrics["spearman"] = spearman(rankable_scores, clean_grades)
    metrics["kendall_tau"] = kendall_tau_b(rankable_scores, clean_grades)
    metrics["missing_candidate_ids"] = missing
    return metrics


def describe(values: Sequence[Optional[float]], confidence: float = 0.95) -> Dict[str, Optional[float]]:
    """Mean, median, std, and a normal-approximation CI over JD-level values."""
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "std": None,
            "ci_lower": None,
            "ci_upper": None,
        }
    mean = statistics.fmean(numeric)
    std = statistics.stdev(numeric) if len(numeric) > 1 else 0.0
    z = 1.96 if abs(confidence - 0.95) < 1e-9 else _normal_quantile(confidence)
    margin = z * std / math.sqrt(len(numeric)) if numeric else 0.0
    return {
        "count": len(numeric),
        "mean": mean,
        "median": statistics.median(numeric),
        "std": std,
        "ci_lower": mean - margin,
        "ci_upper": mean + margin,
    }


def _normal_quantile(confidence: float) -> float:
    """Inverse normal CDF approximation (Acklam) for arbitrary confidence."""
    p = 1.0 - (1.0 - confidence) / 2.0
    a = [-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924]
    b = [-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857]
    c = [-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878]
    d = [0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > 1 - 0.02425:
        return -_normal_quantile(2 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1
    )


def paired_bootstrap_ci(
    baseline_by_jd: Mapping[str, Mapping[str, Any]],
    proposed_by_jd: Mapping[str, Mapping[str, Any]],
    metric: str = "ndcg_at_3",
    samples: int = 2000,
    seed: int = 20261119,
) -> Dict[str, Any]:
    """JD-level paired bootstrap CI for (proposed - baseline) metric deltas."""
    jd_ids = sorted(set(baseline_by_jd) & set(proposed_by_jd))
    if not jd_ids:
        return {"metric": metric, "jd_count": 0, "lower": None, "upper": None, "observed_mean": None}
    deltas = [
        float(proposed_by_jd[jd].get(metric) or 0.0)
        - float(baseline_by_jd[jd].get(metric) or 0.0)
        for jd in jd_ids
    ]
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(samples):
        draw = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        means.append(statistics.fmean(draw))
    means.sort()
    lower_index = min(len(means) - 1, max(0, int(0.025 * len(means)) - 1))
    upper_index = min(len(means) - 1, int(0.975 * len(means)))
    return {
        "metric": metric,
        "jd_count": len(jd_ids),
        "lower": means[lower_index],
        "upper": means[upper_index],
        "observed_mean": statistics.fmean(deltas),
        "samples": samples,
        "seed": seed,
    }
