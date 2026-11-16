import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, text
import app.db.database as db_module
from app.models.resume import Resume
from app.models.job import Job
from app.models.screening_result import ScreeningResult

RESUME_ID = "e3357f64-3994-4ef3-87b5-b25273568f10"
JOB_ID = "960bdb94-c807-407f-b86d-002c1b82215a"

async def main():
    db_module.init_database()
    if db_module.engine is None:
        print("FAIL: Database initialization failed")
        return
    
    try:
        async with db_module.AsyncSessionLocal() as db:
            # Check resume
            result = await db.execute(select(Resume).where(Resume.id == RESUME_ID))
            resume = result.scalar_one_or_none()
            if resume:
                print(f"PASS: Resume record exists")
                print(f"  ID: {resume.id}")
                print(f"  Filename: {resume.original_filename}")
                print(f"  Skills: {resume.skills[:5]}...")
                print(f"  Status: {resume.processing_status}")
            else:
                print(f"FAIL: Resume record not found")
            
            # Check job
            result = await db.execute(select(Job).where(Job.id == JOB_ID))
            job = result.scalar_one_or_none()
            if job:
                print(f"\nPASS: Job record exists")
                print(f"  ID: {job.id}")
                print(f"  Title: {job.title}")
                print(f"  Required Skills: {job.required_skills}")
                print(f"  Preferred Skills: {job.preferred_skills}")
            else:
                print(f"\nFAIL: Job record not found")
            
            # Check screening result
            result = await db.execute(
                select(ScreeningResult).where(
                    ScreeningResult.job_id == JOB_ID,
                    ScreeningResult.resume_id == RESUME_ID
                )
            )
            screening = result.scalar_one_or_none()
            if screening:
                print(f"\nPASS: Screening result record exists")
                print(f"  Overall Score: {screening.overall_score}")
                print(f"  TF-IDF Score: {screening.tfidf_score}")
                print(f"  Semantic Score: {screening.semantic_score}")
                print(f"  Skill Match Score: {screening.skill_match_score}")
                print(f"  Matched Skills: {screening.matched_skills}")
                print(f"  Missing Skills: {screening.missing_skills}")
                print(f"  Required Coverage: {screening.required_skill_coverage}")
                print(f"  Preferred Coverage: {screening.preferred_skill_coverage}")
                print(f"  Screening Status: {screening.screening_status}")
                
                # Check JSONB evidence
                if screening.skill_evidence:
                    print(f"\nPASS: Skill evidence JSONB is populated")
                    print(f"  Evidence keys: {list(screening.skill_evidence.keys())[:5]}...")
                else:
                    print(f"\nFAIL: Skill evidence JSONB is empty")
                
                if screening.scoring_strategy:
                    print(f"PASS: Scoring strategy JSONB is populated")
                    print(f"  Algorithm: {screening.scoring_strategy.get('algorithm_version')}")
                else:
                    print(f"FAIL: Scoring strategy JSONB is empty")
                    
            else:
                print(f"\nFAIL: Screening result record not found")
            
    except Exception as e:
        print(f"FAIL: Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
