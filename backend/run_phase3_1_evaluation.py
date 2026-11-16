"""
Phase 3.1 Integration Evaluation
Compare baseline scoring with integrated components.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation_dataset_extended import EXTENDED_EVALUATION_DATASET
from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills
import numpy as np

print("=== Phase 3.1 Integration Evaluation ===\n")

jobs = EXTENDED_EVALUATION_DATASET["job_descriptions"]
resumes = EXTENDED_EVALUATION_DATASET["resumes"]

# Focus on jd_001 (Backend Software Engineer)
job = jobs[0]
print(f"Evaluating job: {job['title']} ({job['id']})")
print(f"Required skills: {job['required_skills']}")
print(f"Preferred skills: {job['preferred_skills']}")
print()

# Filter resumes for this job
job_resumes = [r for r in resumes if r["for_job"] == job["id"]]
print(f"Total resumes for this job: {len(job_resumes)}")
print()

# Define configurations for comparison
configs = {
    "baseline": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=False,
    ),
    "baseline_hierarchy": ScoringConfig(
        use_skill_hierarchy=True,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=False,
    ),
    "baseline_demonstration": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=True,
        use_keyword_stuffing_penalty=False,
    ),
    "baseline_stuffing": ScoringConfig(
        use_skill_hierarchy=False,
        use_demonstration_levels=False,
        use_keyword_stuffing_penalty=True,
    ),
    "all_integrated": ScoringConfig(
        use_skill_hierarchy=True,
        use_demonstration_levels=True,
        use_keyword_stuffing_penalty=True,
    ),
}

results = {}

for config_name, config in configs.items():
    print(f"\n=== Evaluating: {config_name} ===")
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
            "test_category": resume.get("test_category", "N/A"),
            "required_coverage": result["required_skill_coverage"],
            "evidence_score": result["evidence_score"],
            "keyword_stuffing_penalty": result.get("keyword_stuffing_penalty", 0.0),
            "keyword_stuffing_analysis": result.get("keyword_stuffing_analysis"),
        })
    
    ranked.sort(key=lambda x: x["score"], reverse=True)
    results[config_name] = ranked
    
    # Show top 10
    print(f"\nTop 10 candidates:")
    for i, r in enumerate(ranked[:10]):
        penalty_str = f" (penalty: {r['keyword_stuffing_penalty']:.2f})" if r['keyword_stuffing_penalty'] > 0 else ""
        print(f"  {i+1}. {r['id']} ({r['name']}) - {r['score']:.2f}% - {r['relevance']}{penalty_str}")

# Compare keyword stuffer rankings
print("\n=== Keyword Stuffer Ranking Comparison ===")
stuffer_resumes = [r for r in job_resumes if r.get("test_category") == "claimed_vs_demonstrated"]
for stuffer in stuffer_resumes:
    print(f"\nResume: {stuffer['id']} ({stuffer['name']})")
    for config_name, ranked in results.items():
        for i, r in enumerate(ranked):
            if r["id"] == stuffer["id"]:
                print(f"  {config_name}: rank {i+1}, score {r['score']:.2f}%, penalty {r['keyword_stuffing_penalty']:.2f}")
                break

# Compare skill alias rankings
print("\n=== Skill Alias Ranking Comparison ===")
alias_resumes = [r for r in job_resumes if r.get("test_category") == "skill_alias"]
for alias in alias_resumes:
    print(f"\nResume: {alias['id']} ({alias['name']})")
    for config_name, ranked in results.items():
        for i, r in enumerate(ranked):
            if r["id"] == alias["id"]:
                print(f"  {config_name}: rank {i+1}, score {r['score']:.2f}%")
                break

# Compare related technology rankings
print("\n=== Related Technology Ranking Comparison ===")
related_resumes = [r for r in job_resumes if r.get("test_category") == "related_technology"]
for related in related_resumes:
    print(f"\nResume: {related['id']} ({related['name']})")
    for config_name, ranked in results.items():
        for i, r in enumerate(ranked):
            if r["id"] == related["id"]:
                print(f"  {config_name}: rank {i+1}, score {r['score']:.2f}%")
                break

# Calculate ranking metrics
print("\n=== Ranking Metrics Comparison ===")

def calculate_precision_at_k(ranked_ids, relevant_ids, k=5):
    """Calculate Precision@K."""
    top_k = ranked_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top_k / k if k > 0 else 0.0

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

# Get relevant resumes (high or medium relevance)
relevant_resumes = {r["id"]: 2 if r["relevance"] == "high" else 1 if r["relevance"] == "medium" else 0 for r in job_resumes}
relevant_ids = {rid for rid, rel in relevant_resumes.items() if rel > 0}

for config_name, ranked in results.items():
    ranked_ids = [r["id"] for r in ranked]
    p5 = calculate_precision_at_k(ranked_ids, relevant_ids, 5)
    ndcg5 = calculate_ndcg_at_k(ranked_ids, relevant_resumes, 5)
    
    print(f"\n{config_name}:")
    print(f"  Precision@5: {p5:.3f}")
    print(f"  NDCG@5: {ndcg5:.3f}")

print("\n=== Phase 3.1 Evaluation Complete ===")
