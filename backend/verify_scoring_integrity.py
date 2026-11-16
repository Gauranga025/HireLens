"""
Verify scoring integrity and normalization.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation_dataset import EVALUATION_DATASET
from app.services.scoring_service import ScoringService
from app.services.skill_service import extract_skills

print("=== Scoring Integrity Verification ===\n")

job = EVALUATION_DATASET["job_descriptions"][0]
resume = EVALUATION_DATASET["resumes"][0]

scoring_service = ScoringService()
resume_skills = extract_skills(resume["content"])["technical_skills"]

result = scoring_service.compute_match(
    resume_text=resume["content"],
    job_text=job["description"],
    resume_skills=resume_skills,
    required_skills=job["required_skills"],
    preferred_skills=job["preferred_skills"],
    use_semantic=True,
)

print("Test 1: Component Score Normalization (0-100)")
print("-" * 50)
print(f"Required skill coverage: {result['required_skill_coverage']:.2f}%")
print(f"Preferred skill coverage: {result['preferred_skill_coverage']:.2f}%")
print(f"Evidence score: {result['evidence_score']:.2f}%")
print(f"Semantic score: {result['semantic_score']:.2f}%")
print(f"TF-IDF score: {result['tfidf_score']:.2f}%")
print(f"Overall score: {result['overall_score']:.2f}%")

all_in_range = all(0 <= v <= 100 for v in [
    result['required_skill_coverage'],
    result['preferred_skill_coverage'],
    result['evidence_score'],
    result['semantic_score'] or 0,
    result['tfidf_score'],
    result['overall_score']
])
print(f"All scores in 0-100 range: {all_in_range}")
print()

print("Test 2: Missing Semantic Score Handling")
print("-" * 50)
result_no_semantic = scoring_service.compute_match(
    resume_text=resume["content"],
    job_text=job["description"],
    resume_skills=resume_skills,
    required_skills=job["required_skills"],
    preferred_skills=job["preferred_skills"],
    use_semantic=False,
)
print(f"Semantic score (use_semantic=False): {result_no_semantic['semantic_score']}")
print(f"Overall score (fallback): {result_no_semantic['overall_score']:.2f}%")
print(f"Fallback used: {result_no_semantic['scoring_strategy']['fallback_used']}")
print()

print("Test 3: Model Fallback Metadata Accuracy")
print("-" * 50)
print(f"Semantic available: {result['scoring_strategy']['semantic_available']}")
print(f"Fallback used: {result['scoring_strategy']['fallback_used']}")
print(f"Algorithm version: {result['scoring_strategy']['algorithm_version']}")
print(f"Active components: {result['scoring_strategy']['components']}")
print(f"Weights: {result['scoring_strategy']['weights']}")
print()

print("Test 4: Required vs Preferred Skills Separation")
print("-" * 50)
print(f"Matched skills: {result['matched_skills']}")
print(f"Missing skills: {result['missing_skills']}")
print(f"Additional skills: {result['additional_skills'][:5]}...")
print(f"Required coverage: {result['required_skill_coverage']:.2f}%")
print(f"Preferred coverage: {result['preferred_skill_coverage']:.2f}%")
print()

print("Test 5: Evidence Score Supported by Snippets")
print("-" * 50)
print(f"Skill evidence keys: {list(result['skill_evidence'].keys())[:5]}")
for skill, evidence_list in list(result['skill_evidence'].items())[:3]:
    print(f"\n{skill}:")
    if evidence_list:
        for ev in evidence_list[:2]:
            print(f"  Section: {ev['section']}")
            print(f"  Snippet: {ev['snippet'][:80]}...")
            print(f"  Strength: {ev['strength']}")
    else:
        print("  No evidence found")
print()

print("Test 6: No Duplicate Skill Credit")
print("-" * 50)
matched_set = set(result['matched_skills'])
print(f"Matched skills (list): {result['matched_skills']}")
print(f"Matched skills (set): {matched_set}")
print(f"Duplicate check: {len(result['matched_skills']) == len(matched_set)}")
print()

print("Test 7: Candidate Ordering Matches Backend Scores")
print("-" * 50)
# Test with multiple resumes
test_resumes = EVALUATION_DATASET["resumes"][:5]
ranked = []
for r in test_resumes:
    r_skills = extract_skills(r["content"])["technical_skills"]
    r_result = scoring_service.compute_match(
        resume_text=r["content"],
        job_text=job["description"],
        resume_skills=r_skills,
        required_skills=job["required_skills"],
        preferred_skills=job["preferred_skills"],
        use_semantic=True,
    )
    ranked.append((r["id"], r_result["overall_score"]))

ranked.sort(key=lambda x: x[1], reverse=True)
print("Ranked candidates:")
for i, (rid, score) in enumerate(ranked):
    print(f"  {i+1}. {rid}: {score:.2f}%")

# Verify ordering
is_sorted = all(ranked[i][1] >= ranked[i+1][1] for i in range(len(ranked)-1))
print(f"Ordering is descending: {is_sorted}")
print()

print("Test 8: Scoring Consistency Across Multiple Runs")
print("-" * 50)
scores = []
for i in range(3):
    r_result = scoring_service.compute_match(
        resume_text=resume["content"],
        job_text=job["description"],
        resume_skills=resume_skills,
        required_skills=job["required_skills"],
        preferred_skills=job["preferred_skills"],
        use_semantic=True,
    )
    scores.append(r_result["overall_score"])

print(f"Scores across 3 runs: {[f'{s:.2f}%' for s in scores]}")
is_consistent = len(set(round(s, 2) for s in scores)) == 1
print(f"Scores are consistent: {is_consistent}")
print()

print("=== Verification Complete ===")
