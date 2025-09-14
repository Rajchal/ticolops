"""
Unit tests for user profile and preferences service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.services.user import UserService
from app.schemas.user import UserUpdate, UserStatusUpdate, UserPreferences, UserStatus
from app.models.user import User, UserRoleEnum, UserStatusEnum
from app.core.security import get_password_hash


class TestUserService:
    """Test user service functionality."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService instance with mocked database."""
        return UserService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Sample database user."""
        user = User(
            email="test@example.com",
            name="Test User",
            hashed_password=get_password_hash("securepassword123"),
            role=UserRoleEnum.STUDENT,
            status=UserStatusEnum.ONLINE
        )
        user.id = "123e4567-e89b-12d3-a456-426614174000"
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.last_activity = datetime.utcnow()
        user.preferences = {
            "email_notifications": True,
            "push_notifications": True,
            "activity_visibility": True,
            "conflict_alerts": True,
            "deployment_notifications": True
        }
        return user

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, user_service, sample_user):
        """Test successful user profile retrieval."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            result = await user_service.get_user_profile(str(sample_user.id))
            
            assert result.id == str(sample_user.id)
            assert result.email == "test@example.com"
            assert result.name == "Test User"
            assert result.role == "student"
            assert result.status == "online"

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service):
        """Test user profile retrieval when user not found."""
        with patch.object(user_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.get_user_profile("non-existent-id")
            
            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_db, sample_user):
        """Test successful user profile update."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            update_data = UserUpdate(
                name="Updated Name",
                avatar="https://example.com/avatar.jpg",
                preferences=UserPreferences(
                    email_notifications=False,
                    push_notifications=True
                )
            )
            
            result = await user_service.update_user_profile(str(sample_user.id), update_data)
            
            assert result.name == "Updated Name"
            assert result.avatar == "https://example.com/avatar.jpg"
            assert sample_user.name == "Updated Name"
            assert sample_user.avatar == "https://example.com/avatar.jpg"
            assert sample_user.preferences["email_notifications"] is False
            assert sample_user.preferences["push_notifications"] is True
            
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_profile_partial(self, user_service, mock_db, sample_user):
        """Test partial user profile update."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Only update name
            update_data = UserUpdate(name="New Name Only")
            
            result = await user_service.update_user_profile(str(sample_user.id), update_data)
            
            assert result.name == "New Name Only"
            assert sample_user.name == "New Name Only"
            # Avatar should remain unchanged (None in this case)
            assert sample_user.avatar is None

    @pytest.mark.asyncio
    async def test_update_user_status_success(self, user_service, mock_db, sample_user):
        """Test successful user status update."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            status_update = UserStatusUpdate(status=UserStatus.AWAY)
            
            result = await user_service.update_user_status(str(sample_user.id), status_update)
            
            assert result.status == "away"
            assert sample_user.status == UserStatusEnum.AWAY
            
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, user_service, mock_db, sample_user):
        """Test successful user preferences update."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            new_preferences = UserPreferences(
                email_notifications=False,
                push_notifications=False,
                activity_visibility=False,
                conflict_alerts=False,
                deployment_notifications=False
            )
            
            result = await user_service.update_user_preferences(str(sample_user.id), new_preferences)
            
            assert sample_user.preferences["email_notifications"] is False
            assert sample_user.preferences["push_notifications"] is False
            assert sample_user.preferences["activity_visibility"] is False
            assert sample_user.preferences["conflict_alerts"] is False
            assert sample_user.preferences["deployment_notifications"] is False
            
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_activity_status(self, user_service, sample_user):
        """Test getting user activity status."""
        # Set last activity to 3 minutes ago
        sample_user.last_activity = datetime.utcnow() - timedelta(minutes=3)
        
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            result = await user_service.get_user_activity_status(str(sample_user.id))
            
            assert result["user_id"] == str(sample_user.id)
            assert result["status"] == "online"
            assert result["minutes_since_activity"] == 3
            assert result["is_active"] is True  # Less than 5 minutes and online

    @pytest.mark.asyncio
    async def test_get_user_activity_status_inactive(self, user_service, sample_user):
        """Test getting user activity status when inactive."""
        # Set last activity to 10 minutes ago
        sample_user.last_activity = datetime.utcnow() - timedelta(minutes=10)
        sample_user.status = UserStatusEnum.AWAY
        
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            result = await user_service.get_user_activity_status(str(sample_user.id))
            
            assert result["user_id"] == str(sample_user.id)
            assert result["status"] == "away"
            assert result["minutes_since_activity"] == 10
            assert result["is_active"] is False  # More than 5 minutes

    @pytest.mark.asyncio
    async def test_update_last_activity(self, user_service, mock_db, sample_user):
        """Test updating user's last activity."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            
            original_activity = sample_user.last_activity
            
            await user_service.update_last_activity(str(sample_user.id))
            
            # Last activity should be updated
            assert sample_user.last_activity > original_activity
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_db, sample_user):
        """Test successful password change."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            
            result = await user_service.change_password(
                str(sample_user.id),
                "securepassword123",  # Current password
                "newsecurepassword456"  # New password
            )
            
            assert result["message"] == "Password updated successfully"
            # Password hash should be updated
            assert sample_user.hashed_password != get_password_hash("securepassword123")
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, sample_user):
        """Test password change with wrong current password."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.change_password(
                    str(sample_user.id),
                    "wrongpassword",  # Wrong current password
                    "newsecurepassword456"
                )
            
            assert exc_info.value.status_code == 400
            assert "Current password is incorrect" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_user_account_success(self, user_service, mock_db, sample_user):
        """Test successful account deletion."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            mock_db.commit = AsyncMock()
            
            result = await user_service.delete_user_account(
                str(sample_user.id),
                "securepassword123"  # Correct password
            )
            
            assert result["message"] == "Account deactivated successfully"
            assert sample_user.status == UserStatusEnum.OFFLINE
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_account_wrong_password(self, user_service, sample_user):
        """Test account deletion with wrong password."""
        with patch.object(user_service, '_get_user_by_id', return_value=sample_user):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.delete_user_account(
                    str(sample_user.id),
                    "wrongpassword"
                )
            
            assert exc_info.value.status_code == 400
            assert "Password is incorrect" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_user_not_found_operations(self, user_service):
        """Test operations when user is not found."""
        with patch.object(user_service, '_get_user_by_id', return_value=None):
            user_id = "non-existent-id"
            
            # Test all operations that should raise 404
            operations = [
                user_service.update_user_profile(user_id, UserUpdate(name="Test")),
                user_service.update_user_status(user_id, UserStatusUpdate(status=UserStatus.AWAY)),
                user_service.update_user_preferences(user_id, UserPreferences()),
                user_service.get_user_activity_status(user_id),
                user_service.update_last_activity(user_id),
                user_service.change_password(user_id, "old", "new"),
                user_service.delete_user_account(user_id, "password")
            ]
            
            for operation in operations:
                with pytest.raises(HTTPException) as exc_info:
                    await operation
                assert exc_info.value.status_code == 404
                assert "User not found" in str(exc_info.value.detail)