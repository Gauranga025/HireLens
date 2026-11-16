"""
Verify database persistence of new fields.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.screening_result import ScreeningResult
from app.models.job import Job
from app.models.resume import Resume
from app.repositories.screening_repository import ScreeningRepository
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.core.config import settings


async def main():
    print("=" * 60)
    print("DATABASE PERSISTENCE VERIFICATION")
    print("=" * 60)
    
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create test job
        job_repo = JobRepository()
        job = Job(
            title="Test Backend Developer",
            description="Required: Python, Docker, PostgreSQL",
            required_skills=["Python", "Docker", "PostgreSQL"],
            preferred_skills=["FastAPI", "Redis"],
            analysis_data={"raw_text": "Required: Python, Docker, PostgreSQL"}
        )
        session.add(job)
        await session.flush()
        await session.refresh(job)
        print(f"\n✓ Created job: {job.id}")
        
        # Create test resume
        resume_repo = ResumeRepository()
        resume = Resume(
            original_filename="test_resume.pdf",
            file_type="pdf",
            storage_key="test_resume.pdf",
            extracted_text="Skills: Python, Docker, PostgreSQL. Experience: Developed APIs.",
            candidate_info={"name": "Test Candidate", "email": "test@example.com"},
            skills=["Python", "Docker", "PostgreSQL"]
        )
        session.add(resume)
        await session.flush()
        await session.refresh(resume)
        print(f"✓ Created resume: {resume.id}")
        
        # Create screening result with new fields
        screening_repo = ScreeningRepository()
        
        test_skill_evidence = {
            "Python": [
                {
                    "skill": "Python",
                    "section": "experience",
                    "evidence_type": "demonstrated_in_experience",
                    "snippet": "Developed APIs using Python",
                    "strength": "strong",
                    "start_offset": 50,
                    "end_offset": 56
                }
            ],
            "Docker": [
                {
                    "skill": "Docker",
                    "section": "skills",
                    "evidence_type": "listed_in_skills",
                    "snippet": "Skills: Python, Docker",
                    "strength": "basic",
                    "start_offset": 30,
                    "end_offset": 36
                }
            ]
        }
        
        test_requirement_matches = [
            {
                "requirement": "Python",
                "matched": True,
                "similarity_score": 1.0,
                "evidence": test_skill_evidence["Python"],
                "is_alternative": False
            },
            {
                "requirement": "Docker",
                "matched": True,
                "similarity_score": 1.0,
                "evidence": test_skill_evidence["Docker"],
                "is_alternative": False
            },
            {
                "requirement": "PostgreSQL",
                "matched": False,
                "evidence": [],
                "is_alternative": False
            }
        ]
        
        test_scoring_strategy = {
            "algorithm_version": "2.0.0-evidence-aware",
            "components": ["required_skills", "evidence"],
            "weights": {
                "required_skills": 0.35,
                "preferred_skills": 0.15,
                "semantic": 0.3,
                "evidence": 0.2,
                "tfidf": 0.0
            },
            "semantic_available": False,
            "fallback_used": False
        }
        
        screening = await screening_repo.create(
            db=session,
            job_id=job.id,
            resume_id=resume.id,
            overall_score=75.5,
            tfidf_score=60.0,
            semantic_score=None,
            skill_match_score=66.67,
            matched_skills=["Python", "Docker"],
            missing_skills=["PostgreSQL"],
            additional_skills=["FastAPI"],
            explanation="Candidate matches most required skills with strong evidence.",
            screening_status="completed",
            skill_evidence=test_skill_evidence,
            requirement_matches=test_requirement_matches,
            required_skill_coverage=66.67,
            preferred_skill_coverage=0.0,
            scoring_strategy=test_scoring_strategy,
        )
        
        await session.commit()
        print(f"✓ Created screening result: {screening.id}")
        
        # Retrieve in separate session to verify persistence
        await session.close()
        
    async with async_session() as session:
        # Retrieve the screening result
        result = await session.get(ScreeningResult, screening.id)
        
        print("\n" + "=" * 60)
        print("PERSISTENCE VERIFICATION")
        print("=" * 60)
        
        print(f"\nRetrieved screening: {result.id}")
        print(f"Overall score: {result.overall_score}")
        print(f"Required skill coverage: {result.required_skill_coverage}")
        print(f"Preferred skill coverage: {result.preferred_skill_coverage}")
        
        print(f"\nSkill evidence type: {type(result.skill_evidence)}")
        print(f"Skill evidence keys: {list(result.skill_evidence.keys()) if result.skill_evidence else 'None'}")
        
        print(f"\nRequirement matches type: {type(result.requirement_matches)}")
        print(f"Requirement matches count: {len(result.requirement_matches) if result.requirement_matches else 0}")
        
        print(f"\nScoring strategy type: {type(result.scoring_strategy)}")
        print(f"Scoring strategy version: {result.scoring_strategy.get('algorithm_version') if result.scoring_strategy else 'None'}")
        
        # Verify JSONB values match
        print("\n" + "=" * 60)
        print("DATA INTEGRITY CHECK")
        print("=" * 60)
        
        checks_passed = True
        
        if result.skill_evidence == test_skill_evidence:
            print("✓ skill_evidence matches original")
        else:
            print("✗ skill_evidence does NOT match original")
            checks_passed = False
        
        if result.requirement_matches == test_requirement_matches:
            print("✓ requirement_matches matches original")
        else:
            print("✗ requirement_matches does NOT match original")
            checks_passed = False
        
        if result.scoring_strategy == test_scoring_strategy:
            print("✓ scoring_strategy matches original")
        else:
            print("✗ scoring_strategy does NOT match original")
            checks_passed = False
        
        if abs(result.required_skill_coverage - 66.67) < 0.01:
            print("✓ required_skill_coverage matches original")
        else:
            print("✗ required_skill_coverage does NOT match original")
            checks_passed = False
        
        if abs(result.preferred_skill_coverage - 0.0) < 0.01:
            print("✓ preferred_skill_coverage matches original")
        else:
            print("✗ preferred_skill_coverage does NOT match original")
            checks_passed = False
        
        # Clean up test data
        await session.delete(result)
        await session.delete(resume)
        await session.delete(job)
        await session.commit()
        print("\n✓ Cleaned up test data")
        
        await engine.dispose()
        
        print("\n" + "=" * 60)
        if checks_passed:
            print("✓ ALL PERSISTENCE CHECKS PASSED")
        else:
            print("✗ SOME PERSISTENCE CHECKS FAILED")
        print("=" * 60)
        
        return checks_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
