"""
Integration tests for user database operations.
These tests require a test database to be set up.
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.core.database import Base
from app.models.user import User, UserRoleEnum, UserStatusEnum
from app.schemas.user import UserPreferences


# Test database URL - should be different from production
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()


class TestUserDatabaseOperations:
    """Test user database operations."""

    async def test_create_user(self, test_session: AsyncSession):
        """Test creating a user in the database."""
        user = User(
            email="test@example.com",
            name="Test User",
            hashed_password="hashed_password_here",
            role=UserRoleEnum.STUDENT,
            status=UserStatusEnum.ONLINE,
            preferences={
                "email_notifications": True,
                "push_notifications": True,
                "activity_visibility": True,
                "conflict_alerts": True,
                "deployment_notifications": True
            }
        )
        
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == UserRoleEnum.STUDENT
        assert user.status == UserStatusEnum.ONLINE
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.last_activity is not None

    @pytest.mark.asyncio
    async def test_user_unique_email(self, test_session: AsyncSession):
        """Test that user email must be unique."""
        user1 = User(
            email="unique@example.com",
            name="User One",
            hashed_password="password1",
            role=UserRoleEnum.STUDENT,
            status=UserStatusEnum.ONLINE
        )
        
        user2 = User(
            email="unique@example.com",  # Same email
            name="User Two",
            hashed_password="password2",
            role=UserRoleEnum.COORDINATOR,
            status=UserStatusEnum.OFFLINE
        )
        
        test_session.add(user1)
        await test_session.commit()
        
        test_session.add(user2)
        
        # This should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # SQLAlchemy will raise an IntegrityError
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_user_default_values(self, test_session: AsyncSession):
        """Test user model default values."""
        user = User(
            email="defaults@example.com",
            name="Default User",
            hashed_password="password"
        )
        
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # Test default values
        assert user.role == UserRoleEnum.STUDENT
        assert user.status == UserStatusEnum.OFFLINE
        assert user.avatar is None
        assert isinstance(user.preferences, dict)
        assert user.preferences["email_notifications"] is True
        assert user.preferences["push_notifications"] is True
        assert user.preferences["activity_visibility"] is True
        assert user.preferences["conflict_alerts"] is True
        assert user.preferences["deployment_notifications"] is True

    @pytest.mark.asyncio
    async def test_user_update(self, test_session: AsyncSession):
        """Test updating user information."""
        user = User(
            email="update@example.com",
            name="Original Name",
            hashed_password="password",
            role=UserRoleEnum.STUDENT,
            status=UserStatusEnum.OFFLINE
        )
        
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        original_updated_at = user.updated_at
        
        # Update user
        user.name = "Updated Name"
        user.status = UserStatusEnum.ONLINE
        user.preferences = {
            "email_notifications": False,
            "push_notifications": True,
            "activity_visibility": False,
            "conflict_alerts": True,
            "deployment_notifications": False
        }
        
        await test_session.commit()
        await test_session.refresh(user)
        
        assert user.name == "Updated Name"
        assert user.status == UserStatusEnum.ONLINE
        assert user.preferences["email_notifications"] is False
        assert user.preferences["activity_visibility"] is False
        # updated_at should be automatically updated (if trigger is set up)

    @pytest.mark.asyncio
    async def test_user_query_by_email(self, test_session: AsyncSession):
        """Test querying user by email."""
        user = User(
            email="query@example.com",
            name="Query User",
            hashed_password="password",
            role=UserRoleEnum.COORDINATOR
        )
        
        test_session.add(user)
        await test_session.commit()
        
        # Query by email
        result = await test_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": "query@example.com"}
        )
        found_user = result.fetchone()
        
        assert found_user is not None
        assert found_user.email == "query@example.com"
        assert found_user.name == "Query User"

    @pytest.mark.asyncio
    async def test_user_delete(self, test_session: AsyncSession):
        """Test deleting a user."""
        user = User(
            email="delete@example.com",
            name="Delete User",
            hashed_password="password"
        )
        
        test_session.add(user)
        await test_session.commit()
        user_id = user.id
        
        # Delete user
        await test_session.delete(user)
        await test_session.commit()
        
        # Verify user is deleted
        result = await test_session.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {"id": str(user_id)}
        )
        found_user = result.fetchone()
        
        assert found_user is None