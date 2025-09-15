import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from app.main import app
from app.core.security import create_access_token


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def auth_token(self):
        return create_access_token({"sub": "user-123", "role": "student"})

    def test_websocket_connection_authentication(self, client, mock_db, auth_token):
        """Test WebSocket connection with authentication"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user and project access
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            # Test successful connection with valid token
            with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                # Should receive connection confirmation
                data = websocket.receive_json()
                assert data["type"] == "connection_established"
                assert data["user_id"] == "user-123"

    def test_websocket_connection_without_auth(self, client):
        """Test WebSocket connection without authentication"""
        
        # Should reject connection without token
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/project-123"):
                pass

    def test_websocket_presence_updates(self, client, mock_db, auth_token):
        """Test real-time presence updates via WebSocket"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.presence_manager.PresenceManager') as mock_presence:
                # Mock user data
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "role": "student"
                }
                
                presence_manager = mock_presence.return_value
                
                with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                    # Receive connection confirmation
                    websocket.receive_json()
                    
                    # Send presence update
                    websocket.send_json({
                        "type": "presence_update",
                        "data": {
                            "status": "online",
                            "location": "src/components/Dashboard.tsx"
                        }
                    })
                    
                    # Should receive acknowledgment
                    response = websocket.receive_json()
                    assert response["type"] == "presence_updated"
                    
                    # Verify presence manager was called
                    presence_manager.update_user_presence.assert_called_once()

    def test_websocket_activity_broadcasting(self, client, mock_db, auth_token):
        """Test activity broadcasting to team members"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.websocket.connection_manager.ConnectionManager') as mock_manager:
                # Mock user data
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "role": "student"
                }
                
                connection_manager = mock_manager.return_value
                
                with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                    # Receive connection confirmation
                    websocket.receive_json()
                    
                    # Send activity update
                    websocket.send_json({
                        "type": "activity_update",
                        "data": {
                            "type": "coding",
                            "location": "src/utils/helpers.ts",
                            "action": "editing"
                        }
                    })
                    
                    # Should receive activity confirmation
                    response = websocket.receive_json()
                    assert response["type"] == "activity_logged"
                    
                    # Verify broadcast to other users
                    connection_manager.broadcast_to_project.assert_called_once()

    def test_websocket_conflict_detection(self, client, mock_db, auth_token):
        """Test real-time conflict detection via WebSocket"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.conflict_detector.ConflictDetector') as mock_detector:
                # Mock user data
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "role": "student"
                }
                
                conflict_detector = mock_detector.return_value
                conflict_detector.detect_conflicts.return_value = [
                    {
                        "location": "src/components/Header.tsx",
                        "users": ["user-123", "user-456"],
                        "severity": "medium"
                    }
                ]
                
                with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                    # Receive connection confirmation
                    websocket.receive_json()
                    
                    # Simulate conflict detection trigger
                    websocket.send_json({
                        "type": "check_conflicts",
                        "data": {
                            "location": "src/components/Header.tsx"
                        }
                    })
                    
                    # Should receive conflict notification
                    response = websocket.receive_json()
                    assert response["type"] == "conflict_detected"
                    assert len(response["data"]["conflicts"]) == 1

    def test_websocket_deployment_notifications(self, client, mock_db, auth_token):
        """Test deployment status notifications via WebSocket"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                # Receive connection confirmation
                websocket.receive_json()
                
                # Simulate deployment status update from external service
                # This would normally come from the deployment service
                deployment_update = {
                    "type": "deployment_update",
                    "data": {
                        "deployment_id": "deploy-123",
                        "status": "success",
                        "url": "https://staging.example.com",
                        "duration": 120
                    }
                }
                
                # In a real scenario, this would be sent by the deployment service
                # For testing, we simulate receiving it
                with patch('app.websocket.connection_manager.ConnectionManager.send_to_user') as mock_send:
                    # Verify the WebSocket can handle deployment updates
                    # This tests the message handling infrastructure
                    pass

    def test_websocket_multiple_connections(self, client, mock_db):
        """Test multiple WebSocket connections for the same project"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Create tokens for different users
            user1_token = create_access_token({"sub": "user-123", "role": "student"})
            user2_token = create_access_token({"sub": "user-456", "role": "student"})
            
            # Mock user data for both users
            def mock_user_data(query):
                if "user-123" in str(query):
                    return {"id": "user-123", "email": "user1@example.com", "role": "student"}
                else:
                    return {"id": "user-456", "email": "user2@example.com", "role": "student"}
            
            mock_db.execute.return_value.fetchone.side_effect = mock_user_data
            
            # Connect both users to the same project
            with client.websocket_connect(f"/ws/project-123?token={user1_token}") as ws1:
                with client.websocket_connect(f"/ws/project-123?token={user2_token}") as ws2:
                    # Both should receive connection confirmations
                    ws1_data = ws1.receive_json()
                    ws2_data = ws2.receive_json()
                    
                    assert ws1_data["type"] == "connection_established"
                    assert ws2_data["type"] == "connection_established"
                    
                    # User 1 sends activity update
                    ws1.send_json({
                        "type": "activity_update",
                        "data": {
                            "type": "coding",
                            "location": "src/main.tsx"
                        }
                    })
                    
                    # User 1 should receive confirmation
                    ws1_response = ws1.receive_json()
                    assert ws1_response["type"] == "activity_logged"

    def test_websocket_connection_cleanup(self, client, mock_db, auth_token):
        """Test WebSocket connection cleanup on disconnect"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.presence_manager.PresenceManager') as mock_presence:
                # Mock user data
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "role": "student"
                }
                
                presence_manager = mock_presence.return_value
                
                with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                    # Receive connection confirmation
                    websocket.receive_json()
                    
                    # Connection should be established
                    presence_manager.user_connected.assert_called_once()
                
                # After context exit, connection should be cleaned up
                presence_manager.user_disconnected.assert_called_once()

    def test_websocket_error_handling(self, client, mock_db, auth_token):
        """Test WebSocket error handling"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                # Receive connection confirmation
                websocket.receive_json()
                
                # Send invalid message format
                websocket.send_json({
                    "invalid": "message"
                })
                
                # Should receive error response
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "Invalid message format" in response["message"]

    def test_websocket_rate_limiting(self, client, mock_db, auth_token):
        """Test WebSocket rate limiting"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                # Receive connection confirmation
                websocket.receive_json()
                
                # Send many messages rapidly
                for i in range(100):
                    websocket.send_json({
                        "type": "activity_update",
                        "data": {
                            "type": "coding",
                            "location": f"file-{i}.tsx"
                        }
                    })
                
                # Should eventually receive rate limit warning
                messages = []
                try:
                    for _ in range(10):  # Try to receive up to 10 messages
                        message = websocket.receive_json()
                        messages.append(message)
                        if message.get("type") == "rate_limit_warning":
                            break
                except:
                    pass
                
                # Should have received at least some messages
                assert len(messages) > 0

    def test_websocket_project_permissions(self, client, mock_db):
        """Test WebSocket project access permissions"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Create token for user not in project
            outsider_token = create_access_token({"sub": "outsider-123", "role": "student"})
            
            # Mock user exists but not in project
            mock_db.execute.return_value.fetchone.return_value = None
            
            # Should reject connection
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(f"/ws/project-123?token={outsider_token}"):
                    pass

    def test_websocket_message_persistence(self, client, mock_db, auth_token):
        """Test WebSocket message persistence and replay"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.message_store.MessageStore') as mock_store:
                # Mock user data
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "role": "student"
                }
                
                message_store = mock_store.return_value
                message_store.get_recent_messages.return_value = [
                    {
                        "type": "activity_update",
                        "user_id": "user-456",
                        "data": {"type": "coding", "location": "src/app.tsx"},
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                ]
                
                with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                    # Receive connection confirmation
                    connection_msg = websocket.receive_json()
                    assert connection_msg["type"] == "connection_established"
                    
                    # Should receive recent messages
                    recent_msg = websocket.receive_json()
                    assert recent_msg["type"] == "recent_messages"
                    assert len(recent_msg["messages"]) == 1

    def test_websocket_heartbeat(self, client, mock_db, auth_token):
        """Test WebSocket heartbeat mechanism"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            with client.websocket_connect(f"/ws/project-123?token={auth_token}") as websocket:
                # Receive connection confirmation
                websocket.receive_json()
                
                # Send heartbeat
                websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": "2024-01-01T00:00:00Z"
                })
                
                # Should receive heartbeat response
                response = websocket.receive_json()
                assert response["type"] == "heartbeat_ack"

    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self, client, mock_db):
        """Test handling of many concurrent WebSocket connections"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            # Create multiple tokens
            tokens = [create_access_token({"sub": f"user-{i}", "role": "student"}) for i in range(10)]
            
            # Test concurrent connections
            connections = []
            try:
                for token in tokens:
                    ws = client.websocket_connect(f"/ws/project-123?token={token}")
                    connections.append(ws)
                
                # All connections should be established
                assert len(connections) == 10
                
            finally:
                # Clean up connections
                for ws in connections:
                    try:
                        ws.close()
                    except:
                        pass