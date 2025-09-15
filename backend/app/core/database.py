"""
Database configuration and session management using SQLAlchemy async.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def init_db():
    """Initialize database connection."""
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
            # In debug/demo mode, ensure newer demo columns exist to avoid
            # failing service code when migrations haven't been run.
            if settings.DEBUG:
                # Add columns if they don't exist (Postgres IF NOT EXISTS for columns)
                try:
                    await conn.execute(text(
                        """
                        ALTER TABLE projects
                        ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active',
                        ADD COLUMN IF NOT EXISTS settings JSON DEFAULT '{}'::JSON,
                        ADD COLUMN IF NOT EXISTS metadata_info JSON DEFAULT '{}'::JSON,
                        ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP WITH TIME ZONE NULL;
                        """
                    ))
                except Exception:
                    # If projectstatus enum type doesn't exist or the table is missing,
                    # skip and let application logic handle it (this is demo-friendly).
                    logger.exception("Could not run demo schema adjustments; continuing")
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()