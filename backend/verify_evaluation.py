"""
Verify evaluation metrics calculations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.evaluation.evaluation_dataset import get_all_examples, RelevanceLabel
from app.evaluation.evaluation_metrics import RankingMetrics

def main():
    examples = get_all_examples()
    
    # Group by job
    job_examples = {}
    for ex in examples:
        if ex.job_id not in job_examples:
            job_examples[ex.job_id] = []
        job_examples[ex.job_id].append(ex)
    
    print("=" * 60)
    print("EVALUATION DATASET ANALYSIS")
    print("=" * 60)
    
    for job_id, job_ex_list in job_examples.items():
        print(f"\nJob: {job_id}")
        print(f"Total candidates: {len(job_ex_list)}")
        
        # Count by relevance
        relevance_counts = {}
        for ex in job_ex_list:
            rel = ex.expected_relevance.value
            relevance_counts[rel] = relevance_counts.get(rel, 0) + 1
        
        print("Relevance distribution:")
        for rel, count in sorted(relevance_counts.items(), reverse=True):
            label = RelevanceLabel(rel).name
            print(f"  {label} ({rel}): {count}")
        
        # Simulate ranking (using simple skill match as proxy)
        # In real evaluation, this would use actual scores
        print("\nCandidate details:")
        for ex in job_ex_list:
            print(f"  {ex.resume_id}: {ex.expected_relevance.name} ({ex.expected_relevance.value}) - {ex.reasoning}")
    
    print("\n" + "=" * 60)
    print("METRICS CALCULATION VERIFICATION")
    print("=" * 60)
    
    # Test metrics calculation manually
    print("\nTest case: job_backend_001")
    backend_job = job_examples["job_backend_001"]
    
    # Assume ranking based on relevance (perfect ranking for test)
    ranked_ids = [ex.resume_id for ex in sorted(backend_job, key=lambda x: x.expected_relevance.value, reverse=True)]
    relevant_ids = [ex.resume_id for ex in backend_job if ex.expected_relevance.value >= RelevanceLabel.PARTIALLY_RELEVANT.value]
    
    print(f"Ranked IDs: {ranked_ids}")
    print(f"Relevant IDs: {relevant_ids}")
    
    precision_5 = RankingMetrics.precision_at_k(relevant_ids, ranked_ids, 5)
    recall_5 = RankingMetrics.recall_at_k(relevant_ids, ranked_ids, 5)
    
    print(f"\nCalculated Precision@5: {precision_5}")
    print(f"Calculated Recall@5: {recall_5}")
    
    # NDCG calculation
    relevance_dict = {ex.resume_id: ex.expected_relevance.value for ex in backend_job}
    ndcg_5 = RankingMetrics.ndcg_at_k(relevance_dict, ranked_ids, 5)
    print(f"Calculated NDCG@5: {ndcg_5}")
    
    print("\n" + "=" * 60)
    print("SKILL EXTRACTION METRICS ANALYSIS")
    print("=" * 60)
    
    from app.services.skill_service import extract_skills
    
    print("\nSkill extraction for backend job candidates:")
    for ex in backend_job:
        skills = extract_skills(ex.resume_text)
        predicted = skills.get("technical_skills", [])
        actual = ex.required_skills
        
        from app.evaluation.evaluation_metrics import SkillExtractionMetrics
        precision = SkillExtractionMetrics.precision(predicted, actual)
        recall = SkillExtractionMetrics.recall(predicted, actual)
        f1 = SkillExtractionMetrics.f1_score(predicted, actual)
        
        print(f"\n{ex.resume_id}:")
        print(f"  Predicted: {predicted}")
        print(f"  Actual (required): {actual}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1: {f1:.4f}")

if __name__ == "__main__":
    main()
