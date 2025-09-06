"""
Database initialization and session management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Global engine and session maker
engine = None
async_session_maker = None


def init_database_sync(database_url: str = None) -> None:
    """Initialize database engine and session maker (synchronous)."""
    global engine, async_session_maker
    
    if database_url is None:
        settings = get_settings()
        database_url = settings.database_url
    
    settings = get_settings()
    engine = create_async_engine(
        database_url,
        echo=settings.database_echo or settings.debug,
        future=True,
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def create_tables() -> None:
    """Create database tables."""
    # Import models to register them with Base
    from ..db.models import Server, Capability
    
    if engine is None:
        init_database_sync()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_database(database_url: str = None) -> None:
    """Initialize database engine and session maker (async wrapper)."""
    init_database_sync(database_url)


async def get_session() -> AsyncSession:
    """Get database session."""
    if async_session_maker is None:
        await init_database()
    
    async with async_session_maker() as session:
        yield session


def get_engine():
    """Get database engine."""
    return engine


def get_session_maker():
    """Get async session maker."""
    return async_session_maker