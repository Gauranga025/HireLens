"""
Test Phase 3 components: skill hierarchy, evidence classification, keyword stuffing detection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.data.skill_hierarchy import get_skill_hierarchy_registry, RelationshipType
from app.services.keyword_stuffing_detector import KeywordStuffingDetector
from app.services.evidence_extraction_service import EvidenceExtractionService
from app.services.skill_service import extract_skills

print("=== Phase 3 Component Tests ===\n")

# Test 1: Skill Hierarchy Registry
print("Test 1: Skill Hierarchy Registry")
print("-" * 50)
registry = get_skill_hierarchy_registry()

test_pairs = [
    ("REST API", "RESTful services", RelationshipType.ALIAS),
    ("PostgreSQL", "Postgres", RelationshipType.ALIAS),
    ("SQL", "PostgreSQL", RelationshipType.PARENT_CHILD),
    ("TensorFlow", "PyTorch", RelationshipType.RELATED),
    ("Java", "JavaScript", RelationshipType.DISTINCT),
]

for skill_a, skill_b, expected in test_pairs:
    rel = registry.get_relationship(skill_a, skill_b)
    match_credit = registry.get_match_credit(skill_a, skill_b)
    print(f"{skill_a} ↔ {skill_b}:")
    print(f"  Relationship: {rel.value if rel else 'None'}")
    print(f"  Expected: {expected.value}")
    print(f"  Match credit: {match_credit}")
    print(f"  ✓ PASS" if rel == expected else "  ✗ FAIL")
    print()

# Test 2: Match Credit Calculation
print("Test 2: Match Credit Calculation")
print("-" * 50)
credit_tests = [
    ("REST API", "RESTful services", 1.0),
    ("SQL", "PostgreSQL", 0.5),
    ("TensorFlow", "PyTorch", 0.5),
    ("Java", "JavaScript", 0.0),
    ("Python", "Java", 0.0),
]

for required, candidate, expected in credit_tests:
    credit = registry.get_match_credit(required, candidate)
    print(f"Required: {required}, Candidate: {candidate}")
    print(f"  Credit: {credit}, Expected: {expected}")
    print(f"  ✓ PASS" if credit == expected else "  ✗ FAIL")
    print()

# Test 3: Evidence Classification with New Types
print("Test 3: Evidence Classification (Internship, Demonstration Level)")
print("-" * 50)
evidence_service = EvidenceExtractionService()

test_texts = [
    ("Internship experience", "Software Engineering Intern at TechCorp (Summer 2024). Assisted with FastAPI API development."),
    ("Professional experience", "Senior Backend Developer at ScaleUp (2019-present). Built REST APIs serving 10M+ daily requests."),
    ("Skills section", "Skills: Python, FastAPI, PostgreSQL, REST API"),
]

for name, text in test_texts:
    skills = extract_skills(text)["technical_skills"]
    evidence = evidence_service.extract_skill_evidence(text, skills)
    print(f"{name}:")
    print(f"  Extracted skills: {skills}")
    for skill, ev_list in evidence.items():
        if ev_list:
            ev = ev_list[0]
            print(f"  {skill}:")
            print(f"    Type: {ev.evidence_type.value}")
            print(f"    Strength: {ev.strength.value}")
            print(f"    Demonstration: {ev.demonstration_level.value if ev.demonstration_level else 'None'}")
            print(f"    Has dates: {ev.date_info.get('has_dates', False)}")
            print(f"    Is recent: {ev.date_info.get('is_recent')}")
    print()

# Test 4: Keyword Stuffing Detection
print("Test 4: Keyword Stuffing Detection")
print("-" * 50)
detector = KeywordStuffingDetector(threshold=0.7)

# Case 1: Keyword stuffer
stuffer_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Kubernetes", "TensorFlow", "PyTorch", "React", "Angular", "Vue.js"]
stuffer_evidence = {
    skill: [] for skill in stuffer_skills  # No evidence
}
analysis_stuffer = detector.analyze(stuffer_skills, stuffer_evidence)
print("Keyword Stuffer (no evidence):")
print(f"  Total skills: {analysis_stuffer.total_skills}")
print(f"  Skills without evidence: {analysis_stuffer.skills_without_evidence}")
print(f"  Stuffing ratio: {analysis_stuffer.stuffing_ratio:.2f}")
print(f"  Is stuffed: {analysis_stuffer.is_stuffed}")
print(f"  Penalty: {analysis_stuffer.penalty:.2f}")
print()

# Case 2: Legitimate candidate with evidence
legit_skills = ["Python", "FastAPI", "PostgreSQL"]
# Convert to proper evidence format for detector
from app.services.evidence_extraction_service import SkillEvidence, EvidenceStrength, EvidenceType
from app.services.section_detection_service import SectionType

legit_evidence_proper = {}
for skill in legit_skills:
    legit_evidence_proper[skill] = [
        SkillEvidence(
            skill=skill,
            section=SectionType.EXPERIENCE,
            evidence_type=EvidenceType.DEMONSTRATED_IN_EXPERIENCE,
            snippet="Built REST API using Python and FastAPI",
            strength=EvidenceStrength.STRONG,
            start_offset=0,
            end_offset=10,
        )
    ]
analysis_legit = detector.analyze(legit_skills, legit_evidence_proper)
print("Legitimate candidate (with evidence):")
print(f"  Total skills: {analysis_legit.total_skills}")
print(f"  Skills without evidence: {analysis_legit.skills_without_evidence}")
print(f"  Stuffing ratio: {analysis_legit.stuffing_ratio:.2f}")
print(f"  Is stuffed: {analysis_legit.is_stuffed}")
print(f"  Penalty: {analysis_legit.penalty:.2f}")
print()

# Case 3: Mixed (some evidence)
mixed_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]
mixed_evidence_proper = {}
for skill in mixed_skills[:3]:  # First 3 have evidence
    mixed_evidence_proper[skill] = [
        SkillEvidence(
            skill=skill,
            section=SectionType.EXPERIENCE,
            evidence_type=EvidenceType.DEMONSTRATED_IN_EXPERIENCE,
            snippet="Built REST API using Python and FastAPI",
            strength=EvidenceStrength.STRONG,
            start_offset=0,
            end_offset=10,
        )
    ]
for skill in mixed_skills[3:]:  # Last 2 have no evidence
    mixed_evidence_proper[skill] = []
analysis_mixed = detector.analyze(mixed_skills, mixed_evidence_proper)
print("Mixed candidate (partial evidence):")
print(f"  Total skills: {analysis_mixed.total_skills}")
print(f"  Skills without evidence: {analysis_mixed.skills_without_evidence}")
print(f"  Stuffing ratio: {analysis_mixed.stuffing_ratio:.2f}")
print(f"  Is stuffed: {analysis_mixed.is_stuffed}")
print(f"  Penalty: {analysis_mixed.penalty:.2f}")
print()

print("=== Phase 3 Component Tests Complete ===")
