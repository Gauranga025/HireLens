"""
HireLens Matching Quality Evaluation
Runs ablation experiments and calculates ranking metrics.
"""
import sys
import os
import time
import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation_dataset import EVALUATION_DATASET
from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills, match_skills_to_requirements
from app.services.semantic_matching_service import SemanticMatchingService


@dataclass
class EvaluationResult:
    """Result of a single evaluation run."""
    job_id: str
    experiment: str
    ranked_resumes: List[Tuple[str, float]]  # (resume_id, score)
    precision_at_5: float
    recall_at_5: float
    ndcg_at_5: float
    mrr: float
    skill_precision: float
    skill_recall: float


def calculate_precision_at_k(ranked_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Calculate Precision@K."""
    if k == 0:
        return 0.0
    top_k = ranked_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top_k / k


def calculate_recall_at_k(ranked_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Calculate Recall@K."""
    if not relevant_ids:
        return 0.0
    top_k = ranked_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top_k / len(relevant_ids)


def calculate_ndcg_at_k(ranked_ids: List[str], relevance_scores: Dict[str, int], k: int) -> float:
    """Calculate NDCG@K."""
    if k == 0:
        return 0.0
    
    # DCG
    dcg = 0.0
    for i, rid in enumerate(ranked_ids[:k]):
        relevance = relevance_scores.get(rid, 0)
        dcg += relevance / np.log2(i + 2)  # log2(i+2) for 1-indexed rank
    
    # IDCG (ideal ranking)
    ideal_relevances = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_relevances):
        idcg += rel / np.log2(i + 2)
    
    if idcg == 0:
        return 0.0
    return dcg / idcg


