"""
Phase 4 Performance Measurement
Measure processing time for different batch sizes.
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills
from app.services.semantic_matching_service import SemanticMatchingService

print("=== Phase 4 Performance Measurement ===\n")

# Test resume
resume_text = """
John Smith
Backend Developer

Skills: Python, FastAPI, PostgreSQL, REST API, Docker, AWS

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
  - Deployed applications using Docker on AWS
"""

job_description = """
We are looking for a Backend Software Engineer to join our team.

Required Skills:
- Python
- FastAPI
- PostgreSQL
- REST API development

Preferred Skills:
- Docker
- AWS
- Kubernetes
""".strip()

required_skills = ["Python", "FastAPI", "PostgreSQL", "REST API"]
preferred_skills = ["Docker", "AWS", "Kubernetes"]

resume_skills = extract_skills(resume_text)["technical_skills"]

# Test batch sizes
batch_sizes = [1, 10, 25, 50]
runs_per_size = 3

print(f"Testing batch sizes: {batch_sizes}")
print(f"Runs per size: {runs_per_size}")
print()

results = {}

for batch_size in batch_sizes:
    print(f"{'='*60}")
    print(f"Batch Size: {batch_size}")
    print(f"{'='*60}")
    
    cold_times = []
    warm_times = []
    
    for run in range(runs_per_size):
        # Cold start (new service instance)
        cold_service = ScoringService(config=ScoringConfig())
        
        start = time.time()
        for _ in range(batch_size):
            result = cold_service.compute_match(
                resume_text=resume_text,
                job_text=job_description,
                resume_skills=resume_skills,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                use_semantic=True,
            )
        cold_time = time.time() - start
        cold_times.append(cold_time)
        
        # Warm start (reuse service instance)
        warm_service = ScoringService(config=ScoringConfig())
        
        # Warm up the model
        warm_service.compute_match(
            resume_text=resume_text,
            job_text=job_description,
            resume_skills=resume_skills,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            use_semantic=True,
        )
        
        start = time.time()
        for _ in range(batch_size):
            result = warm_service.compute_match(
                resume_text=resume_text,
                job_text=job_description,
                resume_skills=resume_skills,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                use_semantic=True,
            )
        warm_time = time.time() - start
        warm_times.append(warm_time)
        
        print(f"Run {run+1}: Cold {cold_time:.3f}s, Warm {warm_time:.3f}s")
    
    avg_cold = sum(cold_times) / len(cold_times)
    avg_warm = sum(warm_times) / len(warm_times)
    per_resume_cold = avg_cold / batch_size
    per_resume_warm = avg_warm / batch_size
    
    results[batch_size] = {
        "cold_avg": avg_cold,
        "warm_avg": avg_warm,
        "per_resume_cold": per_resume_cold,
        "per_resume_warm": per_resume_warm,
    }
    
    print(f"Average: Cold {avg_cold:.3f}s, Warm {avg_warm:.3f}s")
    print(f"Per resume: Cold {per_resume_cold:.3f}s, Warm {per_resume_warm:.3f}s")
    print()

print(f"{'='*60}")
print("Summary")
print(f"{'='*60}")
print(f"{'Batch Size':<12} | {'Cold Total':<12} | {'Warm Total':<12} | {'Cold/Resume':<13} | {'Warm/Resume':<13}")
print("-"*60)

for batch_size in batch_sizes:
    r = results[batch_size]
    print(f"{batch_size:<12} | {r['cold_avg']:<12.3f} | {r['warm_avg']:<12.3f} | {r['per_resume_cold']:<13.3f} | {r['per_resume_warm']:<13.3f}")

print()
print("Analysis:")
print(f"- Cold start overhead: {results[1]['cold_avg'] - results[1]['warm_avg']:.3f}s")
print(f"- Warm start per resume: {results[1]['per_resume_warm']:.3f}s")
print(f"- Batch efficiency (50 resumes): {results[50]['per_resume_warm'] / results[1]['per_resume_warm']:.2f}x")

print(f"\n=== Phase 4 Performance Measurement Complete ===")
