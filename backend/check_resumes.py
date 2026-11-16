import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
import app.db.database as db_module
from app.models.resume import Resume

async def main():
    db_module.init_database()
    if db_module.AsyncSessionLocal is None:
        print("Database initialization failed")
        return
    async with db_module.AsyncSessionLocal() as db:
        result = await db.execute(select(Resume).limit(5))
        resumes = list(result.scalars().all())
        if resumes:
            for r in resumes:
                print(f'Resume ID: {r.id}, Filename: {r.original_filename}')
        else:
            print('No resumes found')

if __name__ == "__main__":
    asyncio.run(main())
