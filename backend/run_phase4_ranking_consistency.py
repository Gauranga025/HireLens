"""
Phase 4 Ranking Consistency Testing
Test deterministic ranking, score normalization, duplicate prevention, and semantic fallback.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import extract_skills

print("=== Phase 4 Ranking Consistency Testing ===\n")

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

scoring_service = ScoringService(config=ScoringConfig())
resume_skills = extract_skills(resume_text)["technical_skills"]

# Test 1: Deterministic ranking across repeated runs
print("Test 1: Deterministic Ranking Across Repeated Runs")
print("-"*60)

scores = []
for i in range(10):
    result = scoring_service.compute_match(
        resume_text=resume_text,
        job_text=job_description,
        resume_skills=resume_skills,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        use_semantic=True,
    )
    scores.append(result["overall_score"])

print(f"Scores from 10 runs: {[f'{s:.2f}%' for s in scores]}")
print(f"Min: {min(scores):.2f}%, Max: {max(scores):.2f}%, Mean: {sum(scores)/len(scores):.2f}%")
print(f"All identical: {len(set(scores)) == 1}")
assert len(set(scores)) == 0 or max(scores) - min(scores) < 0.01, "Scores should be deterministic"
print("✓ PASS: Deterministic ranking\n")

# Test 2: Stable score normalization
print("Test 2: Stable Score Normalization")
print("-"*60)

result = scoring_service.compute_match(
    resume_text=resume_text,
    job_text=job_description,
    resume_skills=resume_skills,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=True,
)

print(f"Overall score: {result['overall_score']:.2f}%")
print(f"Required coverage: {result['required_skill_coverage']:.2f}%")
print(f"Preferred coverage: {result['preferred_skill_coverage']:.2f}%")
print(f"Evidence score: {result['evidence_score']:.2f}%")
print(f"Semantic score: {result['semantic_score']:.2f}%")

assert 0 <= result['overall_score'] <= 100, "Overall score should be in 0-100 range"
assert 0 <= result['required_skill_coverage'] <= 100, "Required coverage should be in 0-100 range"
assert 0 <= result['evidence_score'] <= 100, "Evidence score should be in 0-100 range"
print("✓ PASS: Score normalization stable\n")

# Test 3: Duplicate skill prevention
print("Test 3: Duplicate Skill Prevention")
print("-"*60)

resume_with_duplicates = """
John Smith
Backend Developer

Skills: Python, Python, FastAPI, FastAPI, PostgreSQL, PostgreSQL, REST API, REST API

Experience:
- Senior Backend Developer at TechCorp (2020-present)
  - Built scalable REST APIs using Python and FastAPI
  - Designed PostgreSQL database schemas
"""

skills_with_duplicates = extract_skills(resume_with_duplicates)["technical_skills"]
print(f"Skills extracted: {skills_with_duplicates}")
print(f"Unique skills: {len(set(skills_with_duplicates))}")
print(f"Total skills: {len(skills_with_duplicates)}")

result = scoring_service.compute_match(
    resume_text=resume_with_duplicates,
    job_text=job_description,
    resume_skills=skills_with_duplicates,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=True,
)

print(f"Matched skills: {result['matched_skills']}")
print(f"Match percentage: {result['required_skill_coverage']:.2f}%")
assert result['required_skill_coverage'] <= 100, "Match percentage should not exceed 100%"
print("✓ PASS: Duplicate skills handled correctly\n")

# Test 4: Consistent semantic fallback
print("Test 4: Consistent Semantic Fallback")
print("-"*60)

result_with_semantic = scoring_service.compute_match(
    resume_text=resume_text,
    job_text=job_description,
    resume_skills=resume_skills,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=True,
)

result_without_semantic = scoring_service.compute_match(
    resume_text=resume_text,
    job_text=job_description,
    resume_skills=resume_skills,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=False,
)

print(f"With semantic: {result_with_semantic['overall_score']:.2f}%")
print(f"Without semantic: {result_without_semantic['overall_score']:.2f}%")
print(f"Semantic score: {result_with_semantic['semantic_score']}")
print(f"Fallback used: {result_with_semantic['scoring_strategy']['fallback_used']}")

assert result_with_semantic['semantic_score'] is not None, "Semantic score should be present when enabled"
assert result_without_semantic['semantic_score'] is None, "Semantic score should be None when disabled"
print("✓ PASS: Semantic fallback consistent\n")

# Test 5: Evidence traceability
print("Test 5: Evidence Traceability")
print("-"*60)

result = scoring_service.compute_match(
    resume_text=resume_text,
    job_text=job_description,
    resume_skills=resume_skills,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=True,
)

print(f"Matched skills: {result['matched_skills']}")
print(f"Skill evidence keys: {list(result['skill_evidence'].keys())}")

for skill in result['matched_skills']:
    if skill in result['skill_evidence']:
        evidence_list = result['skill_evidence'][skill]
        print(f"  {skill}: {len(evidence_list)} evidence items")
        if evidence_list:
            print(f"    First evidence type: {evidence_list[0].get('evidence_type', 'N/A')}")
            print(f"    First evidence strength: {evidence_list[0].get('strength', 'N/A')}")

assert result['skill_evidence'] is not None, "Skill evidence should be present"
print("✓ PASS: Evidence traceable\n")

# Test 6: Correct handling of missing information
print("Test 6: Correct Handling of Missing Information")
print("-"*60)

empty_resume = ""
empty_skills = []

result = scoring_service.compute_match(
    resume_text=empty_resume,
    job_text=job_description,
    resume_skills=empty_skills,
    required_skills=required_skills,
    preferred_skills=preferred_skills,
    use_semantic=True,
)

print(f"Overall score: {result['overall_score']:.2f}%")
print(f"Matched skills: {result['matched_skills']}")
print(f"Missing skills: {result['missing_skills']}")
print(f"Evidence score: {result['evidence_score']:.2f}%")

assert result['overall_score'] == 0.0, "Empty resume should have 0 score"
assert result['matched_skills'] == [], "Empty resume should have no matched skills"
assert result['missing_skills'] == required_skills, "All required skills should be missing"
print("✓ PASS: Missing information handled correctly\n")

print("=== Phase 4 Ranking Consistency Testing Complete ===")
