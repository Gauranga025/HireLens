"""
Phase 4 Aggregate Evaluation
Run the 42-resume benchmark across all 5 job descriptions with different configurations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation_dataset_extended import EXTENDED_EVALUATION_DATASET
from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills
import numpy as np

print("=== Phase 4 Aggregate Evaluation ===\n")

jobs = EXTENDED_EVALUATION_DATASET["job_descriptions"]
resumes = EXTENDED_EVALUATION_DATASET["resumes"]

print(f"Total job descriptions: {len(jobs)}")
print(f"Total resumes: {len(resumes)}")
print()

# Define configurations for comparison
configs = {
    "baseline": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=False,
    ),
    "semantic": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=False,
    ),
    "evidence": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=True,
        use_keyword_stuffing_penalty=False,
    ),
    "hierarchy": ScoringConfig(
        use_skill_hierarchy=True,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=False,
    ),
    "stuffing": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=True,
    ),
    "complete": ScoringConfig(
        use_skill_hierarchy=True,
        use_demonstration_levels=True,
        use_keyword_stuffing_penalty=True,
    ),
}

def calculate_precision_at_k(ranked_ids, relevant_ids, k=5):
    """Calculate Precision@K."""
    top_k = ranked_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top_k / k if k > 0 else 0.0

def calculate_recall_at_k(ranked_ids, relevant_ids, k=5):
    """Calculate Recall@K."""
    top_k = ranked_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    total_relevant = len(relevant_ids)
    return relevant_in_top_k / total_relevant if total_relevant > 0 else 0.0

def calculate_ndcg_at_k(ranked_ids, relevance_scores, k=5):
    """Calculate NDCG@K."""
    if not ranked_ids:
        return 0.0
    
    dcg = 0.0
    for i, rid in enumerate(ranked_ids[:k]):
        rel = relevance_scores.get(rid, 0)
        if rel > 0:
            dcg += rel / np.log2(i + 2)
    
    # Ideal DCG
    ideal_relevances = sorted([relevance_scores.get(rid, 0) for rid in ranked_ids], reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_relevances):
        if rel > 0:
            idcg += rel / np.log2(i + 2)
    
    return dcg / idcg if idcg > 0 else 0.0

def calculate_mrr(ranked_ids, relevant_ids):
    """Calculate Mean Reciprocal Rank."""
    for i, rid in enumerate(ranked_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0

# Store results per job
job_results = {}

for job in jobs:
    print(f"\n{'='*60}")
    print(f"Job: {job['title']} ({job['id']})")
    print(f"{'='*60}")
    
    # Filter resumes for this job
    job_resumes = [r for r in resumes if r["for_job"] == job["id"]]
    print(f"Resumes for this job: {len(job_resumes)}")
    
    # Get relevant resumes (high or medium relevance)
    relevant_resumes = {r["id"]: 2 if r["relevance"] == "high" else 1 if r["relevance"] == "medium" else 0 for r in job_resumes}
    relevant_ids = {rid for rid, rel in relevant_resumes.items() if rel > 0}
    print(f"Relevant resumes: {len(relevant_ids)}")
    print()
    
    job_results[job["id"]] = {}
    
    for config_name, config in configs.items():
        scoring_service = ScoringService(config=config)
        
        ranked = []
        for resume in job_resumes:
            resume_skills = extract_skills(resume["content"])["technical_skills"]
            
            result = scoring_service.compute_match(
                resume_text=resume["content"],
                job_text=job["description"],
                resume_skills=resume_skills,
                required_skills=job["required_skills"],
                preferred_skills=job["preferred_skills"],
                use_semantic=True,
            )
            
            ranked.append({
                "id": resume["id"],
                "name": resume.get("name", "Unknown"),
                "score": result["overall_score"],
                "relevance": resume["relevance"],
            })
        
        ranked.sort(key=lambda x: x["score"], reverse=True)
        ranked_ids = [r["id"] for r in ranked]
        
        # Calculate metrics
        p5 = calculate_precision_at_k(ranked_ids, relevant_ids, 5)
        r5 = calculate_recall_at_k(ranked_ids, relevant_ids, 5)
        ndcg5 = calculate_ndcg_at_k(ranked_ids, relevant_resumes, 5)
        mrr = calculate_mrr(ranked_ids, relevant_ids)
        
        job_results[job["id"]][config_name] = {
            "p5": p5,
            "r5": r5,
            "ndcg5": ndcg5,
            "mrr": mrr,
            "ranked": ranked,
        }
        
        print(f"{config_name:12} | P@5: {p5:.3f} | R@5: {r5:.3f} | NDCG@5: {ndcg5:.3f} | MRR: {mrr:.3f}")

# Calculate macro averages
print(f"\n{'='*60}")
print("Macro Averages Across All Jobs")
print(f"{'='*60}")

macro_averages = {}
for config_name in configs.keys():
    p5_sum = 0.0
    r5_sum = 0.0
    ndcg5_sum = 0.0
    mrr_sum = 0.0
    count = 0
    
    for job_id in job_results:
        if config_name in job_results[job_id]:
            p5_sum += job_results[job_id][config_name]["p5"]
            r5_sum += job_results[job_id][config_name]["r5"]
            ndcg5_sum += job_results[job_id][config_name]["ndcg5"]
            mrr_sum += job_results[job_id][config_name]["mrr"]
            count += 1
    
    macro_averages[config_name] = {
        "p5": p5_sum / count if count > 0 else 0.0,
        "r5": r5_sum / count if count > 0 else 0.0,
        "ndcg5": ndcg5_sum / count if count > 0 else 0.0,
        "mrr": mrr_sum / count if count > 0 else 0.0,
    }

print(f"{'Config':12} | P@5    | R@5    | NDCG@5 | MRR")
print("-" * 60)
for config_name, metrics in macro_averages.items():
    print(f"{config_name:12} | {metrics['p5']:.3f}   | {metrics['r5']:.3f}   | {metrics['ndcg5']:.3f}   | {metrics['mrr']:.3f}")

print(f"\n{'='*60}")
print("Comparison to Baseline")
print(f"{'='*60}")

baseline = macro_averages["baseline"]
for config_name in ["semantic", "evidence", "hierarchy", "stuffing", "complete"]:
    metrics = macro_averages[config_name]
    print(f"\n{config_name} vs baseline:")
    print(f"  P@5: {metrics['p5']:.3f} (Δ{metrics['p5'] - baseline['p5']:+.3f})")
    print(f"  R@5: {metrics['r5']:.3f} (Δ{metrics['r5'] - baseline['r5']:+.3f})")
    print(f"  NDCG@5: {metrics['ndcg5']:.3f} (Δ{metrics['ndcg5'] - baseline['ndcg5']:+.3f})")
    print(f"  MRR: {metrics['mrr']:.3f} (Δ{metrics['mrr'] - baseline['mrr']:+.3f})")

print(f"\n=== Phase 4 Aggregate Evaluation Complete ===")
