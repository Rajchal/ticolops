"""Tests for notification service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.notification import NotificationService, NotificationType, NotificationPriority
from app.models.user import User
from app.models.project import Project
from app.core.exceptions import NotFoundError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def notification_service(mock_db):
    """Notification service instance with mocked database."""
    service = NotificationService(mock_db)
    # Mock private methods
    service._send_realtime_notification = AsyncMock()
    service._send_email_notification = AsyncMock()
    return service


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="hashed_password",
        role="student",
        status="active"
    )
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.last_activity = datetime.utcnow()
    return user


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        status="active",
        owner_id=uuid4(),
        settings={"auto_save": True},
        metadata_info={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    return project


class TestNotificationService:
    """Test cases for NotificationService."""

    @pytest.mark.asyncio
    async def test_create_notification_success(self, notification_service):
        """Test successful notification creation."""
        recipient_id = str(uuid4())
        title = "Test Notification"
        message = "This is a test notification"
        
        # Call the method
        result = await notification_service.create_notification(
            notification_type=NotificationType.PROJECT_INVITATION,
            recipient_id=recipient_id,
            title=title,
            message=message,
            priority=NotificationPriority.HIGH
        )
        
        # Assertions
        assert result["type"] == NotificationType.PROJECT_INVITATION.value
        assert result["recipient_id"] == recipient_id
        assert result["title"] == title
        assert result["message"] == message
        assert result["priority"] == NotificationPriority.HIGH.value
        assert result["read"] is False
        assert "id" in result
        assert "created_at" in result
        assert "expires_at" in result
        
        # Verify that real-time and email notifications were attempted
        notification_service._send_realtime_notification.assert_called_once()
        notification_service._send_email_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_invitation_notification_success(self, notification_service, mock_db, sample_user, sample_project):
        """Test successful project invitation notification creation."""
        project_id = str(sample_project.id)
        recipient_email = "recipient@example.com"
        inviter_id = str(sample_user.id)
        role = "collaborator"
        
        # Create recipient user
        recipient_user = User(
            id=uuid4(),
            email=recipient_email,
            name="Recipient User",
            hashed_password="hashed_password",
            role="student",
            status="active"
        )
        
        # Mock database queries
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = sample_project
        
        mock_inviter_result = MagicMock()
        mock_inviter_result.scalar_one_or_none.return_value = sample_user
        
        mock_recipient_result = MagicMock()
        mock_recipient_result.scalar_one_or_none.return_value = recipient_user
        
        mock_db.execute = AsyncMock(side_effect=[mock_project_result, mock_inviter_result, mock_recipient_result])
        
        # Call the method
        result = await notification_service.create_project_invitation_notification(
            project_id, recipient_email, inviter_id, role
        )
        
        # Assertions
        assert result["type"] == NotificationType.PROJECT_INVITATION.value
        assert result["recipient_id"] == str(recipient_user.id)
        assert sample_project.name in result["title"]
        assert sample_user.name in result["message"]
        assert result["priority"] == NotificationPriority.HIGH.value
        assert result["metadata"]["role"] == role

    @pytest.mark.asyncio
    async def test_create_project_invitation_notification_project_not_found(self, notification_service, mock_db):
        """Test project invitation notification when project doesn't exist."""
        project_id = str(uuid4())
        recipient_email = "recipient@example.com"
        inviter_id = str(uuid4())
        role = "collaborator"
        
        # Mock database query to return None for project
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await notification_service.create_project_invitation_notification(
                project_id, recipient_email, inviter_id, role
            )

    @pytest.mark.asyncio
    async def test_create_project_invitation_notification_recipient_not_found(self, notification_service, mock_db, sample_user, sample_project):
        """Test project invitation notification when recipient doesn't exist."""
        project_id = str(sample_project.id)
        recipient_email = "nonexistent@example.com"
        inviter_id = str(sample_user.id)
        role = "collaborator"
        
        # Mock database queries
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = sample_project
        
        mock_inviter_result = MagicMock()
        mock_inviter_result.scalar_one_or_none.return_value = sample_user
        
        mock_recipient_result = MagicMock()
        mock_recipient_result.scalar_one_or_none.return_value = None  # Recipient not found
        
        mock_db.execute = AsyncMock(side_effect=[mock_project_result, mock_inviter_result, mock_recipient_result])
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await notification_service.create_project_invitation_notification(
                project_id, recipient_email, inviter_id, role
            )

    @pytest.mark.asyncio
    async def test_create_member_activity_notification_file_created(self, notification_service, mock_db, sample_user):
        """Test member activity notification for file creation."""
        project_id = str(uuid4())
        actor_id = str(sample_user.id)
        activity_type = "file_created"
        activity_details = {"file_name": "test.html", "file_path": "/test.html"}
        
        # Create another user as project member
        member_user = User(
            id=uuid4(),
            email="member@example.com",
            name="Member User",
            hashed_password="hashed_password",
            role="student",
            status="active"
        )
        
        # Mock database queries
        mock_members_result = MagicMock()
        mock_members_result.all.return_value = [(member_user, "collaborator")]
        
        mock_actor_result = MagicMock()
        mock_actor_result.scalar_one_or_none.return_value = sample_user
        
        mock_db.execute = AsyncMock(side_effect=[mock_members_result, mock_actor_result])
        
        # Call the method
        result = await notification_service.create_member_activity_notification(
            project_id, actor_id, activity_type, activity_details
        )
        
        # Assertions
        assert len(result) == 1
        notification = result[0]
        assert notification["type"] == NotificationType.FILE_CREATED.value
        assert notification["recipient_id"] == str(member_user.id)
        assert "test.html" in notification["title"]
        assert sample_user.name in notification["message"]

    @pytest.mark.asyncio
    async def test_create_member_activity_notification_no_actor(self, notification_service, mock_db):
        """Test member activity notification when actor doesn't exist."""
        project_id = str(uuid4())
        actor_id = str(uuid4())
        activity_type = "file_created"
        activity_details = {"file_name": "test.html"}
        
        # Mock database queries
        mock_members_result = MagicMock()
        mock_members_result.all.return_value = []
        
        mock_actor_result = MagicMock()
        mock_actor_result.scalar_one_or_none.return_value = None  # Actor not found
        
        mock_db.execute = AsyncMock(side_effect=[mock_members_result, mock_actor_result])
        
        # Call the method
        result = await notification_service.create_member_activity_notification(
            project_id, actor_id, activity_type, activity_details
        )
        
        # Assertions
        assert len(result) == 0  # No notifications created when actor not found

    @pytest.mark.asyncio
    async def test_create_settings_change_notification_success(self, notification_service, mock_db, sample_user, sample_project):
        """Test successful settings change notification creation."""
        project_id = str(sample_project.id)
        actor_id = str(sample_user.id)
        changes = [
            {"setting": "auto_save", "old_value": False, "new_value": True},
            {"setting": "max_collaborators", "old_value": 5, "new_value": 10}
        ]
        
        # Create member user
        member_user = User(
            id=uuid4(),
            email="member@example.com",
            name="Member User",
            hashed_password="hashed_password",
            role="student",
            status="active"
        )
        
        # Mock database queries
        mock_members_result = MagicMock()
        mock_members_result.scalars.return_value.all.return_value = [member_user]
        
        mock_actor_result = MagicMock()
        mock_actor_result.scalar_one_or_none.return_value = sample_user
        
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = sample_project
        
        mock_db.execute = AsyncMock(side_effect=[mock_members_result, mock_actor_result, mock_project_result])
        
        # Call the method
        result = await notification_service.create_settings_change_notification(
            project_id, actor_id, changes
        )
        
        # Assertions
        assert len(result) == 1
        notification = result[0]
        assert notification["type"] == NotificationType.SETTINGS_CHANGED.value
        assert notification["recipient_id"] == str(member_user.id)
        assert sample_project.name in notification["title"]
        assert sample_user.name in notification["message"]
        assert notification["metadata"]["changes"] == changes

    @pytest.mark.asyncio
    async def test_create_deployment_notification_success(self, notification_service, mock_db, sample_user, sample_project):
        """Test successful deployment notification creation."""
        project_id = str(sample_project.id)
        deployment_id = str(uuid4())
        status = "success"
        deployed_by = str(sample_user.id)
        deployment_url = "https://example.com"
        
        # Create member user
        member_user = User(
            id=uuid4(),
            email="member@example.com",
            name="Member User",
            hashed_password="hashed_password",
            role="student",
            status="active"
        )
        
        # Mock database queries
        mock_members_result = MagicMock()
        mock_members_result.scalars.return_value.all.return_value = [member_user, sample_user]
        
        mock_deployer_result = MagicMock()
        mock_deployer_result.scalar_one_or_none.return_value = sample_user
        
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = sample_project
        
        mock_db.execute = AsyncMock(side_effect=[mock_members_result, mock_deployer_result, mock_project_result])
        
        # Call the method
        result = await notification_service.create_deployment_notification(
            project_id, deployment_id, status, deployed_by, deployment_url
        )
        
        # Assertions
        assert len(result) == 2  # Both members get notifications
        notification = result[0]
        assert notification["type"] == NotificationType.DEPLOYMENT_SUCCESS.value
        assert "successful" in notification["title"]
        assert notification["metadata"]["deployment_url"] == deployment_url

    @pytest.mark.asyncio
    async def test_create_deployment_notification_failed(self, notification_service, mock_db, sample_user, sample_project):
        """Test deployment notification for failed deployment."""
        project_id = str(sample_project.id)
        deployment_id = str(uuid4())
        status = "failed"
        deployed_by = str(sample_user.id)
        error_message = "Build failed"
        
        # Mock database queries
        mock_members_result = MagicMock()
        mock_members_result.scalars.return_value.all.return_value = [sample_user]
        
        mock_deployer_result = MagicMock()
        mock_deployer_result.scalar_one_or_none.return_value = sample_user
        
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = sample_project
        
        mock_db.execute = AsyncMock(side_effect=[mock_members_result, mock_deployer_result, mock_project_result])
        
        # Call the method
        result = await notification_service.create_deployment_notification(
            project_id, deployment_id, status, deployed_by, error_message=error_message
        )
        
        # Assertions
        assert len(result) == 1
        notification = result[0]
        assert notification["type"] == NotificationType.DEPLOYMENT_FAILED.value
        assert notification["priority"] == NotificationPriority.HIGH.value
        assert "failed" in notification["title"]
        assert notification["metadata"]["error_message"] == error_message

    @pytest.mark.asyncio
    async def test_create_conflict_notification_success(self, notification_service, mock_db):
        """Test successful conflict notification creation."""
        project_id = str(uuid4())
        file_path = "/src/index.html"
        
        # Create conflicting users
        user1 = User(id=uuid4(), email="user1@example.com", name="User One", hashed_password="hash", role="student", status="active")
        user2 = User(id=uuid4(), email="user2@example.com", name="User Two", hashed_password="hash", role="student", status="active")
        conflicting_users = [str(user1.id), str(user2.id)]
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [user1, user2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await notification_service.create_conflict_notification(
            project_id, file_path, conflicting_users
        )
        
        # Assertions
        assert len(result) == 2  # Both users get notifications
        for notification in result:
            assert notification["type"] == NotificationType.CONFLICT_DETECTED.value
            assert notification["priority"] == NotificationPriority.HIGH.value
            assert file_path in notification["title"]
            assert "conflict" in notification["message"].lower()

    @pytest.mark.asyncio
    async def test_get_user_notifications(self, notification_service):
        """Test getting user notifications."""
        user_id = str(uuid4())
        
        # Call the method (currently returns empty list)
        result = await notification_service.get_user_notifications(user_id)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 0  # Current implementation returns empty list

    @pytest.mark.asyncio
    async def test_mark_notification_read(self, notification_service):
        """Test marking notification as read."""
        notification_id = str(uuid4())
        user_id = str(uuid4())
        
        # Call the method
        result = await notification_service.mark_notification_read(notification_id, user_id)
        
        # Assertions
        assert result is True  # Current implementation always returns True

    @pytest.mark.asyncio
    async def test_mark_all_notifications_read(self, notification_service):
        """Test marking all notifications as read."""
        user_id = str(uuid4())
        project_id = str(uuid4())
        
        # Call the method
        result = await notification_service.mark_all_notifications_read(user_id, project_id)
        
        # Assertions
        assert result == 0  # Current implementation returns 0