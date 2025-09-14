"""Tests for presence API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.models.user import User
from app.schemas.activity import UserPresenceStatus


class TestPresenceAPI:
    """Test cases for presence API endpoints."""

    @pytest.mark.asyncio
    async def test_set_user_online_success(self, client, mock_current_user):
        """Test setting user online successfully."""
        with patch('app.api.presence.register_user_online') as mock_register:
            mock_session_data = {
                "user_id": str(mock_current_user.id),
                "session_id": "web_session_123",
                "status": "online",
                "started_at": "2024-01-15T10:00:00Z"
            }
            mock_register.return_value = mock_session_data
            
            session_data = {
                "session_id": "web_session_123",
                "project_id": str(uuid4()),
                "metadata": {"browser": "chrome"}
            }
            
            response = await client.post("/presence/online", json=session_data)
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "User set to online"
            assert "session" in data
            
            # Verify register was called
            mock_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_user_offline_success(self, client, mock_current_user):
        """Test setting user offline successfully."""
        with patch('app.api.presence.register_user_offline') as mock_register:
            mock_register.return_value = AsyncMock()
            
            response = await client.post("/presence/offline")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "User set to offline"
            
            # Verify register was called
            mock_register.assert_called_once_with(str(mock_current_user.id))

    @pytest.mark.asyncio
    async def test_send_heartbeat_success(self, client, mock_current_user):
        """Test sending heartbeat successfully."""
        with patch('app.api.presence.update_user_activity') as mock_update:
            mock_update.return_value = AsyncMock()
            
            with patch('app.api.presence.presence_manager') as mock_manager:
                mock_manager.user_heartbeats = {str(mock_current_user.id): "2024-01-15T10:00:00Z"}
                
                activity_data = {
                    "location": "src/main.py",
                    "activity_type": "coding",
                    "metadata": {"language": "python"}
                }
                
                response = await client.post("/presence/heartbeat", json=activity_data)
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Heartbeat received"
                
                # Verify update was called
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_heartbeat_no_data(self, client, mock_current_user):
        """Test sending heartbeat without activity data."""
        with patch('app.api.presence.update_user_activity') as mock_update:
            mock_update.return_value = AsyncMock()
            
            with patch('app.api.presence.presence_manager') as mock_manager:
                mock_manager.user_heartbeats = {}
                
                response = await client.post("/presence/heartbeat")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                
                # Verify update was called with None values
                mock_update.assert_called_once_with(
                    user_id=str(mock_current_user.id),
                    location=None,
                    activity_type=None,
                    metadata=None
                )

    @pytest.mark.asyncio
    async def test_update_presence_status_success(self, client, mock_current_user):
        """Test updating presence status successfully."""
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_session_data = {
                "user_id": str(mock_current_user.id),
                "status": "away",
                "current_location": "src/test.py"
            }
            mock_manager.update_user_presence = AsyncMock(return_value=mock_session_data)
            
            status_data = {
                "status": "away",
                "current_location": "src/test.py",
                "current_activity": "testing"
            }
            
            response = await client.put("/presence/status", json=status_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Presence status updated"
            assert data["session"] == mock_session_data
            
            # Verify update was called
            mock_manager.update_user_presence.assert_called_once_with(
                str(mock_current_user.id), status_data
            )

    @pytest.mark.asyncio
    async def test_update_presence_status_invalid_status(self, client, mock_current_user):
        """Test updating presence with invalid status."""
        status_data = {"status": "invalid_status"}
        
        response = await client.put("/presence/status", json=status_data)
        
        # Verify validation error
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_presence_status_session_not_found(self, client, mock_current_user):
        """Test updating presence when session not found."""
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_manager.update_user_presence = AsyncMock(return_value=None)
            
            status_data = {"status": "away"}
            
            response = await client.put("/presence/status", json=status_data)
            
            # Verify not found error
            assert response.status_code == 404
            assert "User session not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_my_presence_success(self, client, mock_current_user):
        """Test getting current user's presence."""
        with patch('app.api.presence.get_user_status') as mock_get_status:
            mock_presence_data = {
                "user_id": str(mock_current_user.id),
                "status": "online",
                "current_location": "src/main.py"
            }
            mock_get_status.return_value = mock_presence_data
            
            response = await client.get("/presence/me")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == str(mock_current_user.id)
            assert data["presence"] == mock_presence_data
            
            # Verify get_status was called
            mock_get_status.assert_called_once_with(str(mock_current_user.id))

    @pytest.mark.asyncio
    async def test_get_my_presence_no_session(self, client, mock_current_user):
        """Test getting presence when no active session."""
        with patch('app.api.presence.get_user_status') as mock_get_status:
            mock_get_status.return_value = None
            
            response = await client.get("/presence/me")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == str(mock_current_user.id)
            assert data["status"] == "offline"
            assert "No active session found" in data["message"]

    @pytest.mark.asyncio
    async def test_get_user_presence_success(self, client, mock_current_user):
        """Test getting specific user's presence (own)."""
        user_id = str(mock_current_user.id)
        
        with patch('app.api.presence.get_user_status') as mock_get_status:
            mock_presence_data = {
                "user_id": user_id,
                "status": "active",
                "current_location": "src/feature.py"
            }
            mock_get_status.return_value = mock_presence_data
            
            response = await client.get(f"/presence/user/{user_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert data["presence"] == mock_presence_data

    @pytest.mark.asyncio
    async def test_get_user_presence_access_denied(self, client, mock_current_user):
        """Test getting other user's presence (access denied)."""
        other_user_id = str(uuid4())
        
        response = await client.get(f"/presence/user/{other_user_id}")
        
        # Verify access denied
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_user_presence_admin_access(self, client, mock_admin_user):
        """Test admin can get any user's presence."""
        other_user_id = str(uuid4())
        
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.presence.get_user_status') as mock_get_status:
                mock_presence_data = {
                    "user_id": other_user_id,
                    "status": "online"
                }
                mock_get_status.return_value = mock_presence_data
                
                response = await client.get(f"/presence/user/{other_user_id}")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["user_id"] == other_user_id
                assert data["presence"] == mock_presence_data

    @pytest.mark.asyncio
    async def test_get_project_presence_success(self, client, mock_current_user):
        """Test getting project presence."""
        project_id = str(uuid4())
        
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_project_presence = {
                str(mock_current_user.id): {
                    "user_id": str(mock_current_user.id),
                    "status": "online"
                }
            }
            mock_online_users = [{"user_id": str(mock_current_user.id), "status": "online"}]
            
            mock_manager.get_project_presence = AsyncMock(return_value=mock_project_presence)
            
            with patch('app.api.presence.get_project_online_users') as mock_get_online:
                mock_get_online.return_value = mock_online_users
                
                response = await client.get(f"/presence/project/{project_id}")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["project_id"] == project_id
                assert data["total_users"] == 1
                assert data["online_users"] == 1
                assert data["presence_data"] == mock_project_presence
                assert data["online_users_list"] == mock_online_users

    @pytest.mark.asyncio
    async def test_get_online_users_success(self, client, mock_current_user):
        """Test getting online users."""
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_online_users = [
                {"user_id": str(mock_current_user.id), "status": "online"},
                {"user_id": str(uuid4()), "status": "active"}
            ]
            mock_manager.get_online_users = AsyncMock(return_value=mock_online_users)
            
            response = await client.get("/presence/online")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["project_id"] is None
            assert data["online_count"] == 2
            assert data["online_users"] == mock_online_users

    @pytest.mark.asyncio
    async def test_get_online_users_with_project_filter(self, client, mock_current_user):
        """Test getting online users filtered by project."""
        project_id = str(uuid4())
        
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_online_users = [{"user_id": str(mock_current_user.id), "status": "online"}]
            mock_manager.get_online_users = AsyncMock(return_value=mock_online_users)
            
            response = await client.get("/presence/online", params={"project_id": project_id})
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["project_id"] == project_id
            assert data["online_count"] == 1
            
            # Verify filter was applied
            mock_manager.get_online_users.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_get_user_activity_summary_success(self, client, mock_current_user):
        """Test getting user activity summary."""
        user_id = str(mock_current_user.id)
        
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_summary = {
                "user_id": user_id,
                "status": "active",
                "session_duration_minutes": 45,
                "current_location": "src/main.py"
            }
            mock_manager.get_user_activity_summary = AsyncMock(return_value=mock_summary)
            
            response = await client.get(f"/presence/activity-summary/{user_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert data["hours_analyzed"] == 24  # default
            assert data["summary"] == mock_summary

    @pytest.mark.asyncio
    async def test_get_user_activity_summary_custom_hours(self, client, mock_current_user):
        """Test getting user activity summary with custom hours."""
        user_id = str(mock_current_user.id)
        
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_summary = {"user_id": user_id, "status": "active"}
            mock_manager.get_user_activity_summary = AsyncMock(return_value=mock_summary)
            
            response = await client.get(
                f"/presence/activity-summary/{user_id}",
                params={"hours": 48}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["hours_analyzed"] == 48
            
            # Verify correct hours were passed
            mock_manager.get_user_activity_summary.assert_called_once_with(user_id, 48)

    @pytest.mark.asyncio
    async def test_get_presence_stats_success(self, client, mock_admin_user):
        """Test getting presence statistics (admin only)."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.presence.presence_manager') as mock_manager:
                mock_stats = {
                    "total_active_sessions": 5,
                    "status_distribution": {"online": 3, "away": 2},
                    "is_running": True
                }
                mock_manager.get_stats.return_value = mock_stats
                
                response = await client.get("/presence/stats")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["stats"] == mock_stats

    @pytest.mark.asyncio
    async def test_get_presence_stats_access_denied(self, client, mock_current_user):
        """Test presence stats access denied for non-admin."""
        response = await client.get("/presence/stats")
        
        # Verify access denied
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_configure_presence_settings_success(self, client, mock_admin_user):
        """Test configuring presence settings (admin only)."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.presence.presence_manager') as mock_manager:
                mock_manager.idle_threshold_minutes = 5
                mock_manager.offline_threshold_minutes = 15
                
                settings = {
                    "idle_threshold_minutes": 10,
                    "offline_threshold_minutes": 30
                }
                
                response = await client.post("/presence/configure", json=settings)
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["settings"]["idle_threshold_minutes"] == 10
                assert data["settings"]["offline_threshold_minutes"] == 30

    @pytest.mark.asyncio
    async def test_configure_presence_settings_invalid_values(self, client, mock_admin_user):
        """Test configuring presence settings with invalid values."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            settings = {"idle_threshold_minutes": 100}  # Too high
            
            response = await client.post("/presence/configure", json=settings)
            
            # Verify validation error
            assert response.status_code == 400
            assert "must be between 1 and 60" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_bulk_update_presence_success(self, client, mock_admin_user):
        """Test bulk updating presence (admin only)."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.presence.presence_manager') as mock_manager:
                mock_manager.update_user_presence = AsyncMock(return_value={"status": "updated"})
                
                updates = [
                    {
                        "user_id": str(uuid4()),
                        "status_data": {"status": "away"}
                    },
                    {
                        "user_id": str(uuid4()),
                        "status_data": {"status": "online"}
                    }
                ]
                
                response = await client.post("/presence/bulk-update", json=updates)
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["results"]) == 2
                assert all(result["success"] for result in data["results"])

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence_success(self, client, mock_admin_user):
        """Test cleaning up stale presence (admin only)."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.presence.presence_manager') as mock_manager:
                mock_before_stats = {"total_active_sessions": 10}
                mock_after_stats = {"total_active_sessions": 8}
                
                mock_manager.get_stats.side_effect = [mock_before_stats, mock_after_stats]
                mock_manager._cleanup_offline_users = AsyncMock()
                
                response = await client.delete("/presence/cleanup", params={"force": True})
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["cleaned_count"] == 2
                assert data["before_stats"] == mock_before_stats
                assert data["after_stats"] == mock_after_stats

    @pytest.mark.asyncio
    async def test_presence_health_check_healthy(self, client):
        """Test presence health check when system is healthy."""
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_stats = {
                "is_running": True,
                "total_active_sessions": 5,
                "status_distribution": {"online": 3, "away": 2}
            }
            mock_manager.get_stats.return_value = mock_stats
            
            response = await client.get("/presence/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["stats"] == mock_stats
            assert data["features"]["heartbeat_monitoring"] is True

    @pytest.mark.asyncio
    async def test_presence_health_check_degraded(self, client):
        """Test presence health check when system is degraded."""
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_stats = {
                "is_running": False,
                "total_active_sessions": 0
            }
            mock_manager.get_stats.return_value = mock_stats
            
            response = await client.get("/presence/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert len(data["issues"]) > 0
            assert data["features"]["heartbeat_monitoring"] is False

    @pytest.mark.asyncio
    async def test_presence_health_check_error(self, client):
        """Test presence health check when error occurs."""
        with patch('app.api.presence.presence_manager') as mock_manager:
            mock_manager.get_stats.side_effect = Exception("System error")
            
            response = await client.get("/presence/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "System error" in data["error"]
            assert all(not feature for feature in data["features"].values())


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        name="Admin User",
        hashed_password="hashed_password",
        role="admin",
        status="active"
    )