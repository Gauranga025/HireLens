import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
import app.db.database as db_module

async def main():
    db_module.init_database()
    if db_module.engine is None:
        print("FAIL: Database initialization failed")
        return
    
    try:
        async with db_module.engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"PASS: PostgreSQL connectivity verified (returned: {value})")
            
            # Check database name
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar_one_or_none()
            print(f"PASS: Connected to database: {db_name}")
            
            # Check tables exist
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"PASS: Tables found: {', '.join(tables)}")
            
    except Exception as e:
        print(f"FAIL: PostgreSQL connectivity error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
