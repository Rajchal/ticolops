"""Tests for WebSocket API endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.models.user import User


class TestWebSocketAPI:
    """Test cases for WebSocket API endpoints."""

    @pytest.mark.asyncio
    async def test_get_websocket_stats_success(self, client, mock_admin_user):
        """Test getting WebSocket statistics (admin only)."""
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_stats = {
                "total_connections": 10,
                "unique_users": 8,
                "active_projects": 3,
                "project_stats": {"proj1": 5, "proj2": 3, "proj3": 2},
                "timestamp": "2024-01-15T10:00:00Z"
            }
            mock_manager.get_connection_stats.return_value = mock_stats
            
            # Mock admin user
            with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
                response = await client.get("/ws/stats")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["total_connections"] == 10
            assert data["unique_users"] == 8
            assert data["active_projects"] == 3

    @pytest.mark.asyncio
    async def test_get_websocket_stats_access_denied(self, client, mock_current_user):
        """Test WebSocket stats access denied for non-admin."""
        response = await client.get("/ws/stats")
        
        # Verify access denied
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_broadcast_message_success(self, client, mock_admin_user):
        """Test broadcasting message via WebSocket (admin only)."""
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_manager.broadcast_to_all = AsyncMock(return_value=5)
            
            message_data = {
                "message": "System maintenance in 10 minutes"
            }
            
            # Mock admin user
            with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
                response = await client.post("/ws/broadcast", json=message_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["recipients"] == 5
            
            # Verify broadcast was called
            mock_manager.broadcast_to_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_to_project(self, client, mock_admin_user):
        """Test broadcasting message to specific project."""
        project_id = str(uuid4())
        
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_manager.broadcast_to_project = AsyncMock(return_value=3)
            
            message_data = {
                "message": "Project update available"
            }
            
            # Mock admin user
            with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
                response = await client.post(
                    "/ws/broadcast", 
                    json=message_data,
                    params={"project_id": project_id}
                )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["recipients"] == 3
            
            # Verify project broadcast was called
            mock_manager.broadcast_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_access_denied(self, client, mock_current_user):
        """Test broadcast message access denied for non-admin."""
        message_data = {"message": "Test message"}
        
        response = await client.post("/ws/broadcast", json=message_data)
        
        # Verify access denied
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cleanup_connections_success(self, client, mock_admin_user):
        """Test cleaning up stale WebSocket connections (admin only)."""
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_manager.cleanup_stale_connections = AsyncMock(return_value=3)
            
            # Mock admin user
            with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
                response = await client.post(
                    "/ws/cleanup",
                    params={"timeout_minutes": 60}
                )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["cleaned_count"] == 3
            assert data["timeout_minutes"] == 60
            
            # Verify cleanup was called with correct timeout
            mock_manager.cleanup_stale_connections.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_cleanup_connections_access_denied(self, client, mock_current_user):
        """Test cleanup connections access denied for non-admin."""
        response = await client.post("/ws/cleanup")
        
        # Verify access denied
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cleanup_connections_invalid_timeout(self, client, mock_admin_user):
        """Test cleanup connections with invalid timeout parameter."""
        # Mock admin user
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            response = await client.post(
                "/ws/cleanup",
                params={"timeout_minutes": 2000}  # Exceeds maximum
            )
        
        # Verify validation error
        assert response.status_code == 422


class TestWebSocketMessageHandling:
    """Test cases for WebSocket message handling functions."""

    @pytest.mark.asyncio
    async def test_handle_activity_update(self):
        """Test handling activity update message."""
        from app.api.websocket import handle_activity_update
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {
            "activity_type": "coding",
            "title": "Working on feature",
            "location": "src/feature.py",
            "create_record": True,
            "metadata": {"language": "python"}
        }
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.ActivityService') as mock_service:
            mock_service.return_value.create_activity = AsyncMock()
            
            with patch('app.api.websocket.connection_manager') as mock_manager:
                mock_manager.update_user_activity = AsyncMock()
                
                await handle_activity_update(user_id, project_id, data, mock_db)
                
                # Verify activity was created
                mock_service.return_value.create_activity.assert_called_once()
                
                # Verify activity update was broadcast
                mock_manager.update_user_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_presence_update(self):
        """Test handling presence update message."""
        from app.api.websocket import handle_presence_update
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {
            "status": "online",
            "current_location": "src/main.py",
            "current_activity": "coding",
            "metadata": {"browser": "chrome"}
        }
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.PresenceService') as mock_service:
            with patch('app.api.websocket.connection_manager') as mock_manager:
                mock_manager.broadcast_to_project = AsyncMock()
                
                await handle_presence_update(user_id, project_id, data, mock_db)
                
                # Verify presence update was broadcast
                mock_manager.broadcast_to_project.assert_called_once()
                args = mock_manager.broadcast_to_project.call_args[0]
                assert args[0] == project_id  # project_id
                assert args[1]["type"] == "presence_update"  # message type
                assert mock_manager.broadcast_to_project.call_args[1]["exclude_user"] == user_id

    @pytest.mark.asyncio
    async def test_handle_typing_event(self):
        """Test handling typing start/stop events."""
        from app.api.websocket import handle_typing_event
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {"file_path": "src/main.py"}
        
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_manager.broadcast_to_project = AsyncMock()
            
            # Test typing start
            await handle_typing_event(user_id, project_id, data, True)
            
            # Verify typing indicator was broadcast
            mock_manager.broadcast_to_project.assert_called_once()
            args = mock_manager.broadcast_to_project.call_args[0]
            assert args[0] == project_id
            assert args[1]["type"] == "typing_indicator"
            assert args[1]["data"]["is_typing"] is True
            assert args[1]["data"]["file_path"] == "src/main.py"

    @pytest.mark.asyncio
    async def test_handle_cursor_update(self):
        """Test handling cursor position updates."""
        from app.api.websocket import handle_cursor_update
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {
            "file_path": "src/main.py",
            "position": {"line": 10, "column": 5},
            "selection": {"start": {"line": 10, "column": 5}, "end": {"line": 10, "column": 15}}
        }
        
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_manager.broadcast_to_project = AsyncMock()
            
            await handle_cursor_update(user_id, project_id, data)
            
            # Verify cursor update was broadcast
            mock_manager.broadcast_to_project.assert_called_once()
            args = mock_manager.broadcast_to_project.call_args[0]
            assert args[0] == project_id
            assert args[1]["type"] == "cursor_update"
            assert args[1]["data"]["file_path"] == "src/main.py"
            assert args[1]["data"]["position"] == {"line": 10, "column": 5}

    @pytest.mark.asyncio
    async def test_handle_file_event(self):
        """Test handling file open/close events."""
        from app.api.websocket import handle_file_event
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {"file_path": "src/main.py"}
        
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_manager.broadcast_to_project = AsyncMock()
            
            await handle_file_event(user_id, project_id, data, "opened")
            
            # Verify file event was broadcast
            mock_manager.broadcast_to_project.assert_called_once()
            args = mock_manager.broadcast_to_project.call_args[0]
            assert args[0] == project_id
            assert args[1]["type"] == "file_event"
            assert args[1]["data"]["event_type"] == "opened"
            assert args[1]["data"]["file_path"] == "src/main.py"

    @pytest.mark.asyncio
    async def test_handle_join_project_success(self):
        """Test handling user joining a project."""
        from app.api.websocket import handle_join_project
        
        connection_id = str(uuid4())
        user_id = str(uuid4())
        new_project_id = str(uuid4())
        data = {"project_id": new_project_id}
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.ProjectService') as mock_project_service:
            mock_project_service.return_value._user_has_project_access = AsyncMock(return_value=True)
            
            with patch('app.api.websocket.connection_manager') as mock_manager:
                # Mock connection metadata
                mock_manager.connection_metadata = {
                    connection_id: {"websocket": AsyncMock(), "project_id": None}
                }
                mock_manager.project_subscriptions = {}
                mock_manager.broadcast_to_project = AsyncMock()
                
                await handle_join_project(connection_id, user_id, data, mock_db)
                
                # Verify project was joined
                assert mock_manager.connection_metadata[connection_id]["project_id"] == new_project_id
                assert new_project_id in mock_manager.project_subscriptions
                assert connection_id in mock_manager.project_subscriptions[new_project_id]
                
                # Verify other users were notified
                mock_manager.broadcast_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_join_project_access_denied(self):
        """Test handling user joining project with access denied."""
        from app.api.websocket import handle_join_project, send_error_message_to_connection
        
        connection_id = str(uuid4())
        user_id = str(uuid4())
        new_project_id = str(uuid4())
        data = {"project_id": new_project_id}
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.ProjectService') as mock_project_service:
            mock_project_service.return_value._user_has_project_access = AsyncMock(return_value=False)
            
            with patch('app.api.websocket.send_error_message_to_connection') as mock_send_error:
                mock_send_error.return_value = AsyncMock()
                
                with patch('app.api.websocket.connection_manager') as mock_manager:
                    mock_manager.connection_metadata = {
                        connection_id: {"websocket": AsyncMock()}
                    }
                    
                    await handle_join_project(connection_id, user_id, data, mock_db)
                    
                    # Verify error message was sent
                    mock_send_error.assert_called_once_with(connection_id, "Project access denied")

    @pytest.mark.asyncio
    async def test_handle_leave_project(self):
        """Test handling user leaving a project."""
        from app.api.websocket import handle_leave_project
        
        connection_id = str(uuid4())
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {"project_id": project_id}
        
        with patch('app.api.websocket.connection_manager') as mock_manager:
            # Mock initial state
            mock_manager.project_subscriptions = {project_id: {connection_id}}
            mock_manager.connection_metadata = {
                connection_id: {"project_id": project_id}
            }
            mock_manager.broadcast_to_project = AsyncMock()
            
            await handle_leave_project(connection_id, user_id, data)
            
            # Verify user was removed from project
            assert connection_id not in mock_manager.project_subscriptions[project_id]
            assert mock_manager.connection_metadata[connection_id]["project_id"] is None
            
            # Verify other users were notified
            mock_manager.broadcast_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_project_status_request(self):
        """Test handling project status request."""
        from app.api.websocket import handle_project_status_request
        
        connection_id = str(uuid4())
        user_id = str(uuid4())
        project_id = str(uuid4())
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.connection_manager') as mock_manager:
            mock_users = [
                {"user_id": user_id, "connected_at": "2024-01-15T10:00:00Z", "connection_count": 1}
            ]
            mock_stats = {"total_connections": 1, "unique_users": 1}
            
            mock_manager.get_project_users = AsyncMock(return_value=mock_users)
            mock_manager.get_connection_stats.return_value = mock_stats
            mock_manager.connection_metadata = {
                connection_id: {"websocket": AsyncMock()}
            }
            
            await handle_project_status_request(connection_id, user_id, project_id, mock_db)
            
            # Verify status was sent
            websocket = mock_manager.connection_metadata[connection_id]["websocket"]
            websocket.send_text.assert_called_once()
            
            # Verify message content
            sent_data = json.loads(websocket.send_text.call_args[0][0])
            assert sent_data["type"] == "project_status"
            assert sent_data["data"]["project_id"] == project_id
            assert sent_data["data"]["connected_users"] == mock_users

    @pytest.mark.asyncio
    async def test_handle_broadcast_message_success(self):
        """Test handling broadcast message request."""
        from app.api.websocket import handle_broadcast_message
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {
            "message": "Important announcement",
            "message_type": "warning"
        }
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.ProjectService') as mock_project_service:
            mock_project_service.return_value._user_can_edit_project = AsyncMock(return_value=True)
            
            with patch('app.api.websocket.connection_manager') as mock_manager:
                mock_manager.broadcast_to_project = AsyncMock()
                
                await handle_broadcast_message(user_id, project_id, data, mock_db)
                
                # Verify broadcast was sent
                mock_manager.broadcast_to_project.assert_called_once()
                args = mock_manager.broadcast_to_project.call_args[0]
                assert args[0] == project_id
                assert args[1]["type"] == "broadcast"
                assert args[1]["data"]["message"] == "Important announcement"
                assert args[1]["data"]["message_type"] == "warning"

    @pytest.mark.asyncio
    async def test_handle_broadcast_message_unauthorized(self):
        """Test handling broadcast message request without permission."""
        from app.api.websocket import handle_broadcast_message
        
        user_id = str(uuid4())
        project_id = str(uuid4())
        data = {"message": "Unauthorized message"}
        
        mock_db = AsyncMock()
        
        with patch('app.api.websocket.ProjectService') as mock_project_service:
            mock_project_service.return_value._user_can_edit_project = AsyncMock(return_value=False)
            
            with patch('app.api.websocket.connection_manager') as mock_manager:
                mock_manager.broadcast_to_project = AsyncMock()
                
                await handle_broadcast_message(user_id, project_id, data, mock_db)
                
                # Verify broadcast was NOT sent
                mock_manager.broadcast_to_project.assert_not_called()


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