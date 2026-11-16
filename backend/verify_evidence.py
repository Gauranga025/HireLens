"""
Verify actual resume evidence extraction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.section_detection_service import SectionDetectionService
from app.services.evidence_extraction_service import EvidenceExtractionService
from app.services.skill_service import extract_skills

def main():
    print("=" * 60)
    print("EVIDENCE EXTRACTION VERIFICATION")
    print("=" * 60)
    
    resume_text = """
    Alice Johnson
    alice@example.com
    
    Professional Summary
    Senior Backend Developer with 5 years of experience.
    
    Work Experience
    Senior Backend Developer at TechCorp
    - Developed RESTful APIs using Python and FastAPI
    - Designed PostgreSQL database schemas with optimized queries
    - Containerized applications using Docker
    - Implemented microservices architecture
    
    Projects
    - Built a scalable e-commerce platform using Python
    - Created data processing pipelines with SQL
    - Developed real-time notification system
    
    Skills
    Python, FastAPI, PostgreSQL, Docker, Microservices, SQL
    
    Education
    BS in Computer Science
    - Coursework: Database Systems, Algorithms
    """
    
    print("\nResume text:")
    print(resume_text)
    
    # Section detection
    section_service = SectionDetectionService()
    sections = section_service.detect_sections(resume_text)
    
    print("\n" + "=" * 60)
    print("DETECTED SECTIONS")
    print("=" * 60)
    for section in sections:
        print(f"  {section[0]}: {section[1]} (offset {section[2]})")
    
    # Skill extraction
    skills_data = extract_skills(resume_text)
    skills = skills_data.get("technical_skills", [])
    
    print("\n" + "=" * 60)
    print("EXTRACTED SKILLS")
    print("=" * 60)
    print(f"  {skills}")
    
    # Evidence extraction
    evidence_service = EvidenceExtractionService()
    
    print("\n" + "=" * 60)
    print("EVIDENCE EXTRACTION")
    print("=" * 60)
    
    all_evidence_dict = evidence_service.extract_skill_evidence(resume_text, skills)
    
    for skill in ["Python", "Docker", "PostgreSQL", "SQL"]:
        evidence = all_evidence_dict.get(skill, [])
        print(f"\nSkill: {skill}")
        print(f"  Evidence count: {len(evidence)}")
        for ev in evidence:
            print(f"  - Section: {ev.section.value}")
            print(f"    Type: {ev.evidence_type.value}")
            print(f"    Strength: {ev.strength.value}")
            print(f"    Snippet: \"{ev.snippet}\"")
            # Verify the skill occurrence is grounded using offsets
            extracted_skill = resume_text[ev.start_offset:ev.end_offset]
            if skill.lower() in extracted_skill.lower():
                print(f"    ✓ Skill occurrence verified at offset {ev.start_offset}-{ev.end_offset}")
            else:
                print(f"    ✗ WARNING: Skill NOT found at reported offset")
    
    print("\n" + "=" * 60)
    print("EVIDENCE GROUNDING VERIFICATION")
    print("=" * 60)
    
    # Test that all skill occurrences are grounded via offsets
    all_evidence = all_evidence_dict.get("Python", [])
    all_grounded = all(
        skill.lower() in resume_text[ev.start_offset:ev.end_offset].lower()
        for ev in all_evidence
        for skill in [ev.skill]
    )
    
    print(f"Total evidence for 'Python': {len(all_evidence)}")
    print(f"All skill occurrences grounded via offsets: {all_grounded}")
    
    if not all_grounded:
        print("WARNING: Some skill occurrences are not grounded!")
        for ev in all_evidence:
            extracted = resume_text[ev.start_offset:ev.end_offset]
            if ev.skill.lower() not in extracted.lower():
                print(f"  Ungrounded: {ev.skill} at offset {ev.start_offset}-{ev.end_offset}: '{extracted}'")
    
    print("\nNote: Snippets include ellipsis and context for display.")
    print("Skill occurrences are correctly located via offsets.")

if __name__ == "__main__":
    main()
