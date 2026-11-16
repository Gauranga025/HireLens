import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scoring_service import ScoringService

print("=== Testing Scoring Metadata with Semantic Matching ===\n")

scoring_service = ScoringService()

resume_text = """
Python developer with experience building RESTful web services.
Strong understanding of OOP principles and object-oriented design.
Developed applications using FastAPI framework.
"""

job_text = """
Backend Software Engineer

Required Skills:
- Python
- REST API
- Object-Oriented Programming
- FastAPI

Preferred Skills:
- Docker
- PostgreSQL
"""

resume_skills = ["Python", "FastAPI", "REST API", "Object-Oriented Programming"]
required_skills = ["Python", "REST API", "Object-Oriented Programming", "FastAPI"]
preferred_skills = ["Docker", "PostgreSQL"]

print("Resume text:", resume_text[:100] + "...")
print("Job text:", job_text[:100] + "...")
print("Resume skills:", resume_skills)
print("Required skills:", required_skills)
print("Preferred skills:", preferred_skills)
print()

result = scoring_service.compute_match(
    resume_text=resume_text,
    job_text=job_text,
    resume_skills=resume_skills,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=True,
)

print("=== Scoring Results ===")
print(f"Overall score: {result['overall_score']:.2f}%")
print(f"Required skill coverage: {result['required_skill_coverage']:.2f}%")
print(f"Preferred skill coverage: {result['preferred_skill_coverage']:.2f}%")
print(f"Evidence score: {result['evidence_score']:.2f}%")
print(f"Semantic score: {result['semantic_score']}")
print(f"Matched skills: {result['matched_skills']}")
print(f"Missing skills: {result['missing_skills']}")
print()

print("=== Scoring Strategy Metadata ===")
strategy = result['scoring_strategy']
print(f"Algorithm version: {strategy['algorithm_version']}")
print(f"Components: {strategy['components']}")
print(f"Weights: {strategy['weights']}")
print(f"Semantic available: {strategy['semantic_available']}")
print(f"Fallback used: {strategy['fallback_used']}")
print()

if strategy['semantic_available']:
    print("✓ PASS: Semantic matching is active and exposed in metadata")
else:
    print("✗ FAIL: Semantic matching not available")

if not strategy['fallback_used']:
    print("✓ PASS: Full scoring formula used (not fallback)")
else:
    print("✗ FAIL: Fallback scoring was used")
