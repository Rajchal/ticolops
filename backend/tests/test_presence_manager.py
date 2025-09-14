"""Tests for presence management system."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.presence_manager import PresenceManager
from app.schemas.activity import UserPresenceStatus
from app.models.user import User


@pytest.fixture
def presence_manager():
    """Fresh presence manager for testing."""
    return PresenceManager()


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


class TestPresenceManager:
    """Test cases for PresenceManager."""

    @pytest.mark.asyncio
    async def test_register_user_session_success(self, presence_manager, sample_user):
        """Test successful user session registration."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        project_id = str(uuid4())
        metadata = {"browser": "chrome", "os": "windows"}
        
        # Mock database operations
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                # Register session
                session_data = await presence_manager.register_user_session(
                    user_id=user_id,
                    session_id=session_id,
                    project_id=project_id,
                    initial_status=UserPresenceStatus.ONLINE,
                    metadata=metadata
                )
                
                # Verify session was registered
                assert session_data["user_id"] == user_id
                assert session_data["session_id"] == session_id
                assert session_data["project_id"] == project_id
                assert session_data["status"] == UserPresenceStatus.ONLINE.value
                assert session_data["metadata"] == metadata
                
                # Verify session is stored
                assert user_id in presence_manager.active_sessions
                assert user_id in presence_manager.user_heartbeats
                assert project_id in presence_manager.project_presence
                assert user_id in presence_manager.project_presence[project_id]
                
                # Verify database and broadcast were called
                mock_db_update.assert_called_once()
                mock_broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_user_session(self, presence_manager, sample_user):
        """Test user session unregistration."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        project_id = str(uuid4())
        
        # First register the user
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(
                    user_id=user_id,
                    session_id=session_id,
                    project_id=project_id
                )
                
                # Verify user is registered
                assert user_id in presence_manager.active_sessions
                
                # Now unregister
                await presence_manager.unregister_user_session(user_id)
                
                # Verify user is removed
                assert user_id not in presence_manager.active_sessions
                assert user_id not in presence_manager.user_heartbeats
                assert project_id not in presence_manager.project_presence

    @pytest.mark.asyncio
    async def test_update_user_presence_success(self, presence_manager, sample_user):
        """Test updating user presence."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        # Register user first
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(user_id, session_id)
                
                # Update presence
                updates = {
                    "status": UserPresenceStatus.AWAY.value,
                    "current_location": "src/main.py",
                    "current_activity": "coding"
                }
                
                updated_session = await presence_manager.update_user_presence(user_id, updates)
                
                # Verify updates were applied
                assert updated_session is not None
                assert updated_session["status"] == UserPresenceStatus.AWAY.value
                assert updated_session["current_location"] == "src/main.py"
                assert updated_session["current_activity"] == "coding"
                
                # Verify stored session was updated
                stored_session = presence_manager.active_sessions[user_id]
                assert stored_session["status"] == UserPresenceStatus.AWAY.value
                assert stored_session["current_location"] == "src/main.py"

    @pytest.mark.asyncio
    async def test_update_user_presence_not_found(self, presence_manager):
        """Test updating presence for non-existent user."""
        user_id = str(uuid4())
        updates = {"status": UserPresenceStatus.AWAY.value}
        
        result = await presence_manager.update_user_presence(user_id, updates)
        
        # Should return None for non-existent user
        assert result is None

    @pytest.mark.asyncio
    async def test_heartbeat_updates_activity(self, presence_manager, sample_user):
        """Test heartbeat updates user activity."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        # Register user first
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(user_id, session_id)
                
                # Get initial heartbeat time
                initial_heartbeat = presence_manager.user_heartbeats[user_id]
                
                # Wait a bit and send heartbeat
                await asyncio.sleep(0.1)
                
                activity_data = {
                    "location": "src/test.py",
                    "activity_type": "testing",
                    "metadata": {"test_framework": "pytest"}
                }
                
                await presence_manager.heartbeat(user_id, activity_data)
                
                # Verify heartbeat was updated
                new_heartbeat = presence_manager.user_heartbeats[user_id]
                assert new_heartbeat > initial_heartbeat
                
                # Verify activity data was updated
                session_data = presence_manager.active_sessions[user_id]
                assert session_data["current_location"] == "src/test.py"
                assert session_data["current_activity"] == "testing"
                assert "test_framework" in session_data["metadata"]

    @pytest.mark.asyncio
    async def test_heartbeat_reactivates_away_user(self, presence_manager, sample_user):
        """Test heartbeat reactivates user who was away."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        # Register user and set to away
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(user_id, session_id)
                await presence_manager.update_user_presence(user_id, {"status": UserPresenceStatus.AWAY.value})
                
                # Verify user is away
                assert presence_manager.active_sessions[user_id]["status"] == UserPresenceStatus.AWAY.value
                
                # Send heartbeat
                await presence_manager.heartbeat(user_id)
                
                # Verify user is now active
                assert presence_manager.active_sessions[user_id]["status"] == UserPresenceStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_get_user_presence(self, presence_manager, sample_user):
        """Test getting user presence."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        # Test non-existent user
        presence = await presence_manager.get_user_presence(user_id)
        assert presence is None
        
        # Register user
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(user_id, session_id)
                
                # Get presence
                presence = await presence_manager.get_user_presence(user_id)
                
                assert presence is not None
                assert presence["user_id"] == user_id
                assert presence["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_get_project_presence(self, presence_manager, sample_user):
        """Test getting project presence."""
        project_id = str(uuid4())
        user1_id = str(sample_user.id)
        user2_id = str(uuid4())
        
        # Test empty project
        presence = await presence_manager.get_project_presence(project_id)
        assert presence == {}
        
        # Register users to project
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(user1_id, "session1", project_id)
                await presence_manager.register_user_session(user2_id, "session2", project_id)
                
                # Get project presence
                presence = await presence_manager.get_project_presence(project_id)
                
                assert len(presence) == 2
                assert user1_id in presence
                assert user2_id in presence

    @pytest.mark.asyncio
    async def test_get_online_users(self, presence_manager, sample_user):
        """Test getting online users."""
        project_id = str(uuid4())
        user1_id = str(sample_user.id)
        user2_id = str(uuid4())
        
        # Register users with different statuses
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(
                    user1_id, "session1", project_id, UserPresenceStatus.ONLINE
                )
                await presence_manager.register_user_session(
                    user2_id, "session2", project_id, UserPresenceStatus.OFFLINE
                )
                
                # Get online users for project
                online_users = await presence_manager.get_online_users(project_id)
                
                # Should only return online user
                assert len(online_users) == 1
                assert online_users[0]["user_id"] == user1_id
                
                # Get all online users
                all_online = await presence_manager.get_online_users()
                assert len(all_online) == 1
                assert all_online[0]["user_id"] == user1_id

    @pytest.mark.asyncio
    async def test_get_user_activity_summary(self, presence_manager, sample_user):
        """Test getting user activity summary."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        # Test non-existent user
        summary = await presence_manager.get_user_activity_summary(user_id)
        assert summary["status"] == "offline"
        
        # Register user
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                await presence_manager.register_user_session(user_id, session_id)
                
                # Update with activity
                await presence_manager.update_user_presence(user_id, {
                    "current_location": "src/main.py",
                    "current_activity": "coding"
                })
                
                # Get summary
                summary = await presence_manager.get_user_activity_summary(user_id)
                
                assert summary["user_id"] == user_id
                assert summary["status"] == UserPresenceStatus.ONLINE.value
                assert summary["current_location"] == "src/main.py"
                assert summary["current_activity"] == "coding"
                assert "session_duration_minutes" in summary
                assert "time_since_last_activity_minutes" in summary

    @pytest.mark.asyncio
    async def test_check_user_status_idle_detection(self, presence_manager, sample_user):
        """Test idle detection in status checking."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        # Set short idle threshold for testing
        presence_manager.idle_threshold_minutes = 0.01  # 0.6 seconds
        
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                # Register user
                await presence_manager.register_user_session(user_id, session_id)
                
                # Verify user is online
                assert presence_manager.active_sessions[user_id]["status"] == UserPresenceStatus.ONLINE.value
                
                # Set old heartbeat to simulate idle
                old_time = datetime.utcnow() - timedelta(minutes=1)
                presence_manager.user_heartbeats[user_id] = old_time
                presence_manager.active_sessions[user_id]["last_activity"] = old_time
                
                # Check status
                await presence_manager._check_user_status()
                
                # User should now be away
                assert presence_manager.active_sessions[user_id]["status"] == UserPresenceStatus.AWAY.value

    @pytest.mark.asyncio
    async def test_cleanup_offline_users(self, presence_manager, sample_user):
        """Test cleanup of offline users."""
        user_id = str(sample_user.id)
        session_id = "test_session_123"
        
        with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
            mock_db_update.return_value = AsyncMock()
            
            with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
                mock_broadcast.return_value = AsyncMock()
                
                # Register user and set offline
                await presence_manager.register_user_session(user_id, session_id)
                await presence_manager.update_user_presence(user_id, {"status": UserPresenceStatus.OFFLINE.value})
                
                # Set old activity time to simulate stale session
                old_time = datetime.utcnow() - timedelta(hours=2)
                presence_manager.active_sessions[user_id]["last_activity"] = old_time
                
                # Verify user exists
                assert user_id in presence_manager.active_sessions
                
                # Run cleanup
                await presence_manager._cleanup_offline_users()
                
                # User should be removed
                assert user_id not in presence_manager.active_sessions

    def test_register_status_callback(self, presence_manager):
        """Test registering status change callback."""
        callback_id = "test_callback"
        callback_func = MagicMock()
        
        presence_manager.register_status_callback(callback_id, callback_func)
        
        assert callback_id in presence_manager.status_callbacks
        assert presence_manager.status_callbacks[callback_id] == callback_func

    def test_unregister_status_callback(self, presence_manager):
        """Test unregistering status change callback."""
        callback_id = "test_callback"
        callback_func = MagicMock()
        
        # Register then unregister
        presence_manager.register_status_callback(callback_id, callback_func)
        assert callback_id in presence_manager.status_callbacks
        
        presence_manager.unregister_status_callback(callback_id)
        assert callback_id not in presence_manager.status_callbacks

    def test_get_stats(self, presence_manager):
        """Test getting presence manager statistics."""
        # Add some mock sessions
        presence_manager.active_sessions = {
            "user1": {
                "status": UserPresenceStatus.ONLINE.value,
                "project_id": "proj1",
                "started_at": datetime.utcnow() - timedelta(minutes=30)
            },
            "user2": {
                "status": UserPresenceStatus.AWAY.value,
                "project_id": "proj1",
                "started_at": datetime.utcnow() - timedelta(minutes=60)
            },
            "user3": {
                "status": UserPresenceStatus.ONLINE.value,
                "project_id": "proj2",
                "started_at": datetime.utcnow() - timedelta(minutes=15)
            }
        }
        
        stats = presence_manager.get_stats()
        
        # Verify statistics
        assert stats["total_active_sessions"] == 3
        assert stats["status_distribution"][UserPresenceStatus.ONLINE.value] == 2
        assert stats["status_distribution"][UserPresenceStatus.AWAY.value] == 1
        assert stats["project_distribution"]["proj1"] == 2
        assert stats["project_distribution"]["proj2"] == 1
        assert "average_session_duration_minutes" in stats
        assert "idle_threshold_minutes" in stats
        assert "offline_threshold_minutes" in stats

    @pytest.mark.asyncio
    async def test_start_stop_presence_manager(self, presence_manager):
        """Test starting and stopping presence manager."""
        # Initially not running
        assert not presence_manager._is_running
        
        # Start
        await presence_manager.start()
        assert presence_manager._is_running
        assert presence_manager._heartbeat_task is not None
        assert presence_manager._cleanup_task is not None
        
        # Stop
        await presence_manager.stop()
        assert not presence_manager._is_running


@pytest.mark.asyncio
async def test_presence_manager_integration_flow(sample_user):
    """Integration test for complete presence management flow."""
    presence_manager = PresenceManager()
    user_id = str(sample_user.id)
    session_id = "integration_test_session"
    project_id = str(uuid4())
    
    with patch.object(presence_manager, '_update_database_presence') as mock_db_update:
        mock_db_update.return_value = AsyncMock()
        
        with patch.object(presence_manager, '_broadcast_presence_change') as mock_broadcast:
            mock_broadcast.return_value = AsyncMock()
            
            # 1. Register user session
            session_data = await presence_manager.register_user_session(
                user_id=user_id,
                session_id=session_id,
                project_id=project_id,
                initial_status=UserPresenceStatus.ONLINE,
                metadata={"test": "integration"}
            )
            
            assert session_data["user_id"] == user_id
            assert user_id in presence_manager.active_sessions
            
            # 2. Send heartbeat with activity
            await presence_manager.heartbeat(user_id, {
                "location": "src/integration.py",
                "activity_type": "coding"
            })
            
            # 3. Update presence status
            updated_session = await presence_manager.update_user_presence(user_id, {
                "status": UserPresenceStatus.ACTIVE.value,
                "current_location": "src/updated.py"
            })
            
            assert updated_session["status"] == UserPresenceStatus.ACTIVE.value
            assert updated_session["current_location"] == "src/updated.py"
            
            # 4. Get user presence
            presence = await presence_manager.get_user_presence(user_id)
            assert presence is not None
            assert presence["user_id"] == user_id
            
            # 5. Get project presence
            project_presence = await presence_manager.get_project_presence(project_id)
            assert user_id in project_presence
            
            # 6. Get online users
            online_users = await presence_manager.get_online_users(project_id)
            assert len(online_users) == 1
            assert online_users[0]["user_id"] == user_id
            
            # 7. Get activity summary
            summary = await presence_manager.get_user_activity_summary(user_id)
            assert summary["user_id"] == user_id
            assert summary["status"] == UserPresenceStatus.ACTIVE.value
            
            # 8. Unregister session
            await presence_manager.unregister_user_session(user_id)
            assert user_id not in presence_manager.active_sessions