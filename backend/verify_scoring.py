"""
Verify fallback scoring formula and metadata.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.scoring_service import ScoringService
from app.services.skill_service import extract_skills

def main():
    print("=" * 60)
    print("SCORING FORMULA VERIFICATION")
    print("=" * 60)
    
    service = ScoringService()
    
    resume_text = """
    Skills
    Python, Docker, PostgreSQL
    
    Experience
    Developed RESTful APIs using Python and FastAPI.
    """
    
    job_text = "Required: Python, Docker, PostgreSQL"
    
    skills = extract_skills(resume_text)["technical_skills"]
    required_skills = ["Python", "Docker", "PostgreSQL"]
    preferred_skills = []
    
    print(f"\nResume skills: {skills}")
    print(f"Required skills: {required_skills}")
    
    # Test with semantic disabled (fallback mode)
    result = service.compute_match(
        resume_text,
        job_text,
        skills,
        required_skills,
        preferred_skills,
        use_semantic=False,
    )
    
    print("\n" + "=" * 60)
    print("SCORING RESULTS (Fallback Mode)")
    print("=" * 60)
    print(f"Overall score: {result['overall_score']}")
    print(f"Required skill coverage: {result['required_skill_coverage']}")
    print(f"Preferred skill coverage: {result['preferred_skill_coverage']}")
    print(f"Semantic score: {result['semantic_score']}")
    print(f"Evidence score: {result['evidence_score']}")
    
    print("\n" + "=" * 60)
    print("SCORING STRATEGY METADATA")
    print("=" * 60)
    strategy = result['scoring_strategy']
    print(f"Algorithm version: {strategy['algorithm_version']}")
    print(f"Components: {strategy['components']}")
    print(f"Weights: {strategy['weights']}")
    print(f"Semantic available: {strategy['semantic_available']}")
    print(f"Fallback used: {strategy['fallback_used']}")
    
    # Verify fallback formula
    print("\n" + "=" * 60)
    print("FALLBACK FORMULA VERIFICATION")
    print("=" * 60)
    
    # Expected: 50% required + 50% preferred
    expected_score = 0.5 * result['required_skill_coverage'] + 0.5 * result['preferred_skill_coverage']
    print(f"Expected score (50% required + 50% preferred): {expected_score}")
    print(f"Actual score: {result['overall_score']}")
    print(f"Match: {abs(expected_score - result['overall_score']) < 0.01}")
    
    # Test with semantic enabled (but will fail due to huggingface_hub issue)
    print("\n" + "=" * 60)
    print("SEMANTIC MODE TEST")
    print("=" * 60)
    
    result_semantic = service.compute_match(
        resume_text,
        job_text,
        skills,
        required_skills,
        preferred_skills,
        use_semantic=True,
    )
    
    print(f"Overall score: {result_semantic['overall_score']}")
    print(f"Semantic score: {result_semantic['semantic_score']}")
    print(f"Semantic available: {result_semantic['scoring_strategy']['semantic_available']}")
    print(f"Fallback used: {result_semantic['scoring_strategy']['fallback_used']}")

if __name__ == "__main__":
    main()
