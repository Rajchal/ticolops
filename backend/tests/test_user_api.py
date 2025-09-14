"""
Integration tests for user profile and preferences API endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.main import app
from app.models.user import User, UserRoleEnum, UserStatusEnum
from app.core.security import get_password_hash


class TestUserAPI:
    """Test user API endpoints."""

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

    @pytest.fixture
    def auth_headers(self, sample_user):
        """Create authentication headers with valid token."""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": str(sample_user.id), "email": sample_user.email})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_get_my_profile(self, sample_user, auth_headers):
        """Test getting current user's profile."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/users/profile", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["name"] == "Test User"
            assert data["role"] == "student"
            assert data["status"] == "online"

    @pytest.mark.asyncio
    async def test_get_user_profile_by_id(self, sample_user, auth_headers):
        """Test getting user profile by ID."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication and profile retrieval
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    f"/api/users/{sample_user.id}/profile",
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_update_my_profile(self, sample_user, auth_headers):
        """Test updating current user's profile."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            update_data = {
                "name": "Updated Name",
                "avatar": "https://example.com/avatar.jpg"
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.put(
                    "/api/users/profile",
                    json=update_data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"
            assert data["avatar"] == "https://example.com/avatar.jpg"

    @pytest.mark.asyncio
    async def test_update_my_status(self, sample_user, auth_headers):
        """Test updating current user's status."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            status_data = {"status": "away"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.put(
                    "/api/users/status",
                    json=status_data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "away"

    @pytest.mark.asyncio
    async def test_update_my_preferences(self, sample_user, auth_headers):
        """Test updating current user's preferences."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            preferences_data = {
                "email_notifications": False,
                "push_notifications": True,
                "activity_visibility": False,
                "conflict_alerts": True,
                "deployment_notifications": False
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.put(
                    "/api/users/preferences",
                    json=preferences_data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["preferences"]["email_notifications"] is False
            assert data["preferences"]["push_notifications"] is True

    @pytest.mark.asyncio
    async def test_get_my_activity_status(self, sample_user, auth_headers):
        """Test getting current user's activity status."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/users/activity", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == str(sample_user.id)
            assert data["status"] == "online"
            assert "minutes_since_activity" in data
            assert "is_active" in data

    @pytest.mark.asyncio
    async def test_ping_activity(self, sample_user, auth_headers):
        """Test pinging user activity (heartbeat)."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/users/activity/ping", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Activity updated"

    @pytest.mark.asyncio
    async def test_change_password(self, sample_user, auth_headers):
        """Test changing user password."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            password_data = {
                "current_password": "securepassword123",
                "new_password": "newsecurepassword456"
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/users/change-password",
                    json=password_data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Password updated successfully"

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, sample_user, auth_headers):
        """Test changing password with wrong current password."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            password_data = {
                "current_password": "wrongpassword",
                "new_password": "newsecurepassword456"
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/users/change-password",
                    json=password_data,
                    headers=auth_headers
                )
            
            assert response.status_code == 400
            data = response.json()
            assert "Current password is incorrect" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_account(self, sample_user, auth_headers):
        """Test deleting user account."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock user lookup for authentication
            mock_db.execute.return_value.scalar_one_or_none.return_value = sample_user
            mock_db.commit = AsyncMock()
            
            deletion_data = {"password": "securepassword123"}
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.delete(
                    "/api/users/account",
                    json=deletion_data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Account deactivated successfully"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test accessing protected endpoints without authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test various endpoints without auth headers
            endpoints = [
                ("GET", "/api/users/profile"),
                ("PUT", "/api/users/profile"),
                ("PUT", "/api/users/status"),
                ("PUT", "/api/users/preferences"),
                ("GET", "/api/users/activity"),
                ("POST", "/api/users/activity/ping"),
                ("POST", "/api/users/change-password"),
                ("DELETE", "/api/users/account")
            ]
            
            for method, endpoint in endpoints:
                if method == "GET":
                    response = await client.get(endpoint)
                elif method == "PUT":
                    response = await client.put(endpoint, json={})
                elif method == "POST":
                    response = await client.post(endpoint, json={})
                elif method == "DELETE":
                    response = await client.delete(endpoint, json={})
                
                assert response.status_code == 403  # Forbidden without token

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test accessing endpoints with invalid token."""
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/users/profile", headers=invalid_headers)
            assert response.status_code == 401  # Unauthorized