def calculate_mrr(ranked_ids: List[str], relevant_ids: List[str]) -> float:
    """Calculate Mean Reciprocal Rank."""
    for i, rid in enumerate(ranked_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def calculate_skill_precision_recall(
    resume_skills: List[str],
    required_skills: List[str],
    human_matches: Dict[str, str]
) -> Tuple[float, float]:
    """Calculate skill precision and recall based on human labels."""
    if not required_skills:
        return 0.0, 0.0
    
    # Count correctly matched skills
    correct_matches = 0
    for skill in required_skills:
        human_label = human_matches.get(skill, "missing")
        if human_label == "matched" or human_label.startswith("matched"):
            correct_matches += 1
    
    # Precision: correct matches / total matches by system
    system_matches = sum(1 for s in required_skills if s in resume_skills)
    precision = correct_matches / system_matches if system_matches > 0 else 0.0
    
    # Recall: correct matches / total required skills
    recall = correct_matches / len(required_skills)
    
    return precision, recall


def run_baseline_evaluation(job: Dict, resumes: List[Dict]) -> EvaluationResult:
    """Run baseline evaluation (required/preferred skills only)."""
    config = ScoringConfig(
        required_skill_weight=0.7,
        preferred_skill_weight=0.3,
        semantic_weight=0.0,
        evidence_weight=0.0,
        tfidf_weight=0.0
    )
    scoring_service = ScoringService(config=config)
    
    ranked = []
    for resume in resumes:
        resume_skills = extract_skills(resume["content"])["technical_skills"]
        
        result = scoring_service.compute_match(
            resume_text=resume["content"],
            job_text=job["description"],
            resume_skills=resume_skills,
            required_skills=job["required_skills"],
            preferred_skills=job["preferred_skills"],
            use_semantic=False,
        )
        
        ranked.append((resume["id"], result["overall_score"]))
    
    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked_ids = [r[0] for r in ranked]
    
    # Calculate metrics
    relevant_resumes = [r["id"] for r in resumes if r["for_job"] == job["id"] and r["relevance"] in ["high", "medium"]]
    relevance_scores = {r["id"]: 3 if r["relevance"] == "high" else 2 if r["relevance"] == "medium" else 1 
                       for r in resumes if r["for_job"] == job["id"]}
    
    precision_at_5 = calculate_precision_at_k(ranked_ids, relevant_resumes, 5)
    recall_at_5 = calculate_recall_at_k(ranked_ids, relevant_resumes, 5)
    ndcg_at_5 = calculate_ndcg_at_k(ranked_ids, relevance_scores, 5)
    mrr = calculate_mrr(ranked_ids, relevant_resumes)
    
    # Skill metrics (use first relevant resume for simplicity)
    skill_precision, skill_recall = 0.0, 0.0
    for resume in resumes:
        if resume["for_job"] == job["id"] and "skill_matches" in resume:
            resume_skills = extract_skills(resume["content"])["technical_skills"]
            skill_precision, skill_recall = calculate_skill_precision_recall(
                resume_skills, job["required_skills"], resume["skill_matches"]
            )
            break
    
    return EvaluationResult(
        job_id=job["id"],
        experiment="baseline",
        ranked_resumes=ranked,
        precision_at_5=precision_at_5,
        recall_at_5=recall_at_5,
        ndcg_at_5=ndcg_at_5,
        mrr=mrr,
        skill_precision=skill_precision,
        skill_recall=skill_recall
    )


def run_ablation_b(job: Dict, resumes: List[Dict]) -> EvaluationResult:
    """Run ablation B (skills + semantic)."""
    config = ScoringConfig(
        required_skill_weight=0.5,
        preferred_skill_weight=0.2,
        semantic_weight=0.3,
        evidence_weight=0.0,
        tfidf_weight=0.0
    )
    scoring_service = ScoringService(config=config)
    
    ranked = []
    for resume in resumes:
        resume_skills = extract_skills(resume["content"])["technical_skills"]
        
        result = scoring_service.compute_match(
            resume_text=resume["content"],
            job_text=job["description"],
            resume_skills=resume_skills,
            required_skills=job["required_skills"],
            preferred_skills=job["preferred_skills"],
            use_semantic=True,
        )
        
        ranked.append((resume["id"], result["overall_score"]))
    
    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked_ids = [r[0] for r in ranked]
    
    relevant_resumes = [r["id"] for r in resumes if r["for_job"] == job["id"] and r["relevance"] in ["high", "medium"]]
    relevance_scores = {r["id"]: 3 if r["relevance"] == "high" else 2 if r["relevance"] == "medium" else 1 
                       for r in resumes if r["for_job"] == job["id"]}
    
    precision_at_5 = calculate_precision_at_k(ranked_ids, relevant_resumes, 5)
    recall_at_5 = calculate_recall_at_k(ranked_ids, relevant_resumes, 5)
    ndcg_at_5 = calculate_ndcg_at_k(ranked_ids, relevance_scores, 5)
    mrr = calculate_mrr(ranked_ids, relevant_resumes)
    
    skill_precision, skill_recall = 0.0, 0.0
    for resume in resumes:
        if resume["for_job"] == job["id"] and "skill_matches" in resume:
            resume_skills = extract_skills(resume["content"])["technical_skills"]
            skill_precision, skill_recall = calculate_skill_precision_recall(
                resume_skills, job["required_skills"], resume["skill_matches"]
            )
            break
    
    return EvaluationResult(
        job_id=job["id"],
        experiment="ablation_b",
        ranked_resumes=ranked,
        precision_at_5=precision_at_5,
        recall_at_5=recall_at_5,
        ndcg_at_5=ndcg_at_5,
        mrr=mrr,
        skill_precision=skill_precision,
        skill_recall=skill_recall
    )


def run_ablation_c(job: Dict, resumes: List[Dict]) -> EvaluationResult:
    """Run ablation C (skills + semantic + evidence)."""
    config = ScoringConfig(
        required_skill_weight=0.4,
        preferred_skill_weight=0.15,
        semantic_weight=0.25,
        evidence_weight=0.2,
        tfidf_weight=0.0
    )
    scoring_service = ScoringService(config=config)
    
    ranked = []
    for resume in resumes:
        resume_skills = extract_skills(resume["content"])["technical_skills"]
        
        result = scoring_service.compute_match(
            resume_text=resume["content"],
            job_text=job["description"],
            resume_skills=resume_skills,
            required_skills=job["required_skills"],
            preferred_skills=job["preferred_skills"],
            use_semantic=True,
        )
        
        ranked.append((resume["id"], result["overall_score"]))
    
    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked_ids = [r[0] for r in ranked]
    
    relevant_resumes = [r["id"] for r in resumes if r["for_job"] == job["id"] and r["relevance"] in ["high", "medium"]]
    relevance_scores = {r["id"]: 3 if r["relevance"] == "high" else 2 if r["relevance"] == "medium" else 1 
                       for r in resumes if r["for_job"] == job["id"]}
    
    precision_at_5 = calculate_precision_at_k(ranked_ids, relevant_resumes, 5)
    recall_at_5 = calculate_recall_at_k(ranked_ids, relevant_resumes, 5)
    ndcg_at_5 = calculate_ndcg_at_k(ranked_ids, relevance_scores, 5)
    mrr = calculate_mrr(ranked_ids, relevant_resumes)
    
    skill_precision, skill_recall = 0.0, 0.0
    for resume in resumes:
        if resume["for_job"] == job["id"] and "skill_matches" in resume:
            resume_skills = extract_skills(resume["content"])["technical_skills"]
            skill_precision, skill_recall = calculate_skill_precision_recall(
                resume_skills, job["required_skills"], resume["skill_matches"]
            )
            break
    
    return EvaluationResult(
        job_id=job["id"],
        experiment="ablation_c",
        ranked_resumes=ranked,
        precision_at_5=precision_at_5,
        recall_at_5=recall_at_5,
        ndcg_at_5=ndcg_at_5,
        mrr=mrr,
        skill_precision=skill_precision,
        skill_recall=skill_recall
    )


def run_complete_evaluation(job: Dict, resumes: List[Dict]) -> EvaluationResult:
    """Run complete scoring evaluation (current formula)."""
    scoring_service = ScoringService()  # Default config
    
    ranked = []
    for resume in resumes:
        resume_skills = extract_skills(resume["content"])["technical_skills"]
        
        result = scoring_service.compute_match(
            resume_text=resume["content"],
            job_text=job["description"],
            resume_skills=resume_skills,
            required_skills=job["required_skills"],
            preferred_skills=job["preferred_skills"],
            use_semantic=True,
        )
        
        ranked.append((resume["id"], result["overall_score"]))
    
    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked_ids = [r[0] for r in ranked]
    
    relevant_resumes = [r["id"] for r in resumes if r["for_job"] == job["id"] and r["relevance"] in ["high", "medium"]]
    relevance_scores = {r["id"]: 3 if r["relevance"] == "high" else 2 if r["relevance"] == "medium" else 1 
                       for r in resumes if r["for_job"] == job["id"]}
    
    precision_at_5 = calculate_precision_at_k(ranked_ids, relevant_resumes, 5)
    recall_at_5 = calculate_recall_at_k(ranked_ids, relevant_resumes, 5)
    ndcg_at_5 = calculate_ndcg_at_k(ranked_ids, relevance_scores, 5)
    mrr = calculate_mrr(ranked_ids, relevant_resumes)
    
    skill_precision, skill_recall = 0.0, 0.0
    for resume in resumes:
        if resume["for_job"] == job["id"] and "skill_matches" in resume:
            resume_skills = extract_skills(resume["content"])["technical_skills"]
            skill_precision, skill_recall = calculate_skill_precision_recall(
                resume_skills, job["required_skills"], resume["skill_matches"]
            )
            break
    
    return EvaluationResult(
        job_id=job["id"],
        experiment="complete",
        ranked_resumes=ranked,
        precision_at_5=precision_at_5,
        recall_at_5=recall_at_5,
        ndcg_at_5=ndcg_at_5,
        mrr=mrr,
        skill_precision=skill_precision,
        skill_recall=skill_recall
    )


def measure_performance():
    """Measure performance metrics."""
    print("\n=== Performance Measurement ===\n")
    
    # Model loading time
    semantic_service = SemanticMatchingService()
    start = time.time()
    is_available = semantic_service.is_available()
    load_time = time.time() - start
    print(f"Model loading time: {load_time:.3f}s")
    print(f"Model available: {is_available}")
    
    # Embedding generation latency
    test_text = "Python developer with FastAPI experience building REST APIs"
    start = time.time()
    embedding = semantic_service.compute_embedding(test_text)
    embedding_time = time.time() - start
    print(f"Single embedding generation: {embedding_time:.3f}s")
    print(f"Embedding dimensions: {embedding.shape if embedding is not None else 'N/A'}")
    
    # Cosine similarity latency
    text2 = "Built RESTful web services using Python"
    start = time.time()
    similarity = semantic_service.compute_similarity(test_text, text2)
    similarity_time = time.time() - start
    print(f"Cosine similarity calculation: {similarity_time:.3f}s")
    print(f"Similarity score: {similarity}")
    
    # Batch embedding latency
    texts = [test_text] * 10
    start = time.time()
    embeddings = semantic_service.compute_embeddings(texts)
    batch_time = time.time() - start
    print(f"Batch embedding (10 texts): {batch_time:.3f}s")
    print(f"Average per text: {batch_time/10:.3f}s")
    
    # Single resume matching latency
    from evaluation_dataset import EVALUATION_DATASET
    job = EVALUATION_DATASET["job_descriptions"][0]
    resume = EVALUATION_DATASET["resumes"][0]
    
    scoring_service = ScoringService()
    resume_skills = extract_skills(resume["content"])["technical_skills"]
    
    start = time.time()
    result = scoring_service.compute_match(
        resume_text=resume["content"],
        job_text=job["description"],
        resume_skills=resume_skills,
        required_skills=job["required_skills"],
        preferred_skills=job["preferred_skills"],
        use_semantic=True,
    )
    match_time = time.time() - start
    print(f"Single resume matching: {match_time:.3f}s")
    print(f"Overall score: {result['overall_score']:.2f}%")
    
    # Batch processing (10 resumes)
    start = time.time()
    for resume in EVALUATION_DATASET["resumes"][:10]:
        resume_skills = extract_skills(resume["content"])["technical_skills"]
        result = scoring_service.compute_match(
            resume_text=resume["content"],
            job_text=job["description"],
            resume_skills=resume_skills,
            required_skills=job["required_skills"],
            preferred_skills=job["preferred_skills"],
            use_semantic=True,
        )
    batch_match_time = time.time() - start
    print(f"Batch matching (10 resumes): {batch_match_time:.3f}s")
    print(f"Average per resume: {batch_match_time/10:.3f}s")


def main():
    print("=== HireLens Matching Quality Evaluation ===\n")
    
    jobs = EVALUATION_DATASET["job_descriptions"]
    resumes = EVALUATION_DATASET["resumes"]
    
    all_results = []
    
    # Run evaluations for each job
    for job in jobs:
        print(f"\nEvaluating job: {job['title']} ({job['id']})")
        
        # Baseline
        print("  Running baseline evaluation...")
        baseline = run_baseline_evaluation(job, resumes)
        all_results.append(baseline)
        print(f"    P@5: {baseline.precision_at_5:.3f}, R@5: {baseline.recall_at_5:.3f}, NDCG@5: {baseline.ndcg_at_5:.3f}")
        
        # Ablation B
        print("  Running ablation B (skills + semantic)...")
        ablation_b = run_ablation_b(job, resumes)
        all_results.append(ablation_b)
        print(f"    P@5: {ablation_b.precision_at_5:.3f}, R@5: {ablation_b.recall_at_5:.3f}, NDCG@5: {ablation_b.ndcg_at_5:.3f}")
        
        # Ablation C
        print("  Running ablation C (skills + semantic + evidence)...")
        ablation_c = run_ablation_c(job, resumes)
        all_results.append(ablation_c)
        print(f"    P@5: {ablation_c.precision_at_5:.3f}, R@5: {ablation_c.recall_at_5:.3f}, NDCG@5: {ablation_c.ndcg_at_5:.3f}")
        
        # Complete
        print("  Running complete evaluation...")
        complete = run_complete_evaluation(job, resumes)
        all_results.append(complete)
        print(f"    P@5: {complete.precision_at_5:.3f}, R@5: {complete.recall_at_5:.3f}, NDCG@5: {complete.ndcg_at_5:.3f}")
    
    # Calculate aggregate metrics
    print("\n=== Aggregate Results ===\n")
    
    experiments = ["baseline", "ablation_b", "ablation_c", "complete"]
    
    for exp in experiments:
        exp_results = [r for r in all_results if r.experiment == exp]
        avg_precision = np.mean([r.precision_at_5 for r in exp_results])
        avg_recall = np.mean([r.recall_at_5 for r in exp_results])
        avg_ndcg = np.mean([r.ndcg_at_5 for r in exp_results])
        avg_mrr = np.mean([r.mrr for r in exp_results])
        avg_skill_precision = np.mean([r.skill_precision for r in exp_results])
        avg_skill_recall = np.mean([r.skill_recall for r in exp_results])
        
        print(f"{exp}:")
        print(f"  Precision@5: {avg_precision:.3f}")
        print(f"  Recall@5: {avg_recall:.3f}")
        print(f"  NDCG@5: {avg_ndcg:.3f}")
        print(f"  MRR: {avg_mrr:.3f}")
        print(f"  Skill Precision: {avg_skill_precision:.3f}")
        print(f"  Skill Recall: {avg_skill_recall:.3f}")
        print()
    
    # Measure performance
    measure_performance()
    
    # Save results
    results_dict = []
    for r in all_results:
        results_dict.append({
            "job_id": r.job_id,
            "experiment": r.experiment,
            "precision_at_5": r.precision_at_5,
            "recall_at_5": r.recall_at_5,
            "ndcg_at_5": r.ndcg_at_5,
            "mrr": r.mrr,
            "skill_precision": r.skill_precision,
            "skill_recall": r.skill_recall,
            "ranked_resumes": r.ranked_resumes[:10]  # Top 10
        })
    
    with open("evaluation_results.json", "w") as f:
        json.dump(results_dict, f, indent=2)
    
    print("\nResults saved to evaluation_results.json")


if __name__ == "__main__":
    main()
