"""
Pytest configuration and fixtures for MCP Registry tests.
"""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from mcp_registry.core.database import Base
from mcp_registry.core.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings with in-memory database."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        debug=True,
        host="127.0.0.1",
        port=8000,
    )


@pytest.fixture
async def test_engine(test_settings):
    """Create test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        future=True,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def test_client():
    """Create test FastAPI client."""
    from fastapi.testclient import TestClient
    from mcp_registry.api.app import create_app
    
    app = create_app()
    return TestClient(app)