import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
import app.db.database as db_module
from app.models.resume import Resume

async def main():
    db_module.init_database()
    if db_module.engine is None:
        print("FAIL: Database initialization failed")
        return
    
    try:
        async with db_module.AsyncSessionLocal() as db:
            result = await db.execute(
                select(Resume).order_by(Resume.created_at.desc()).limit(5)
            )
            resumes = list(result.scalars().all())
            
            if not resumes:
                print("FAIL: No resumes found in database")
                return
            
            print(f"PASS: Found {len(resumes)} recent resumes in database")
            for r in resumes:
                print(f"  - ID: {r.id}")
                print(f"    Filename: {r.original_filename}")
                print(f"    Skills: {r.skills}")
                print(f"    Status: {r.processing_status}")
                print()
            
            # Return the most recent resume ID
            print(f"Using resume ID: {resumes[0].id}")
            
    except Exception as e:
        print(f"FAIL: Error querying resumes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
