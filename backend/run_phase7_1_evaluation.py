"""
Phase 7.1 Fairness Improvements Benchmark Evaluation
Compare four configurations:
A. Original configuration
B. Education-aware keyword stuffing handling
C. Related-skill partial credit
D. Both improvements enabled
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills
from evaluation_dataset import EVALUATION_DATASET

print("=== Phase 7.1 Fairness Improvements Benchmark Evaluation ===\n")

# Define configurations
configs = {
    "A (Original)": ScoringConfig(
        use_keyword_stuffing_penalty=True,
        keyword_stuffing_education_aware=False,
        related_skill_credit_threshold=1.0,
    ),
    "B (Education-aware)": ScoringConfig(
        use_keyword_stuffing_penalty=True,
        keyword_stuffing_education_aware=True,
        related_skill_credit_threshold=1.0,
    ),
    "C (Partial credit)": ScoringConfig(
        use_keyword_stuffing_penalty=True,
        keyword_stuffing_education_aware=False,
        related_skill_credit_threshold=0.5,
    ),
    "D (Both)": ScoringConfig(
        use_keyword_stuffing_penalty=True,
        keyword_stuffing_education_aware=True,
        related_skill_credit_threshold=0.5,
    ),
}

# Metrics calculation
def calculate_metrics(resumes, job_data, config_name, config):
    """Calculate P@5, R@5, NDCG@5, MRR for a single job."""
    job_id = job_data["id"]
    job_text = job_data["description"]
    required_skills = job_data["required_skills"]
    preferred_skills = job_data["preferred_skills"]
    
    scoring_service = ScoringService(config=config)
    
    # Score all resumes
    scored_resumes = []
    for resume_key, resume_data in resumes.items():
        if resume_data.get("for_job") == job_id:
            resume_text = resume_data["content"]
            resume_skills = extract_skills(resume_text)["technical_skills"]
            
            result = scoring_service.compute_match(
                resume_text=resume_text,
                job_text=job_text,
                resume_skills=resume_skills,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                use_semantic=False,  # Disable semantic for consistency
            )
            
            scored_resumes.append({
                "resume_id": resume_key,
                "score": result["overall_score"],
                "relevance": resume_data["relevance"],
            })
    
    # Sort by score descending
    scored_resumes.sort(key=lambda x: x["score"], reverse=True)
    
    # Calculate metrics
    top_5 = scored_resumes[:5]
    relevant_count = sum(1 for r in scored_resumes if r["relevance"] in ["high", "medium"])
    
    # Precision@5
    precision_at_5 = sum(1 for r in top_5 if r["relevance"] in ["high", "medium"]) / len(top_5) if top_5 else 0.0
    
    # Recall@5
    recall_at_5 = sum(1 for r in top_5 if r["relevance"] in ["high", "medium"]) / relevant_count if relevant_count > 0 else 0.0
    
    # NDCG@5
    def dcg(relevances):
        return sum((2**rel - 1) / (i + 1) for i, rel in enumerate(relevances))
    
    relevance_map = {"high": 2, "medium": 1, "low": 0}
    actual_relevances = [relevance_map[r["relevance"]] for r in top_5]
    ideal_relevances = sorted([relevance_map[r["relevance"]] for r in scored_resumes], reverse=True)[:5]
    
    dcg_score = dcg(actual_relevances)
    idcg_score = dcg(ideal_relevances)
    ndcg_at_5 = dcg_score / idcg_score if idcg_score > 0 else 0.0
    
    # MRR
    mrr = 0.0
    for i, r in enumerate(scored_resumes):
        if r["relevance"] in ["high", "medium"]:
            mrr = 1.0 / (i + 1)
            break
    
    # Count keyword stuffing detections
    stuffing_count = 0
    for resume_key, resume_data in resumes.items():
        if resume_data.get("for_job") == job_id:
            resume_text = resume_data["content"]
            resume_skills = extract_skills(resume_text)["technical_skills"]
            
            result = scoring_service.compute_match(
                resume_text=resume_text,
                job_text=job_text,
                resume_skills=resume_skills,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                use_semantic=False,
            )
            
            if result["keyword_stuffing_analysis"] and result["keyword_stuffing_analysis"]["is_stuffed"]:
                stuffing_count += 1
    
    return {
        "precision_at_5": precision_at_5,
        "recall_at_5": recall_at_5,
        "ndcg_at_5": ndcg_at_5,
        "mrr": mrr,
        "stuffing_count": stuffing_count,
        "total_resumes": len(scored_resumes),
    }

# Run evaluation for all jobs and configurations
resumes = {r["id"]: r for r in EVALUATION_DATASET["resumes"]}
job_descriptions = {jd["id"]: jd for jd in EVALUATION_DATASET["job_descriptions"]}
job_ids = list(job_descriptions.keys())

results = {}
for config_name, config in configs.items():
    print(f"Evaluating {config_name}...")
    config_results = {}
    
    for job_id in job_ids:
        job_data = job_descriptions[job_id]
        metrics = calculate_metrics(resumes, job_data, config_name, config)
        config_results[job_id] = metrics
    
    results[config_name] = config_results

# Print results
print("\n" + "="*80)
print("RESULTS BY JOB")
print("="*80)

for job_id in job_ids:
    print(f"\nJob: {job_id}")
    print("-"*80)
    print(f"{'Config':<20} {'P@5':<8} {'R@5':<8} {'NDCG@5':<10} {'MRR':<8} {'Stuffed':<10} {'Total':<8}")
    print("-"*80)
    
    for config_name in configs.keys():
        metrics = results[config_name][job_id]
        print(f"{config_name:<20} {metrics['precision_at_5']:.3f}  {metrics['recall_at_5']:.3f}  {metrics['ndcg_at_5']:.3f}    {metrics['mrr']:.3f}  {metrics['stuffing_count']:<10} {metrics['total_resumes']:<8}")

# Calculate macro averages
print("\n" + "="*80)
print("MACRO AVERAGES")
print("="*80)
print(f"{'Config':<20} {'P@5':<8} {'R@5':<8} {'NDCG@5':<10} {'MRR':<8}")
print("-"*80)

macro_averages = {}
for config_name in configs.keys():
    avg_p5 = sum(results[config_name][j]["precision_at_5"] for j in job_ids) / len(job_ids)
    avg_r5 = sum(results[config_name][j]["recall_at_5"] for j in job_ids) / len(job_ids)
    avg_ndcg = sum(results[config_name][j]["ndcg_at_5"] for j in job_ids) / len(job_ids)
    avg_mrr = sum(results[config_name][j]["mrr"] for j in job_ids) / len(job_ids)
    
    macro_averages[config_name] = {
        "precision_at_5": avg_p5,
        "recall_at_5": avg_r5,
        "ndcg_at_5": avg_ndcg,
        "mrr": avg_mrr,
    }
    
    print(f"{config_name:<20} {avg_p5:.3f}  {avg_r5:.3f}  {avg_ndcg:.3f}    {avg_mrr:.3f}")

# Compare configurations
print("\n" + "="*80)
print("CONFIGURATION COMPARISONS (vs Original)")
print("="*80)

baseline = macro_averages["A (Original)"]
for config_name in ["B (Education-aware)", "C (Partial credit)", "D (Both)"]:
    metrics = macro_averages[config_name]
    print(f"\n{config_name}:")
    print(f"  P@5: {metrics['precision_at_5']:.3f} (Δ{metrics['precision_at_5'] - baseline['precision_at_5']:+.3f})")
    print(f"  R@5: {metrics['recall_at_5']:.3f} (Δ{metrics['recall_at_5'] - baseline['recall_at_5']:+.3f})")
    print(f"  NDCG@5: {metrics['ndcg_at_5']:.3f} (Δ{metrics['ndcg_at_5'] - baseline['ndcg_at_5']:+.3f})")
    print(f"  MRR: {metrics['mrr']:.3f} (Δ{metrics['mrr'] - baseline['mrr']:+.3f})")

print("\n=== Phase 7.1 Benchmark Evaluation Complete ===")
