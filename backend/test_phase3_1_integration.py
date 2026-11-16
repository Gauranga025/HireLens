"""
Regression tests for Phase 3.1 integrated components.
Tests skill hierarchy, demonstration levels, and keyword stuffing penalty.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scoring_service import ScoringService, ScoringConfig
from app.services.skill_service import match_skills_to_requirements, extract_skills
from app.data.skill_hierarchy import get_skill_hierarchy_registry, RelationshipType
from app.services.keyword_stuffing_detector import KeywordStuffingDetector
from app.services.evidence_extraction_service import EvidenceExtractionService, DemonstrationLevel

print("=== Phase 3.1 Integration Regression Tests ===\n")

# Test 1: Skill hierarchy integration
print("Test 1: Skill Hierarchy Integration")
print("-" * 50)
registry = get_skill_hierarchy_registry()

# Test alias matching
candidate_skills = ["Python", "RESTful services", "Postgres"]
required_skills = ["Python", "REST API", "PostgreSQL"]

match_result = match_skills_to_requirements(candidate_skills, required_skills, use_hierarchy=True)
print(f"Candidate: {candidate_skills}")
print(f"Required: {required_skills}")
print(f"Matched: {match_result['matched']}")
print(f"Match percentage: {match_result['match_percentage']}%")
assert "REST API" in match_result['matched'], "REST API should match via alias"
assert "PostgreSQL" in match_result['matched'], "PostgreSQL should match via alias"
print("✓ PASS: Alias matching works\n")

# Test 2: Related technology partial credit
print("Test 2: Related Technology Partial Credit")
print("-" * 50)
candidate_skills = ["Python", "FastAPI", "MySQL"]
required_skills = ["Python", "FastAPI", "PostgreSQL"]

match_result = match_skills_to_requirements(candidate_skills, required_skills, use_hierarchy=True)
print(f"Candidate: {candidate_skills}")
print(f"Required: {required_skills}")
print(f"Matched: {match_result['matched']}")
print(f"Match percentage: {match_result['match_percentage']}%")
# MySQL is related to PostgreSQL but not equivalent, so it should NOT match
assert "PostgreSQL" not in match_result['matched'], "PostgreSQL should not match MySQL (related but not equivalent)"
print("✓ PASS: Related technologies don't get full credit\n")

# Test 3: Distinct technologies no match
print("Test 3: Distinct Technologies No Match")
print("-" * 50)
candidate_skills = ["JavaScript", "React"]
required_skills = ["Java", "Spring"]

match_result = match_skills_to_requirements(candidate_skills, required_skills, use_hierarchy=True)
print(f"Candidate: {candidate_skills}")
print(f"Required: {required_skills}")
print(f"Matched: {match_result['matched']}")
print(f"Match percentage: {match_result['match_percentage']}%")
assert "Java" not in match_result['matched'], "Java should not match JavaScript (distinct)"
print("✓ PASS: Distinct technologies don't match\n")

# Test 4: Demonstration level weighting
print("Test 4: Demonstration Level Weighting")
print("-" * 50)
config_with_demo = ScoringConfig(use_demonstration_levels=True)
config_without_demo = ScoringConfig(use_demonstration_levels=False)

scoring_with = ScoringService(config=config_with_demo)
scoring_without = ScoringService(config=config_without_demo)

# Resume with claimed skills only
resume_claimed = """
Skills: Python, FastAPI, PostgreSQL
Experience: Junior Developer (2023-present)
"""

resume_demonstrated = """
Experience: Senior Backend Developer (2020-present)
- Built REST APIs using Python and FastAPI
- Designed PostgreSQL database schemas
"""

job_text = "Backend Software Engineer with Python, FastAPI, PostgreSQL"

result_with = scoring_with.compute_match(
    resume_text=resume_claimed,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=[],
    use_semantic=False,
)

result_without = scoring_without.compute_match(
    resume_text=resume_claimed,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=[],
    use_semantic=False,
)

print(f"With demonstration levels: evidence_score={result_with['evidence_score']:.2f}%")
print(f"Without demonstration levels: evidence_score={result_without['evidence_score']:.2f}%")
assert result_with['evidence_score'] < result_without['evidence_score'], "Claimed skills should have lower score with demonstration levels"
print("✓ PASS: Demonstration levels penalize claimed skills\n")

# Test 5: Keyword stuffing penalty
print("Test 5: Keyword Stuffing Penalty")
print("-" * 50)
config_with_penalty = ScoringConfig(use_keyword_stuffing_penalty=True)
config_without_penalty = ScoringConfig(use_keyword_stuffing_penalty=False)

scoring_with_penalty = ScoringService(config=config_with_penalty)
scoring_without_penalty = ScoringService(config=config_without_penalty)

# Keyword stuffer resume
stuffer_resume = """
Skills: Python, FastAPI, PostgreSQL, Docker, AWS, Kubernetes, TensorFlow, PyTorch, React, Angular, Vue.js, MongoDB, Redis, GraphQL, Jenkins, Git, Linux, Ansible, Terraform, Prometheus, Grafana
Experience: Junior Developer (2023-present)
"""

result_with_penalty = scoring_with_penalty.compute_match(
    resume_text=stuffer_resume,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Kubernetes", "TensorFlow", "PyTorch", "React", "Angular", "Vue.js", "MongoDB", "Redis", "GraphQL", "Jenkins", "Git", "Linux", "Ansible", "Terraform", "Prometheus", "Grafana"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Docker", "AWS", "Kubernetes"],
    use_semantic=False,
)

result_without_penalty = scoring_without_penalty.compute_match(
    resume_text=stuffer_resume,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Kubernetes", "TensorFlow", "PyTorch", "React", "Angular", "Vue.js", "MongoDB", "Redis", "GraphQL", "Jenkins", "Git", "Linux", "Ansible", "Terraform", "Prometheus", "Grafana"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Docker", "AWS", "Kubernetes"],
    use_semantic=False,
)

print(f"With penalty: overall_score={result_with_penalty['overall_score']:.2f}%, penalty={result_with_penalty['keyword_stuffing_penalty']:.2f}")
print(f"Without penalty: overall_score={result_without_penalty['overall_score']:.2f}%")
assert result_with_penalty['overall_score'] < result_without_penalty['overall_score'], "Keyword stuffer should have lower score with penalty"
assert result_with_penalty['keyword_stuffing_penalty'] > 0, "Penalty should be applied"
print("✓ PASS: Keyword stuffing penalty applied\n")

# Test 6: Legitimate candidate not penalized
print("Test 6: Legitimate Candidate Not Penalized")
print("-" * 50)

legitimate_resume = """
Experience: Senior Backend Developer (2020-present)
- Built REST APIs using Python and FastAPI
- Designed PostgreSQL database schemas
- Deployed applications using Docker on AWS
"""

result_legit_with = scoring_with_penalty.compute_match(
    resume_text=legitimate_resume,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Docker", "AWS", "Kubernetes"],
    use_semantic=False,
)

print(f"Legitimate candidate: overall_score={result_legit_with['overall_score']:.2f}%, penalty={result_legit_with['keyword_stuffing_penalty']:.2f}")
assert result_legit_with['keyword_stuffing_penalty'] == 0, "Legitimate candidate should not be penalized"
print("✓ PASS: Legitimate candidate not penalized\n")

# Test 7: Score boundaries (0-100)
print("Test 7: Score Boundaries (0-100)")
print("-" * 50)

empty_resume = "No skills here"
result_empty = scoring_with_penalty.compute_match(
    resume_text=empty_resume,
    job_text=job_text,
    resume_skills=[],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Docker", "AWS", "Kubernetes"],
    use_semantic=False,
)

print(f"Empty resume: overall_score={result_empty['overall_score']:.2f}%")
assert 0 <= result_empty['overall_score'] <= 100, "Score should be in 0-100 range"
print("✓ PASS: Score within valid range\n")

# Test 8: Scoring metadata
print("Test 8: Scoring Metadata")
print("-" * 50)

config_all = ScoringConfig(
    use_skill_hierarchy=True,
    use_demonstration_levels=True,
    use_keyword_stuffing_penalty=True,
)
scoring_all = ScoringService(config=config_all)

result_meta = scoring_all.compute_match(
    resume_text=legitimate_resume,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Docker", "AWS", "Kubernetes"],
    use_semantic=False,
)

strategy = result_meta['scoring_strategy']
print(f"Algorithm version: {strategy['algorithm_version']}")
print(f"Skill hierarchy enabled: {strategy['skill_hierarchy_enabled']}")
print(f"Demonstration levels enabled: {strategy['demonstration_levels_enabled']}")
print(f"Keyword stuffing penalty enabled: {strategy['keyword_stuffing_penalty_enabled']}")
assert strategy['skill_hierarchy_enabled'] == True, "Skill hierarchy should be enabled"
assert strategy['demonstration_levels_enabled'] == True, "Demonstration levels should be enabled"
assert strategy['keyword_stuffing_penalty_enabled'] == True, "Keyword stuffing penalty should be enabled"
print("✓ PASS: Metadata correctly reflects configuration\n")

# Test 9: Duplicate alias prevention
print("Test 9: Duplicate Alias Prevention")
print("-" * 50)

candidate_with_duplicates = ["Python", "REST API", "RESTful services", "PostgreSQL", "Postgres"]
required_skills = ["Python", "REST API", "PostgreSQL"]

match_result = match_skills_to_requirements(candidate_with_duplicates, required_skills, use_hierarchy=True)
print(f"Candidate: {candidate_with_duplicates}")
print(f"Required: {required_skills}")
print(f"Matched: {match_result['matched']}")
print(f"Match percentage: {match_result['match_percentage']}%")
# Should match each required skill only once
assert match_result['matched'].count("REST API") == 1, "REST API should appear only once in matched"
assert match_result['matched'].count("PostgreSQL") == 1, "PostgreSQL should appear only once in matched"
print("✓ PASS: Duplicate aliases prevented\n")

# Test 10: Semantic fallback with new components
print("Test 10: Semantic Fallback with New Components")
print("-" * 50)

config_fallback = ScoringConfig(
    use_skill_hierarchy=True,
    use_demonstration_levels=True,
    use_keyword_stuffing_penalty=False,
)

# Test with use_semantic=False to simulate fallback scenario
scoring_fallback = ScoringService(config=config_fallback)

result_fallback = scoring_fallback.compute_match(
    resume_text=legitimate_resume,
    job_text=job_text,
    resume_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    preferred_skills=["Docker", "AWS", "Kubernetes"],
    use_semantic=False,  # Explicitly disable semantic
)

print(f"Semantic disabled: overall_score={result_fallback['overall_score']:.2f}%")
print(f"Semantic score: {result_fallback['semantic_score']}")
assert result_fallback['semantic_score'] is None, "Semantic score should be None when disabled"
print("✓ PASS: Semantic disabled works with new components\n")

print("=== All Phase 3.1 Integration Tests Passed ===")
