"""
Phase 3 Evaluation: Run evaluation on extended benchmark.
Tests skill hierarchy, evidence classification, and keyword stuffing detection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation_dataset_extended import EXTENDED_EVALUATION_DATASET
from app.services.scoring_service import ScoringService
from app.services.skill_service import extract_skills
from app.services.evidence_extraction_service import EvidenceExtractionService
from app.services.keyword_stuffing_detector import KeywordStuffingDetector
from app.data.skill_hierarchy import get_skill_hierarchy_registry
from typing import List, Dict, Tuple
import numpy as np

print("=== Phase 3 Extended Benchmark Evaluation ===\n")

jobs = EXTENDED_EVALUATION_DATASET["job_descriptions"]
resumes = EXTENDED_EVALUATION_DATASET["resumes"]

# Focus on jd_001 (Backend Software Engineer) for detailed analysis
job = jobs[0]
print(f"Evaluating job: {job['title']} ({job['id']})")
print(f"Required skills: {job['required_skills']}")
print(f"Preferred skills: {job['preferred_skills']}")
print()

# Filter resumes for this job
job_resumes = [r for r in resumes if r["for_job"] == job["id"]]
print(f"Total resumes for this job: {len(job_resumes)}")
print()

# Test skill hierarchy
print("=== Skill Hierarchy Analysis ===")
registry = get_skill_hierarchy_registry()

for resume in job_resumes[:5]:  # First 5 resumes
    print(f"\nResume: {resume['id']} - {resume.get('name', 'Unknown')}")
    for required_skill in job['required_skills']:
        resume_skills = extract_skills(resume["content"])["technical_skills"]
        for candidate_skill in resume_skills:
            credit = registry.get_match_credit(required_skill, candidate_skill)
            if credit > 0:
                rel = registry.get_relationship(required_skill, candidate_skill)
                print(f"  {required_skill} ↔ {candidate_skill}: credit={credit}, rel={rel.value if rel else 'None'}")

print("\n=== Evidence Classification Analysis ===")
evidence_service = EvidenceExtractionService()

for resume in job_resumes[:5]:
    print(f"\nResume: {resume['id']} - {resume.get('name', 'Unknown')}")
    resume_skills = extract_skills(resume["content"])["technical_skills"]
    evidence = evidence_service.extract_skill_evidence(resume["content"], resume_skills)
    
    for skill in job['required_skills'][:2]:  # First 2 required skills
        if skill in evidence:
            ev_list = evidence[skill]
            if ev_list:
                ev = ev_list[0]
                print(f"  {skill}:")
                print(f"    Type: {ev.evidence_type.value}")
                print(f"    Strength: {ev.strength.value}")
                print(f"    Demonstration: {ev.demonstration_level.value if ev.demonstration_level else 'None'}")
                print(f"    Has dates: {ev.date_info.get('has_dates', False)}")
                print(f"    Is recent: {ev.date_info.get('is_recent')}")
        else:
            print(f"  {skill}: No evidence")

print("\n=== Keyword Stuffing Detection ===")
detector = KeywordStuffingDetector(threshold=0.7)

for resume in job_resumes:
    resume_skills = extract_skills(resume["content"])["technical_skills"]
    evidence = evidence_service.extract_skill_evidence(resume["content"], resume_skills)
    
    analysis = detector.analyze(resume_skills, evidence)
    
    print(f"\nResume: {resume['id']} - {resume.get('name', 'Unknown')}")
    print(f"  Total skills: {analysis.total_skills}")
    print(f"  Skills without evidence: {analysis.skills_without_evidence}")
    print(f"  Stuffing ratio: {analysis.stuffing_ratio:.2f}")
    print(f"  Is stuffed: {analysis.is_stuffed}")
    print(f"  Penalty: {analysis.penalty:.2f}")
    print(f"  Test category: {resume.get('test_category', 'N/A')}")

print("\n=== Baseline Scoring (Current Formula) ===")
scoring_service = ScoringService()

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
    })

ranked.sort(key=lambda x: x["score"], reverse=True)

print("\nRanked candidates:")
for i, r in enumerate(ranked):
    print(f"  {i+1}. {r['id']} ({r['name']}) - {r['score']:.2f}% - {r['relevance']} - {r['test_category']}")
    print(f"     Required coverage: {r['required_coverage']:.2f}%, Evidence: {r['evidence_score']:.2f}%")

print("\n=== Analysis by Test Category ===")
categories = {}
for r in ranked:
    cat = r["test_category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(r)

for cat, cat_resumes in categories.items():
    avg_score = np.mean([r["score"] for r in cat_resumes])
    print(f"\n{cat}:")
    print(f"  Count: {len(cat_resumes)}")
    print(f"  Average score: {avg_score:.2f}%")
    print(f"  Top resume: {cat_resumes[0]['id']} ({cat_resumes[0]['score']:.2f}%)")

print("\n=== Phase 3 Evaluation Complete ===")
