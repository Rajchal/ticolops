"""
Integration tests for authentication API endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas.user import UserRole


class TestAuthAPI:
    """Test authentication API endpoints."""

    @pytest.fixture
    def sample_user_data(self):
        """Sample user registration data."""
        return {
            "email": "test@example.com",
            "name": "Test User",
            "password": "securepassword123",
            "role": "student"
        }

    @pytest.fixture
    def sample_login_data(self):
        """Sample login data."""
        return {
            "email": "test@example.com",
            "password": "securepassword123"
        }

    @pytest.mark.asyncio
    async def test_register_endpoint(self, sample_user_data):
        """Test user registration endpoint."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock no existing user
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            mock_db.add = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Mock refresh to set user attributes
            async def mock_refresh(user):
                user.id = "123e4567-e89b-12d3-a456-426614174000"
                from datetime import datetime
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
            
            mock_db.refresh.side_effect = mock_refresh
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/auth/register", json=sample_user_data)
            
            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"
            assert data["user"]["name"] == "Test User"
            assert data["user"]["role"] == "student"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, sample_user_data):
        """Test registration with duplicate email."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock existing user
            from app.models.user import User, UserRoleEnum, UserStatusEnum
            existing_user = User(
                email="test@example.com",
                name="Existing User",
                hashed_password="hashed",
                role=UserRoleEnum.STUDENT,
                status=UserStatusEnum.OFFLINE
            )
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/auth/register", json=sample_user_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "Email already registered" in data["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_data(self):
        """Test registration with invalid data."""
        invalid_data = {
            "email": "invalid-email",  # Invalid email format
            "name": "",  # Empty name
            "password": "short",  # Too short password
            "role": "student"
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_endpoint(self, sample_login_data):
        """Test user login endpoint."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock existing user with correct password
            from app.models.user import User, UserRoleEnum, UserStatusEnum
            from app.core.security import get_password_hash
            from datetime import datetime
            
            user = User(
                email="test@example.com",
                name="Test User",
                hashed_password=get_password_hash("securepassword123"),
                role=UserRoleEnum.STUDENT,
                status=UserStatusEnum.OFFLINE
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
            
            mock_db.execute.return_value.scalar_one_or_none.return_value = user
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/auth/login", json=sample_login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock no user found
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            invalid_login = {
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/auth/login", json=invalid_login)
            
            assert response.status_code == 401
            data = response.json()
            assert "Invalid email or password" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_endpoint(self):
        """Test getting current user information."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Create a valid token
            from app.core.security import create_access_token
            from app.models.user import User, UserRoleEnum, UserStatusEnum
            from datetime import datetime
            
            user = User(
                email="test@example.com",
                name="Test User",
                hashed_password="hashed",
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
            
            token = create_access_token(data={"sub": str(user.id), "email": user.email})
            
            # Mock user lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = user
            mock_db.commit = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["name"] == "Test User"
            assert data["role"] == "student"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/auth/me")
        
        assert response.status_code == 403  # Forbidden without token

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer invalid.token.here"}
            )
        
        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_logout_endpoint(self):
        """Test logout endpoint."""
        with patch('app.core.database.get_db') as mock_get_db:
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Create a valid token and user
            from app.core.security import create_access_token
            from app.models.user import User, UserRoleEnum, UserStatusEnum
            from datetime import datetime
            
            user = User(
                email="test@example.com",
                name="Test User",
                hashed_password="hashed",
                role=UserRoleEnum.STUDENT,
                status=UserStatusEnum.ONLINE
            )
            user.id = "123e4567-e89b-12d3-a456-426614174000"
            user.created_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            user.last_activity = datetime.utcnow()
            user.preferences = {}
            
            token = create_access_token(data={"sub": str(user.id), "email": user.email})
            
            # Mock user lookup
            mock_db.execute.return_value.scalar_one_or_none.return_value = user
            mock_db.commit = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/auth/logout",
                    headers={"Authorization": f"Bearer {token}"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "Successfully logged out" in data["message"]