"""Tests for WebSocket functionality."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.core.websocket import ConnectionManager
from app.services.websocket_pubsub import WebSocketPubSubService
from app.models.user import User


@pytest.fixture
def connection_manager():
    """Fresh connection manager for testing."""
    return ConnectionManager()


@pytest.fixture
def pubsub_service():
    """WebSocket pub/sub service for testing."""
    return WebSocketPubSubService()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


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


class TestConnectionManager:
    """Test cases for ConnectionManager."""

    @pytest.mark.asyncio
    async def test_connect_user_success(self, connection_manager, mock_websocket, sample_user):
        """Test successful user connection."""
        user_id = str(sample_user.id)
        project_id = str(uuid4())
        
        # Mock database operations
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService') as mock_presence_service:
                mock_presence_service.return_value.update_presence = AsyncMock()
                
                # Connect user
                connection_id = await connection_manager.connect(
                    websocket=mock_websocket,
                    user_id=user_id,
                    project_id=project_id,
                    session_metadata={"test": "data"}
                )
                
                # Verify connection was established
                assert connection_id is not None
                assert connection_id in connection_manager.connection_metadata
                assert user_id in connection_manager.user_connections
                assert project_id in connection_manager.project_subscriptions
                
                # Verify WebSocket was accepted
                mock_websocket.accept.assert_called_once()
                
                # Verify connection metadata
                metadata = connection_manager.connection_metadata[connection_id]
                assert metadata["user_id"] == user_id
                assert metadata["project_id"] == project_id
                assert metadata["websocket"] == mock_websocket

    @pytest.mark.asyncio
    async def test_disconnect_user(self, connection_manager, mock_websocket, sample_user):
        """Test user disconnection."""
        user_id = str(sample_user.id)
        project_id = str(uuid4())
        
        # First connect the user
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                connection_id = await connection_manager.connect(
                    websocket=mock_websocket,
                    user_id=user_id,
                    project_id=project_id
                )
        
        # Now disconnect
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                await connection_manager.disconnect(connection_id)
                
                # Verify connection was removed
                assert connection_id not in connection_manager.connection_metadata
                assert user_id not in connection_manager.user_connections
                assert project_id not in connection_manager.project_subscriptions

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self, connection_manager, mock_websocket, sample_user):
        """Test sending personal message to user."""
        user_id = str(sample_user.id)
        
        # Connect user first
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                await connection_manager.connect(
                    websocket=mock_websocket,
                    user_id=user_id
                )
        
        # Send message
        message = {"type": "test", "data": {"content": "Hello"}}
        result = await connection_manager.send_personal_message(user_id, message)
        
        # Verify message was sent
        assert result is True
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data == message

    @pytest.mark.asyncio
    async def test_send_personal_message_user_not_connected(self, connection_manager):
        """Test sending message to non-connected user."""
        user_id = str(uuid4())
        message = {"type": "test", "data": {"content": "Hello"}}
        
        result = await connection_manager.send_personal_message(user_id, message)
        
        # Should return False for non-connected user
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_to_project_success(self, connection_manager, sample_user):
        """Test broadcasting message to project."""
        project_id = str(uuid4())
        user1_id = str(sample_user.id)
        user2_id = str(uuid4())
        
        # Create mock websockets
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        
        # Connect multiple users to project
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                await connection_manager.connect(websocket1, user1_id, project_id)
                await connection_manager.connect(websocket2, user2_id, project_id)
        
        # Broadcast message
        message = {"type": "broadcast", "data": {"content": "Hello everyone"}}
        sent_count = await connection_manager.broadcast_to_project(project_id, message)
        
        # Verify message was sent to both users
        assert sent_count == 2
        websocket1.send_text.assert_called_once()
        websocket2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_project_exclude_user(self, connection_manager, sample_user):
        """Test broadcasting message to project excluding specific user."""
        project_id = str(uuid4())
        user1_id = str(sample_user.id)
        user2_id = str(uuid4())
        
        # Create mock websockets
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        
        # Connect multiple users to project
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                await connection_manager.connect(websocket1, user1_id, project_id)
                await connection_manager.connect(websocket2, user2_id, project_id)
        
        # Broadcast message excluding user1
        message = {"type": "broadcast", "data": {"content": "Hello"}}
        sent_count = await connection_manager.broadcast_to_project(project_id, message, exclude_user=user1_id)
        
        # Verify message was sent only to user2
        assert sent_count == 1
        websocket1.send_text.assert_not_called()
        websocket2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_users(self, connection_manager, sample_user):
        """Test getting users connected to a project."""
        project_id = str(uuid4())
        user_id = str(sample_user.id)
        
        # Connect user to project
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                await connection_manager.connect(
                    AsyncMock(), user_id, project_id
                )
        
        # Get project users
        users = await connection_manager.get_project_users(project_id)
        
        # Verify user is in the list
        assert len(users) == 1
        assert users[0]["user_id"] == user_id
        assert users[0]["connection_count"] == 1

    @pytest.mark.asyncio
    async def test_update_user_activity(self, connection_manager, sample_user):
        """Test updating user activity."""
        project_id = str(uuid4())
        user_id = str(sample_user.id)
        other_user_id = str(uuid4())
        
        # Create mock websockets
        websocket1 = AsyncMock()
        websocket2 = AsyncMock()
        
        # Connect users to project
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                await connection_manager.connect(websocket1, user_id, project_id)
                await connection_manager.connect(websocket2, other_user_id, project_id)
        
        # Update user activity
        activity_data = {
            "activity_type": "coding",
            "location": "src/main.py",
            "description": "Working on main function"
        }
        
        await connection_manager.update_user_activity(user_id, activity_data)
        
        # Verify activity update was broadcast to other user (excluding the actor)
        websocket1.send_text.assert_not_called()  # Excluded user
        websocket2.send_text.assert_called_once()  # Other user should receive update

    @pytest.mark.asyncio
    async def test_handle_ping(self, connection_manager, mock_websocket, sample_user):
        """Test handling ping message."""
        user_id = str(sample_user.id)
        
        # Connect user first
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                connection_id = await connection_manager.connect(mock_websocket, user_id)
        
        # Handle ping
        result = await connection_manager.handle_ping(connection_id)
        
        # Verify ping was handled successfully
        assert result is True
        mock_websocket.send_text.assert_called_once()
        
        # Verify pong message was sent
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "pong"
        assert "timestamp" in sent_data

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self, connection_manager, mock_websocket, sample_user):
        """Test cleaning up stale connections."""
        user_id = str(sample_user.id)
        
        # Connect user
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                connection_id = await connection_manager.connect(mock_websocket, user_id)
        
        # Manually set last activity to old time to simulate stale connection
        old_time = datetime.utcnow() - timedelta(minutes=60)
        connection_manager.connection_metadata[connection_id]["last_activity"] = old_time
        
        # Cleanup stale connections
        with patch('app.core.websocket.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with patch('app.services.activity.PresenceService'):
                cleaned_count = await connection_manager.cleanup_stale_connections(timeout_minutes=30)
        
        # Verify stale connection was cleaned up
        assert cleaned_count == 1
        assert connection_id not in connection_manager.connection_metadata

    def test_get_connection_stats(self, connection_manager):
        """Test getting connection statistics."""
        # Add some mock connections
        connection_manager.connection_metadata = {
            "conn1": {"user_id": "user1", "project_id": "proj1"},
            "conn2": {"user_id": "user2", "project_id": "proj1"},
            "conn3": {"user_id": "user1", "project_id": "proj2"}
        }
        connection_manager.user_connections = {
            "user1": {"conn1", "conn3"},
            "user2": {"conn2"}
        }
        connection_manager.project_subscriptions = {
            "proj1": {"conn1", "conn2"},
            "proj2": {"conn3"}
        }
        
        stats = connection_manager.get_connection_stats()
        
        # Verify statistics
        assert stats["total_connections"] == 3
        assert stats["unique_users"] == 2
        assert stats["active_projects"] == 2
        assert stats["project_stats"]["proj1"] == 2
        assert stats["project_stats"]["proj2"] == 1


class TestWebSocketPubSubService:
    """Test cases for WebSocketPubSubService."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, pubsub_service):
        """Test successful pub/sub service initialization."""
        with patch('app.services.websocket_pubsub.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_pubsub = AsyncMock()
            mock_redis.pubsub.return_value = mock_pubsub
            mock_get_redis.return_value = mock_redis
            
            await pubsub_service.initialize()
            
            assert pubsub_service.redis == mock_redis
            assert pubsub_service.pubsub == mock_pubsub

    @pytest.mark.asyncio
    async def test_subscribe_to_channels(self, pubsub_service):
        """Test subscribing to Redis channels."""
        mock_pubsub = AsyncMock()
        pubsub_service.pubsub = mock_pubsub
        
        await pubsub_service.subscribe_to_channels()
        
        # Verify subscription to expected channels
        mock_pubsub.subscribe.assert_called_once()
        args = mock_pubsub.subscribe.call_args[0]
        expected_channels = [
            "websocket:broadcast",
            "websocket:project_broadcast",
            "websocket:user_message",
            "websocket:presence_update",
            "websocket:activity_update"
        ]
        assert all(channel in args for channel in expected_channels)

    @pytest.mark.asyncio
    async def test_publish_broadcast_message(self, pubsub_service):
        """Test publishing broadcast message."""
        mock_redis = AsyncMock()
        pubsub_service.redis = mock_redis
        
        message = {"type": "test", "data": "broadcast"}
        await pubsub_service.publish_broadcast_message(message)
        
        # Verify message was published
        mock_redis.publish.assert_called_once()
        channel, payload = mock_redis.publish.call_args[0]
        assert channel == "websocket:broadcast"
        
        # Verify payload structure
        payload_data = json.loads(payload)
        assert payload_data["type"] == "broadcast_all"
        assert payload_data["message"] == message

    @pytest.mark.asyncio
    async def test_publish_project_message(self, pubsub_service):
        """Test publishing project-specific message."""
        mock_redis = AsyncMock()
        pubsub_service.redis = mock_redis
        
        project_id = str(uuid4())
        message = {"type": "test", "data": "project"}
        exclude_user = str(uuid4())
        
        await pubsub_service.publish_project_message(project_id, message, exclude_user)
        
        # Verify message was published
        mock_redis.publish.assert_called_once()
        channel, payload = mock_redis.publish.call_args[0]
        assert channel == "websocket:project_broadcast"
        
        # Verify payload structure
        payload_data = json.loads(payload)
        assert payload_data["type"] == "project_broadcast"
        assert payload_data["project_id"] == project_id
        assert payload_data["message"] == message
        assert payload_data["exclude_user"] == exclude_user

    @pytest.mark.asyncio
    async def test_publish_user_message(self, pubsub_service):
        """Test publishing user-specific message."""
        mock_redis = AsyncMock()
        pubsub_service.redis = mock_redis
        
        user_id = str(uuid4())
        message = {"type": "test", "data": "user"}
        
        await pubsub_service.publish_user_message(user_id, message)
        
        # Verify message was published
        mock_redis.publish.assert_called_once()
        channel, payload = mock_redis.publish.call_args[0]
        assert channel == "websocket:user_message"
        
        # Verify payload structure
        payload_data = json.loads(payload)
        assert payload_data["type"] == "user_message"
        assert payload_data["user_id"] == user_id
        assert payload_data["message"] == message

    @pytest.mark.asyncio
    async def test_handle_broadcast_message(self, pubsub_service):
        """Test handling broadcast message from Redis."""
        with patch('app.services.websocket_pubsub.connection_manager') as mock_manager:
            mock_manager.broadcast_to_all = AsyncMock()
            
            data = {
                "type": "broadcast_all",
                "message": {"type": "test", "data": "broadcast"},
                "instance_id": "other_instance"
            }
            
            await pubsub_service._handle_broadcast_message(data)
            
            # Verify broadcast was called
            mock_manager.broadcast_to_all.assert_called_once_with(data["message"])

    @pytest.mark.asyncio
    async def test_handle_project_broadcast_message(self, pubsub_service):
        """Test handling project broadcast message from Redis."""
        with patch('app.services.websocket_pubsub.connection_manager') as mock_manager:
            mock_manager.broadcast_to_project = AsyncMock()
            
            project_id = str(uuid4())
            exclude_user = str(uuid4())
            data = {
                "type": "project_broadcast",
                "project_id": project_id,
                "message": {"type": "test", "data": "project"},
                "exclude_user": exclude_user,
                "instance_id": "other_instance"
            }
            
            await pubsub_service._handle_project_broadcast_message(data)
            
            # Verify project broadcast was called
            mock_manager.broadcast_to_project.assert_called_once_with(
                project_id, data["message"], exclude_user
            )

    @pytest.mark.asyncio
    async def test_handle_user_message(self, pubsub_service):
        """Test handling user message from Redis."""
        with patch('app.services.websocket_pubsub.connection_manager') as mock_manager:
            mock_manager.send_personal_message = AsyncMock()
            
            user_id = str(uuid4())
            data = {
                "type": "user_message",
                "user_id": user_id,
                "message": {"type": "test", "data": "user"},
                "instance_id": "other_instance"
            }
            
            await pubsub_service._handle_user_message(data)
            
            # Verify personal message was sent
            mock_manager.send_personal_message.assert_called_once_with(
                user_id, data["message"]
            )

    def test_get_instance_id(self, pubsub_service):
        """Test getting unique instance ID."""
        instance_id = pubsub_service._get_instance_id()
        
        # Verify instance ID format
        assert isinstance(instance_id, str)
        assert ":" in instance_id  # Should contain hostname:pid format

    @pytest.mark.asyncio
    async def test_get_stats_success(self, pubsub_service):
        """Test getting pub/sub service statistics."""
        mock_redis = AsyncMock()
        mock_redis.info.return_value = {
            "connected_clients": 5,
            "used_memory_human": "1.2M"
        }
        pubsub_service.redis = mock_redis
        pubsub_service.is_listening = True
        
        stats = await pubsub_service.get_stats()
        
        # Verify statistics
        assert stats["is_listening"] is True
        assert "instance_id" in stats
        assert stats["redis_connected"] is True
        assert stats["redis_clients"] == 5
        assert stats["redis_memory_usage"] == "1.2M"

    @pytest.mark.asyncio
    async def test_get_stats_error(self, pubsub_service):
        """Test getting statistics with Redis error."""
        mock_redis = AsyncMock()
        mock_redis.info.side_effect = Exception("Redis connection failed")
        pubsub_service.redis = mock_redis
        pubsub_service.is_listening = False
        
        stats = await pubsub_service.get_stats()
        
        # Verify error handling
        assert stats["is_listening"] is False
        assert "error" in stats
        assert "Redis connection failed" in stats["error"]


@pytest.mark.asyncio
async def test_websocket_integration_flow(connection_manager, sample_user):
    """Integration test for complete WebSocket flow."""
    user_id = str(sample_user.id)
    project_id = str(uuid4())
    websocket = AsyncMock()
    
    # Mock all external dependencies
    with patch('app.core.websocket.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__.return_value = [mock_db]
        
        with patch('app.services.activity.PresenceService') as mock_presence_service:
            mock_presence_service.return_value.update_presence = AsyncMock()
            
            # 1. Connect user
            connection_id = await connection_manager.connect(websocket, user_id, project_id)
            assert connection_id is not None
            
            # 2. Send personal message
            message = {"type": "welcome", "data": {"message": "Hello!"}}
            sent = await connection_manager.send_personal_message(user_id, message)
            assert sent is True
            
            # 3. Update activity
            activity_data = {"activity_type": "coding", "location": "src/test.py"}
            await connection_manager.update_user_activity(user_id, activity_data)
            
            # 4. Handle ping
            ping_result = await connection_manager.handle_ping(connection_id)
            assert ping_result is True
            
            # 5. Get project users
            users = await connection_manager.get_project_users(project_id)
            assert len(users) == 1
            assert users[0]["user_id"] == user_id
            
            # 6. Disconnect user
            await connection_manager.disconnect(connection_id)
            assert connection_id not in connection_manager.connection_metadata