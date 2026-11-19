from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.config import settings


engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def init_database() -> None:
    """Initialize the database engine and session factory."""
    global engine, AsyncSessionLocal
    
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_async_session() -> AsyncSession:
    """Dependency for getting async database sessions."""
    if AsyncSessionLocal is None:
        init_database()
    
    async with AsyncSessionLocal() as session:
        yield session


async def check_database_connectivity() -> bool:
    """Check if database connection is working."""
    if engine is None:
        return False
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_database() -> None:
    """Close the database engine."""
    global engine, AsyncSessionLocal
    
    if engine is not None:
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None

