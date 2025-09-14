"""Tests for activity tracking service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock

from app.services.activity import ActivityService, PresenceService
from app.models.activity import Activity, UserPresence, ActivityType, ActivityPriority
from app.models.user import User
from app.models.project import Project
from app.schemas.activity import (
    ActivityCreate, ActivityUpdate, ActivityFilter,
    UserPresenceCreate, UserPresenceStatus
)
from app.core.exceptions import NotFoundError, ValidationError


@pytest.fixture
def activity_service(mock_db_session):
    """Activity service instance with mocked database."""
    return ActivityService(mock_db_session)


@pytest.fixture
def presence_service(mock_db_session):
    """Presence service instance with mocked database."""
    return PresenceService(mock_db_session)


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="hashed_password",
        role="student",
        status="active"
    )


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    return Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        owner_id=uuid4()
    )


@pytest.fixture
def sample_activity_create():
    """Sample activity creation data."""
    return ActivityCreate(
        type=ActivityType.CODING,
        title="Working on user authentication",
        description="Implementing JWT authentication system",
        location="src/auth/jwt.py",
        priority=ActivityPriority.HIGH,
        metadata={"language": "python", "framework": "fastapi"}
    )


class TestActivityService:
    """Test cases for ActivityService."""

    @pytest.mark.asyncio
    async def test_create_activity_success(self, activity_service, mock_db_session, sample_user, sample_activity_create):
        """Test successful activity creation."""
        # Mock database queries
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_user
        
        # Create activity
        result = await activity_service.create_activity(str(sample_user.id), sample_activity_create)
        
        # Verify activity was created
        assert isinstance(result, Activity)
        assert result.type == sample_activity_create.type.value
        assert result.title == sample_activity_create.title
        assert result.user_id == sample_user.id
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_activity_user_not_found(self, activity_service, mock_db_session, sample_activity_create):
        """Test activity creation with non-existent user."""
        # Mock user not found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Attempt to create activity
        with pytest.raises(NotFoundError, match="User with ID .* not found"):
            await activity_service.create_activity(str(uuid4()), sample_activity_create)

    @pytest.mark.asyncio
    async def test_update_activity_success(self, activity_service, mock_db_session, sample_user):
        """Test successful activity update."""
        # Create sample activity
        activity = Activity(
            id=uuid4(),
            type=ActivityType.CODING.value,
            title="Original title",
            user_id=sample_user.id,
            priority=ActivityPriority.MEDIUM.value,
            metadata={}
        )
        
        # Mock database query
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = activity
        
        # Update data
        update_data = ActivityUpdate(
            title="Updated title",
            priority=ActivityPriority.HIGH,
            description="Updated description"
        )
        
        # Update activity
        result = await activity_service.update_activity(str(activity.id), str(sample_user.id), update_data)
        
        # Verify updates
        assert result.title == "Updated title"
        assert result.priority == ActivityPriority.HIGH.value
        assert result.description == "Updated description"
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_activity_not_found(self, activity_service, mock_db_session):
        """Test activity update with non-existent activity."""
        # Mock activity not found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        update_data = ActivityUpdate(title="Updated title")
        
        # Attempt to update activity
        with pytest.raises(NotFoundError, match="Activity with ID .* not found"):
            await activity_service.update_activity(str(uuid4()), str(uuid4()), update_data)

    @pytest.mark.asyncio
    async def test_get_activities_with_filters(self, activity_service, mock_db_session):
        """Test getting activities with various filters."""
        # Mock activities
        activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Activity 1",
                user_id=uuid4(),
                priority=ActivityPriority.HIGH.value,
                metadata={},
                created_at=datetime.utcnow()
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.TESTING.value,
                title="Activity 2",
                user_id=uuid4(),
                priority=ActivityPriority.MEDIUM.value,
                metadata={},
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = activities
        
        # Create filters
        filters = ActivityFilter(
            activity_types=[ActivityType.CODING, ActivityType.TESTING],
            priority=ActivityPriority.HIGH,
            limit=10,
            offset=0
        )
        
        # Get activities
        result = await activity_service.get_activities(filters)
        
        # Verify results
        assert len(result) == 2
        assert all(isinstance(activity, Activity) for activity in result)
        
        # Verify database query was executed
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_activity_success(self, activity_service, mock_db_session, sample_user):
        """Test successfully ending an activity."""
        # Create sample activity with start time
        start_time = datetime.utcnow() - timedelta(minutes=30)
        activity = Activity(
            id=uuid4(),
            type=ActivityType.CODING.value,
            title="Test activity",
            user_id=sample_user.id,
            priority=ActivityPriority.MEDIUM.value,
            metadata={},
            started_at=start_time
        )
        
        # Mock database query
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = activity
        
        # End activity
        result = await activity_service.end_activity(str(activity.id), str(sample_user.id))
        
        # Verify activity was ended
        assert result.ended_at is not None
        assert result.duration_seconds is not None
        assert int(result.duration_seconds) > 0  # Should have some duration
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_stats(self, activity_service, mock_db_session):
        """Test getting activity statistics."""
        # Mock activities for stats
        activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Activity 1",
                user_id=uuid4(),
                priority=ActivityPriority.HIGH.value,
                location="src/main.py",
                metadata={},
                created_at=datetime.utcnow()
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Activity 2",
                user_id=uuid4(),
                priority=ActivityPriority.MEDIUM.value,
                location="src/auth.py",
                metadata={},
                created_at=datetime.utcnow()
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.TESTING.value,
                title="Activity 3",
                user_id=uuid4(),
                priority=ActivityPriority.LOW.value,
                location="tests/test_main.py",
                metadata={},
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = activities
        
        # Get stats
        stats = await activity_service.get_activity_stats(days=7)
        
        # Verify stats
        assert stats.total_activities == 3
        assert stats.activities_by_type[ActivityType.CODING.value] == 2
        assert stats.activities_by_type[ActivityType.TESTING.value] == 1
        assert stats.activities_by_priority[ActivityPriority.HIGH.value] == 1
        assert len(stats.most_active_locations) == 3
        assert stats.collaboration_metrics["unique_locations"] == 3


class TestPresenceService:
    """Test cases for PresenceService."""

    @pytest.mark.asyncio
    async def test_update_presence_new_record(self, presence_service, mock_db_session, sample_user):
        """Test updating presence with new record creation."""
        # Mock no existing presence record
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Presence data
        presence_data = UserPresenceCreate(
            status=UserPresenceStatus.ONLINE,
            current_location="src/main.py",
            current_activity=ActivityType.CODING,
            session_id="session_123",
            metadata={"browser": "chrome"}
        )
        
        # Update presence
        result = await presence_service.update_presence(str(sample_user.id), presence_data)
        
        # Verify presence record was created
        assert isinstance(result, UserPresence)
        assert result.user_id == sample_user.id
        assert result.status == UserPresenceStatus.ONLINE.value
        assert result.current_location == "src/main.py"
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_presence_existing_record(self, presence_service, mock_db_session, sample_user):
        """Test updating existing presence record."""
        # Create existing presence record
        existing_presence = UserPresence(
            id=uuid4(),
            user_id=sample_user.id,
            status=UserPresenceStatus.AWAY.value,
            current_location="old_location.py",
            metadata={"old": "data"}
        )
        
        # Mock existing presence record
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_presence
        
        # New presence data
        presence_data = UserPresenceCreate(
            status=UserPresenceStatus.ONLINE,
            current_location="new_location.py",
            metadata={"new": "data"}
        )
        
        # Update presence
        result = await presence_service.update_presence(str(sample_user.id), presence_data)
        
        # Verify presence was updated
        assert result.status == UserPresenceStatus.ONLINE.value
        assert result.current_location == "new_location.py"
        assert "new" in result.metadata
        
        # Verify database operations (no add, just commit and refresh)
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_online_users(self, presence_service, mock_db_session):
        """Test getting online users."""
        # Mock online users
        online_users = [
            UserPresence(
                id=uuid4(),
                user_id=uuid4(),
                status=UserPresenceStatus.ONLINE.value,
                last_activity=datetime.utcnow()
            ),
            UserPresence(
                id=uuid4(),
                user_id=uuid4(),
                status=UserPresenceStatus.ACTIVE.value,
                last_activity=datetime.utcnow()
            )
        ]
        
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = online_users
        
        # Get online users
        result = await presence_service.get_online_users()
        
        # Verify results
        assert len(result) == 2
        assert all(isinstance(presence, UserPresence) for presence in result)
        assert all(presence.status in ["online", "active"] for presence in result)

    @pytest.mark.asyncio
    async def test_detect_collaboration_opportunities(self, presence_service, mock_db_session, sample_user):
        """Test detecting collaboration opportunities."""
        # Mock recent activities for current user
        user_activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Working on auth",
                user_id=sample_user.id,
                location="src/auth.py",
                created_at=datetime.utcnow()
            )
        ]
        
        # Mock other users' activities
        other_activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Working on auth tests",
                user_id=uuid4(),
                location="tests/test_auth.py",  # Related location
                created_at=datetime.utcnow()
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Working on same file",
                user_id=uuid4(),
                location="src/auth.py",  # Same location
                created_at=datetime.utcnow()
            )
        ]
        
        # Mock database queries
        mock_db_session.execute.side_effect = [
            # First call for user's activities
            AsyncMock(scalars=AsyncMock(return_value=AsyncMock(all=AsyncMock(return_value=user_activities)))),
            # Second call for other users' activities
            AsyncMock(scalars=AsyncMock(return_value=AsyncMock(all=AsyncMock(return_value=other_activities))))
        ]
        
        # Detect opportunities
        opportunities = await presence_service.detect_collaboration_opportunities(
            str(sample_user.id), str(uuid4())
        )
        
        # Verify opportunities were detected
        assert len(opportunities) >= 1
        assert any(opp.type == "same_file" for opp in opportunities)

    @pytest.mark.asyncio
    async def test_detect_conflicts(self, presence_service, mock_db_session):
        """Test detecting conflicts."""
        # Mock recent activities with conflicts
        user1_id = uuid4()
        user2_id = uuid4()
        
        conflicting_activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="User 1 editing",
                user_id=user1_id,
                location="src/shared.py",
                created_at=datetime.utcnow()
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="User 2 editing",
                user_id=user2_id,
                location="src/shared.py",  # Same location - conflict!
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = conflicting_activities
        
        # Detect conflicts
        conflicts = await presence_service.detect_conflicts(str(uuid4()))
        
        # Verify conflicts were detected
        assert len(conflicts) >= 1
        conflict = conflicts[0]
        assert conflict.type == "concurrent_editing"
        assert len(conflict.users) == 2
        assert conflict.location == "src/shared.py"
        assert conflict.severity in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence(self, presence_service, mock_db_session):
        """Test cleaning up stale presence records."""
        # Mock stale presence records
        stale_time = datetime.utcnow() - timedelta(hours=25)
        stale_records = [
            UserPresence(
                id=uuid4(),
                user_id=uuid4(),
                status=UserPresenceStatus.ONLINE.value,
                last_activity=stale_time
            ),
            UserPresence(
                id=uuid4(),
                user_id=uuid4(),
                status=UserPresenceStatus.ACTIVE.value,
                last_activity=stale_time
            )
        ]
        
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = stale_records
        
        # Cleanup stale presence
        cleaned_count = await presence_service.cleanup_stale_presence(hours=24)
        
        # Verify cleanup
        assert cleaned_count == 2
        assert all(record.status == "offline" for record in stale_records)
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_activity_service_integration(activity_service, mock_db_session, sample_user, sample_project):
    """Integration test for activity service workflow."""
    # Mock database responses
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
        sample_user,  # User lookup for create
        sample_project,  # Project lookup for create
    ]
    
    # Create activity
    activity_data = ActivityCreate(
        type=ActivityType.CODING,
        title="Integration test activity",
        project_id=str(sample_project.id),
        location="src/integration.py"
    )
    
    activity = await activity_service.create_activity(str(sample_user.id), activity_data)
    
    # Verify activity creation
    assert activity.type == ActivityType.CODING.value
    assert activity.title == "Integration test activity"
    assert activity.user_id == sample_user.id
    assert activity.project_id == sample_project.id
    
    # Verify database interactions
    assert mock_db_session.add.call_count == 1
    assert mock_db_session.commit.call_count == 1
    assert mock_db_session.refresh.call_count == 1