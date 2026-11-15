from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import database


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    if database.AsyncSessionLocal is None:
        database.init_database()
    
    async with database.AsyncSessionLocal() as session:
        yield session

