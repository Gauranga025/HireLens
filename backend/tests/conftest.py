"""Shared database-safety fixtures for the automated backend test suite.

Automated tests never use the application's main database. A separately
configured disposable database is required, and every write is rolled back.
"""
from pathlib import Path
from typing import AsyncGenerator

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.db.base import Base


def validate_test_database_url(
    url: str | None,
    main_database_url: str | None = None,
) -> None:
    """Reject missing, malformed, main, or non-disposable test databases."""
    if not url:
        raise RuntimeError(
            "TEST_DATABASE_URL must be configured for database-backed tests; "
            "DATABASE_URL is never used as a fallback."
        )

    try:
        test_url = make_url(url)
        main_url = make_url(main_database_url or settings.DATABASE_URL)
    except ArgumentError as exc:
        raise RuntimeError(f"Invalid TEST_DATABASE_URL: {exc}") from exc

    if not test_url.database:
        raise RuntimeError("TEST_DATABASE_URL must include an explicit database name.")

    same_database = (
        test_url.get_backend_name() == main_url.get_backend_name()
        and test_url.host == main_url.host
        and test_url.port == main_url.port
        and test_url.database == main_url.database
    )
    if same_database:
        raise RuntimeError(
            "TEST_DATABASE_URL must not point to the main DATABASE_URL database."
        )

    database_name = test_url.database.lower()
    if not database_name.endswith("_test"):
        raise RuntimeError(
            "TEST_DATABASE_URL database name must be explicitly disposable "
            "and end with '_test'."
        )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "db: test requires the disposable TEST_DATABASE_URL database"
    )
    config.addinivalue_line(
        "markers", "e2e: test exercises the API through the ASGI transport"
    )

    # If a test URL was supplied, reject an unsafe value before collection.
    # Fixtures separately reject a missing URL when a DB-backed test runs.
    if settings.TEST_DATABASE_URL:
        validate_test_database_url(settings.TEST_DATABASE_URL)


@pytest.fixture
async def disposable_db_engine() -> AsyncGenerator:
    """Create an engine for the disposable test database only."""
    validate_test_database_url(settings.TEST_DATABASE_URL)

    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def disposable_db_session(
    disposable_db_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session whose outer transaction is always rolled back."""
    connection = await disposable_db_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest.fixture
async def db_session(disposable_db_session: AsyncSession):
    """Backward-compatible name for the rollback-only database session."""
    yield disposable_db_session


@pytest.fixture
async def disposable_api_client(disposable_db_session: AsyncSession):
    """ASGI client whose database dependency uses the rollback-only session."""
    from httpx import ASGITransport, AsyncClient

    from app.db.session import get_db
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield disposable_db_session

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override


TESTS_DIR = Path(__file__).parent
