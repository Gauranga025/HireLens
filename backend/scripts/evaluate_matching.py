"""
Evaluation script for matching accuracy assessment.
Runs baseline and new matching methods on synthetic dataset.
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.evaluation_dataset import get_all_examples, RelevanceLabel
from app.evaluation.evaluation_metrics import (
    RankingMetrics,
    SkillExtractionMetrics,
    EvidenceMetrics,
    EvaluationReport,
)
from app.services.skill_service import extract_skills, match_skills_to_requirements

# Try to import scoring service, handle gracefully if dependencies missing
try:
    from app.services.scoring_service import ScoringService
    SCORING_AVAILABLE = True
except ImportError:
    SCORING_AVAILABLE = False
    print("Warning: Scoring service unavailable (missing dependencies). Using baseline only.")

try:
    from app.services.matching_service import compute_match as compute_match_baseline
    BASELINE_AVAILABLE = True
except ImportError:
    BASELINE_AVAILABLE = False
    print("Warning: Baseline matching unavailable (missing dependencies).")


def run_evaluation() -> Dict[str, Any]:
    """
    Run full evaluation on synthetic dataset.
    
    Returns:
        Evaluation results dictionary.
    """
    print("Starting HireLens matching evaluation...")
    
    examples = get_all_examples()
    print(f"Loaded {len(examples)} evaluation examples")
    
    report = EvaluationReport()
    
    # Initialize services if available
    scoring_service = ScoringService() if SCORING_AVAILABLE else None
    
    # Group examples by job
    job_examples: Dict[str, List] = {}
    for ex in examples:
        if ex.job_id not in job_examples:
            job_examples[ex.job_id] = []
        job_examples[ex.job_id].append(ex)
    
    # Run evaluation for each job
    all_ranking_results = []
    skill_extraction_results = []
    
    for job_id, job_examples_list in job_examples.items():
        print(f"\nEvaluating job: {job_id}")
        
        # Get job details from first example
        job = job_examples_list[0]
        job_text = job.job_description
        required_skills = job.required_skills
        preferred_skills = job.preferred_skills
        
        # Calculate scores for each candidate
        candidate_scores = []
        
        for ex in job_examples_list:
            # Extract skills from resume
            skills_data = extract_skills(ex.resume_text)
            resume_skills = skills_data.get("technical_skills", [])
            
            # Calculate baseline score if available
            if BASELINE_AVAILABLE:
                baseline_result = compute_match_baseline(
                    ex.resume_text,
                    job_text,
                    resume_skills,
                    required_skills,
                    use_semantic=False,
                )
                baseline_score = baseline_result["overall_score"]
            else:
                baseline_score = 0.0
            
            # Calculate new evidence-aware score if available
            if SCORING_AVAILABLE:
                new_result = scoring_service.compute_match(
                    ex.resume_text,
                    job_text,
                    resume_skills,
                    required_skills,
                    preferred_skills,
                    use_semantic=False,  # Disable semantic for consistent evaluation
                )
                new_score = new_result["overall_score"]
                required_coverage = new_result["required_skill_coverage"]
                matched_skills = new_result["matched_skills"]
                missing_skills = new_result["missing_skills"]
            else:
                # Fallback: simple skill match percentage
                skill_match = match_skills_to_requirements(resume_skills, required_skills)
                new_score = skill_match["match_percentage"]
                required_coverage = skill_match["match_percentage"]
                matched_skills = skill_match["matched"]
                missing_skills = skill_match["missing"]
            
            candidate_scores.append({
                "resume_id": ex.resume_id,
                "expected_relevance": ex.expected_relevance.value,
                "baseline_score": baseline_score,
                "new_score": new_score,
                "required_coverage": required_coverage,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            })
            
            # Collect skill extraction metrics
            skill_extraction_results.append({
                "predicted": resume_skills,
                "actual": required_skills,  # Simplified: use required as ground truth
            })
        
        # Sort by new score (descending)
        candidate_scores.sort(key=lambda x: x["new_score"], reverse=True)
        
        # Calculate ranking metrics
        relevant_ids = [
            c["resume_id"] for c in candidate_scores
            if c["expected_relevance"] >= RelevanceLabel.PARTIALLY_RELEVANT.value
        ]
        retrieved_ids = [c["resume_id"] for c in candidate_scores]
        
        # Create relevance dict for NDCG
        relevance_dict = {
            c["resume_id"]: c["expected_relevance"]
            for c in candidate_scores
        }
        
        # Calculate metrics
        precision_5 = RankingMetrics.precision_at_k(relevant_ids, retrieved_ids, 5)
        recall_5 = RankingMetrics.recall_at_k(relevant_ids, retrieved_ids, 5)
        ndcg_5 = RankingMetrics.ndcg_at_k(relevance_dict, retrieved_ids, 5)
        mrr = RankingMetrics.mean_reciprocal_rank(relevant_ids, retrieved_ids)
        
        all_ranking_results.append({
            "job_id": job_id,
            "precision_at_5": precision_5,
            "recall_at_5": recall_5,
            "ndcg_at_5": ndcg_5,
            "mrr": mrr,
        })
        
        print(f"  Precision@5: {precision_5:.4f}")
        print(f"  Recall@5: {recall_5:.4f}")
        print(f"  NDCG@5: {ndcg_5:.4f}")
        print(f"  MRR: {mrr:.4f}")
    
    # Aggregate ranking metrics (average across jobs)
    if all_ranking_results:
        avg_precision = sum(r["precision_at_5"] for r in all_ranking_results) / len(all_ranking_results)
        avg_recall = sum(r["recall_at_5"] for r in all_ranking_results) / len(all_ranking_results)
        avg_ndcg = sum(r["ndcg_at_5"] for r in all_ranking_results) / len(all_ranking_results)
        avg_mrr = sum(r["mrr"] for r in all_ranking_results) / len(all_ranking_results)
        
        report.add_ranking_metrics(avg_precision, avg_recall, avg_ndcg, avg_mrr)
    
    # Calculate skill extraction metrics
    skill_precisions = []
    skill_recalls = []
    skill_f1s = []
    
    for result in skill_extraction_results:
        precision = SkillExtractionMetrics.precision(
            result["predicted"],
            result["actual"],
        )
        recall = SkillExtractionMetrics.recall(
            result["predicted"],
            result["actual"],
        )
        f1 = SkillExtractionMetrics.f1_score(
            result["predicted"],
            result["actual"],
        )
        
        skill_precisions.append(precision)
        skill_recalls.append(recall)
        skill_f1s.append(f1)
    
    if skill_precisions:
        avg_skill_precision = sum(skill_precisions) / len(skill_precisions)
        avg_skill_recall = sum(skill_recalls) / len(skill_recalls)
        avg_skill_f1 = sum(skill_f1s) / len(skill_f1s)
        
        report.add_skill_extraction_metrics(avg_skill_precision, avg_skill_recall, avg_skill_f1)
    
    # Generate final report
    report_dict = report.to_dict()
    report_dict["total_examples"] = len(examples)
    report_dict["total_jobs"] = len(job_examples)
    report_dict["per_job_results"] = all_ranking_results
    report_dict["scoring_available"] = SCORING_AVAILABLE
    report_dict["baseline_available"] = BASELINE_AVAILABLE
    
    return report_dict


def main():
    """Main entry point."""
    try:
        results = run_evaluation()
        
        # Save JSON report
        output_dir = Path(__file__).parent.parent / "evaluation_results"
        output_dir.mkdir(exist_ok=True)
        
        json_path = output_dir / "evaluation_report.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nJSON report saved to: {json_path}")
        
        # Generate markdown report
        report = EvaluationReport()
        report.add_ranking_metrics(
            results["ranking_metrics"]["precision_at_5"],
            results["ranking_metrics"]["recall_at_5"],
            results["ranking_metrics"]["ndcg_at_5"],
            results["ranking_metrics"]["mrr"],
        )
        report.add_skill_extraction_metrics(
            results["skill_extraction_metrics"]["precision"],
            results["skill_extraction_metrics"]["recall"],
            results["skill_extraction_metrics"]["f1_score"],
        )
        
        markdown = report.to_markdown()
        markdown_path = output_dir / "evaluation_report.md"
        with open(markdown_path, "w") as f:
            f.write(markdown)
        
        print(f"Markdown report saved to: {markdown_path}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Examples: {results['total_examples']}")
        print(f"Total Jobs: {results['total_jobs']}")
        print(f"\nRanking Metrics:")
        print(f"  Precision@5: {results['ranking_metrics']['precision_at_5']:.4f}")
        print(f"  Recall@5: {results['ranking_metrics']['recall_at_5']:.4f}")
        print(f"  NDCG@5: {results['ranking_metrics']['ndcg_at_5']:.4f}")
        print(f"  MRR: {results['ranking_metrics']['mrr']:.4f}")
        print(f"\nSkill Extraction Metrics:")
        print(f"  Precision: {results['skill_extraction_metrics']['precision']:.4f}")
        print(f"  Recall: {results['skill_extraction_metrics']['recall']:.4f}")
        print(f"  F1 Score: {results['skill_extraction_metrics']['f1_score']:.4f}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
