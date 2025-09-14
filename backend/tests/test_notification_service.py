"""Tests for notification service functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import (
    NotificationService, EmailProvider, WebhookProvider, 
    SlackProvider, InAppProvider
)
from app.models.notification import (
    Notification, NotificationPreferences, NotificationDeliveryLog,
    NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
)
from app.models.user import User
from app.core.exceptions import NotFoundError


class TestNotificationProviders:
    """Test notification delivery providers."""
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            id="user-123",
            name="Test User",
            email="test@example.com"
        )
    
    @pytest.fixture
    def sample_notification(self):
        """Create sample notification for testing."""
        return Notification(
            id="notification-123",
            user_id="user-123",
            type=NotificationType.DEPLOYMENT_SUCCESS.value,
            title="Deployment Successful",
            message="Your deployment completed successfully!",
            priority=NotificationPriority.NORMAL.value,
            action_url="https://app.example.com/deployments/123",
            action_text="View Deployment",
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_preferences(self):
        """Create sample notification preferences."""
        return NotificationPreferences(
            id="prefs-123",
            user_id="user-123",
            enabled=True,
            email_enabled=True,
            email_address="test@example.com",
            webhook_enabled=True,
            webhook_url="https://webhook.example.com",
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/services/test",
            slack_channel="#general"
        )
    
    @pytest.mark.asyncio
    async def test_email_provider_success(self, sample_notification, sample_user, sample_preferences):
        """Test successful email delivery."""
        provider = EmailProvider()
        
        success, error, response = await provider.send_notification(
            sample_notification, sample_user, sample_preferences
        )
        
        assert success is True
        assert error is None
        assert response is not None
        assert response["recipient"] == "test@example.com"
        assert "Deployment Successful" in response["subject"]
    
    @pytest.mark.asyncio
    async def test_email_provider_no_email(self, sample_notification, sample_user, sample_preferences):
        """Test email delivery with no email address."""
        sample_user.email = None
        sample_preferences.email_address = None
        
        provider = EmailProvider()
        
        success, error, response = await provider.send_notification(
            sample_notification, sample_user, sample_preferences
        )
        
        assert success is False
        assert "No email address available" in error
        assert response is None
    
    @pytest.mark.asyncio
    async def test_webhook_provider_success(self, sample_notification, sample_user, sample_preferences):
        """Test successful webhook delivery."""
        provider = WebhookProvider()
        
        success, error, response = await provider.send_notification(
            sample_notification, sample_user, sample_preferences
        )
        
        assert success is True
        assert error is None
        assert response is not None
        assert response["webhook_url"] == "https://webhook.example.com"
    
    @pytest.mark.asyncio
    async def test_webhook_provider_no_url(self, sample_notification, sample_user, sample_preferences):
        """Test webhook delivery with no URL configured."""
        sample_preferences.webhook_url = None
        
        provider = WebhookProvider()
        
        success, error, response = await provider.send_notification(
            sample_notification, sample_user, sample_preferences
        )
        
        assert success is False
        assert "No webhook URL configured" in error
        assert response is None
    
    @pytest.mark.asyncio
    async def test_slack_provider_success(self, sample_notification, sample_user, sample_preferences):
        """Test successful Slack delivery."""
        provider = SlackProvider()
        
        success, error, response = await provider.send_notification(
            sample_notification, sample_user, sample_preferences
        )
        
        assert success is True
        assert error is None
        assert response is not None
        assert response["channel"] == "#general"
    
    @pytest.mark.asyncio
    async def test_slack_provider_priority_colors(self, sample_notification, sample_user, sample_preferences):
        """Test Slack color mapping for different priorities."""
        provider = SlackProvider()
        
        # Test different priorities
        priorities = [
            (NotificationPriority.LOW.value, "#36a64f"),
            (NotificationPriority.NORMAL.value, "#2196F3"),
            (NotificationPriority.HIGH.value, "#ff9800"),
            (NotificationPriority.URGENT.value, "#f44336")
        ]
        
        for priority, expected_color in priorities:
            color = provider._get_slack_color(priority)
            assert color == expected_color
    
    @pytest.mark.asyncio
    async def test_in_app_provider_success(self, sample_notification, sample_user, sample_preferences):
        """Test successful in-app delivery."""
        provider = InAppProvider()
        
        success, error, response = await provider.send_notification(
            sample_notification, sample_user, sample_preferences
        )
        
        assert success is True
        assert error is None
        assert response is not None
        assert response["websocket_broadcast"] is True
        assert response["user_id"] == "user-123"


@pytest.mark.asyncio
class TestNotificationService:
    """Test notification service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def notification_service(self, mock_db):
        """Create notification service instance."""
        return NotificationService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            id="user-123",
            name="Test User",
            email="test@example.com"
        )
    
    @pytest.fixture
    def sample_preferences(self):
        """Create sample notification preferences."""
        return NotificationPreferences(
            id="prefs-123",
            user_id="user-123",
            enabled=True,
            email_enabled=True,
            in_app_enabled=True,
            type_preferences={},
            project_preferences={}
        )
    
    async def test_create_notification(self, notification_service, sample_preferences):
        """Test creating a notification."""
        # Mock get_user_preferences
        with patch.object(notification_service, 'get_user_preferences', return_value=sample_preferences):
            # Mock database operations
            notification_service.db.add = AsyncMock()
            notification_service.db.commit = AsyncMock()
            notification_service.db.refresh = AsyncMock()
            
            # Mock _deliver_notification
            with patch.object(notification_service, '_deliver_notification') as mock_deliver:
                notification = await notification_service.create_notification(
                    user_id="user-123",
                    notification_type=NotificationType.DEPLOYMENT_SUCCESS,
                    title="Test Notification",
                    message="This is a test notification"
                )
        
        # Verify notification creation
        notification_service.db.add.assert_called_once()
        notification_service.db.commit.assert_called_once()
        notification_service.db.refresh.assert_called_once()
    
    async def test_create_bulk_notifications(self, notification_service):
        """Test creating bulk notifications."""
        notifications_data = [
            {
                "user_id": "user-123",
                "type": NotificationType.DEPLOYMENT_SUCCESS.value,
                "title": "Notification 1",
                "message": "Message 1",
                "channels": [NotificationChannel.IN_APP.value]
            },
            {
                "user_id": "user-456",
                "type": NotificationType.DEPLOYMENT_FAILED.value,
                "title": "Notification 2",
                "message": "Message 2",
                "channels": [NotificationChannel.EMAIL.value]
            }
        ]
        
        # Mock database operations
        notification_service.db.add_all = AsyncMock()
        notification_service.db.commit = AsyncMock()
        notification_service.db.refresh = AsyncMock()
        
        # Mock _deliver_notification
        with patch.object(notification_service, '_deliver_notification'):
            notifications = await notification_service.create_bulk_notifications(notifications_data)
        
        # Verify bulk creation
        notification_service.db.add_all.assert_called_once()
        notification_service.db.commit.assert_called_once()
        assert len(notifications) == 2
    
    async def test_get_user_notifications(self, notification_service):
        """Test getting user notifications."""
        # Mock notifications
        mock_notifications = [
            Notification(
                id="notification-1",
                user_id="user-123",
                type=NotificationType.DEPLOYMENT_SUCCESS.value,
                title="Notification 1",
                message="Message 1",
                created_at=datetime.utcnow()
            ),
            Notification(
                id="notification-2",
                user_id="user-123",
                type=NotificationType.DEPLOYMENT_FAILED.value,
                title="Notification 2",
                message="Message 2",
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
        ]
        
        # Mock database query
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalars.return_value.all.return_value = mock_notifications
        
        notifications = await notification_service.get_user_notifications("user-123")
        
        assert len(notifications) == 2
        assert notifications[0].id == "notification-1"
        assert notifications[1].id == "notification-2"
    
    async def test_get_user_notifications_with_filters(self, notification_service):
        """Test getting user notifications with filters."""
        # Mock filtered notifications
        mock_notifications = [
            Notification(
                id="notification-1",
                user_id="user-123",
                type=NotificationType.DEPLOYMENT_SUCCESS.value,
                title="Notification 1",
                message="Message 1",
                read_at=None,  # Unread
                created_at=datetime.utcnow()
            )
        ]
        
        # Mock database query
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalars.return_value.all.return_value = mock_notifications
        
        notifications = await notification_service.get_user_notifications(
            user_id="user-123",
            unread_only=True,
            notification_type=NotificationType.DEPLOYMENT_SUCCESS
        )
        
        assert len(notifications) == 1
        assert notifications[0].read_at is None
    
    async def test_mark_notification_as_read(self, notification_service):
        """Test marking notification as read."""
        mock_notification = Notification(
            id="notification-123",
            user_id="user-123",
            type=NotificationType.DEPLOYMENT_SUCCESS.value,
            title="Test Notification",
            message="Test message",
            read_at=None,
            status=NotificationStatus.SENT.value
        )
        
        # Mock database query
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalar_one_or_none.return_value = mock_notification
        notification_service.db.commit = AsyncMock()
        notification_service.db.refresh = AsyncMock()
        
        updated_notification = await notification_service.mark_notification_as_read(
            "notification-123", "user-123"
        )
        
        assert updated_notification.read_at is not None
        assert updated_notification.status == NotificationStatus.READ.value
        notification_service.db.commit.assert_called_once()
    
    async def test_mark_notification_as_read_not_found(self, notification_service):
        """Test marking non-existent notification as read."""
        # Mock database query returning None
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(NotFoundError):
            await notification_service.mark_notification_as_read("nonexistent", "user-123")
    
    async def test_mark_all_notifications_as_read(self, notification_service):
        """Test marking all notifications as read."""
        # Mock database update
        mock_result = AsyncMock()
        mock_result.rowcount = 5
        notification_service.db.execute = AsyncMock(return_value=mock_result)
        notification_service.db.commit = AsyncMock()
        
        count = await notification_service.mark_all_notifications_as_read("user-123")
        
        assert count == 5
        notification_service.db.commit.assert_called_once()
    
    async def test_delete_notification(self, notification_service):
        """Test deleting a notification."""
        mock_notification = Notification(
            id="notification-123",
            user_id="user-123",
            type=NotificationType.DEPLOYMENT_SUCCESS.value,
            title="Test Notification",
            message="Test message"
        )
        
        # Mock database operations
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalar_one_or_none.return_value = mock_notification
        notification_service.db.delete = AsyncMock()
        notification_service.db.commit = AsyncMock()
        
        success = await notification_service.delete_notification("notification-123", "user-123")
        
        assert success is True
        notification_service.db.delete.assert_called_once_with(mock_notification)
        notification_service.db.commit.assert_called_once()
    
    async def test_get_user_preferences_existing(self, notification_service, sample_preferences):
        """Test getting existing user preferences."""
        # Mock database query
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalar_one_or_none.return_value = sample_preferences
        
        preferences = await notification_service.get_user_preferences("user-123")
        
        assert preferences.id == "prefs-123"
        assert preferences.enabled is True
    
    async def test_get_user_preferences_create_default(self, notification_service):
        """Test creating default preferences when none exist."""
        # Mock database query returning None
        notification_service.db.execute = AsyncMock()
        notification_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock create_default_preferences
        default_preferences = NotificationPreferences(
            id="new-prefs",
            user_id="user-123",
            enabled=True,
            email_enabled=True,
            in_app_enabled=True
        )
        
        with patch.object(notification_service, 'create_default_preferences', return_value=default_preferences):
            preferences = await notification_service.get_user_preferences("user-123")
        
        assert preferences.id == "new-prefs"
        assert preferences.enabled is True
    
    async def test_create_default_preferences(self, notification_service):
        """Test creating default notification preferences."""
        # Mock database operations
        notification_service.db.add = AsyncMock()
        notification_service.db.commit = AsyncMock()
        notification_service.db.refresh = AsyncMock()
        
        preferences = await notification_service.create_default_preferences("user-123")
        
        assert preferences.enabled is True
        assert preferences.email_enabled is True
        assert preferences.in_app_enabled is True
        notification_service.db.add.assert_called_once()
        notification_service.db.commit.assert_called_once()
    
    async def test_update_user_preferences(self, notification_service, sample_preferences):
        """Test updating user preferences."""
        # Mock get_user_preferences
        with patch.object(notification_service, 'get_user_preferences', return_value=sample_preferences):
            notification_service.db.commit = AsyncMock()
            notification_service.db.refresh = AsyncMock()
            
            updates = {
                "email_enabled": False,
                "slack_enabled": True,
                "quiet_hours_enabled": True
            }
            
            updated_preferences = await notification_service.update_user_preferences("user-123", updates)
        
        assert updated_preferences.email_enabled is False
        assert updated_preferences.slack_enabled is True
        assert updated_preferences.quiet_hours_enabled is True
        notification_service.db.commit.assert_called_once()
    
    async def test_get_notification_stats(self, notification_service):
        """Test getting notification statistics."""
        # Mock database queries
        notification_service.db.execute = AsyncMock()
        
        # Mock query results
        total_result = AsyncMock()
        total_result.scalar.return_value = 100
        
        unread_result = AsyncMock()
        unread_result.scalar.return_value = 15
        
        type_result = AsyncMock()
        type_result.fetchall.return_value = [
            ("deployment_success", 50),
            ("deployment_failed", 10),
            ("user_mentioned", 20)
        ]
        
        status_result = AsyncMock()
        status_result.fetchall.return_value = [
            ("sent", 80),
            ("read", 70),
            ("failed", 5)
        ]
        
        priority_result = AsyncMock()
        priority_result.fetchall.return_value = [
            ("normal", 85),
            ("high", 10),
            ("urgent", 5)
        ]
        
        recent_result = AsyncMock()
        recent_result.scalars.return_value.all.return_value = []
        
        # Set up execute return values
        notification_service.db.execute.side_effect = [
            total_result,
            unread_result,
            type_result,
            status_result,
            priority_result,
            recent_result
        ]
        
        # Mock delivery success rate calculation
        with patch.object(notification_service, '_calculate_delivery_success_rate', return_value=95.5):
            stats = await notification_service.get_notification_stats("user-123")
        
        assert stats["total_notifications"] == 100
        assert stats["unread_notifications"] == 15
        assert stats["notifications_by_type"]["deployment_success"] == 50
        assert stats["notifications_by_status"]["sent"] == 80
        assert stats["notifications_by_priority"]["normal"] == 85
        assert stats["delivery_success_rate"] == 95.5
    
    async def test_determine_channels(self, notification_service, sample_preferences):
        """Test determining delivery channels from preferences."""
        channels = await notification_service._determine_channels(
            NotificationType.DEPLOYMENT_SUCCESS, sample_preferences
        )
        
        # Should include in_app and email based on preferences
        assert NotificationChannel.IN_APP in channels
        assert NotificationChannel.EMAIL in channels
    
    async def test_determine_channels_default(self, notification_service):
        """Test determining channels with no preferences enabled."""
        disabled_preferences = NotificationPreferences(
            user_id="user-123",
            enabled=True,
            email_enabled=False,
            in_app_enabled=False,
            webhook_enabled=False,
            slack_enabled=False
        )
        
        channels = await notification_service._determine_channels(
            NotificationType.DEPLOYMENT_SUCCESS, disabled_preferences
        )
        
        # Should default to in_app when no channels enabled
        assert channels == [NotificationChannel.IN_APP]
    
    def test_is_channel_enabled(self, notification_service, sample_preferences):
        """Test checking if a channel is enabled."""
        # Email should be enabled
        assert notification_service._is_channel_enabled(
            NotificationChannel.EMAIL, "deployment_success", sample_preferences
        ) is True
        
        # Webhook should be enabled (has URL)
        assert notification_service._is_channel_enabled(
            NotificationChannel.WEBHOOK, "deployment_success", sample_preferences
        ) is True
        
        # SMS should be disabled (not configured)
        sample_preferences.sms_enabled = False
        assert notification_service._is_channel_enabled(
            NotificationChannel.SMS, "deployment_success", sample_preferences
        ) is False
    
    async def test_calculate_delivery_success_rate(self, notification_service):
        """Test calculating delivery success rate."""
        # Mock database queries
        notification_service.db.execute = AsyncMock()
        
        total_result = AsyncMock()
        total_result.scalar.return_value = 100
        
        success_result = AsyncMock()
        success_result.scalar.return_value = 95
        
        notification_service.db.execute.side_effect = [total_result, success_result]
        
        success_rate = await notification_service._calculate_delivery_success_rate("user-123")
        
        assert success_rate == 95.0
    
    async def test_calculate_delivery_success_rate_no_data(self, notification_service):
        """Test calculating delivery success rate with no data."""
        # Mock database queries returning 0
        notification_service.db.execute = AsyncMock()
        
        total_result = AsyncMock()
        total_result.scalar.return_value = 0
        
        notification_service.db.execute.return_value = total_result
        
        success_rate = await notification_service._calculate_delivery_success_rate("user-123")
        
        assert success_rate == 100.0  # Perfect score when no data