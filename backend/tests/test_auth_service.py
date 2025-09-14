"""
Unit tests for authentication service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from app.services.auth import AuthService
from app.schemas.user import UserCreate, UserLogin, UserRole
from app.models.user import User, UserRoleEnum, UserStatusEnum
from app.core.security import get_password_hash, verify_password


class TestAuthService:
    """Test authentication service functionality."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService instance with mocked database."""
        return AuthService(mock_db)

    @pytest.fixture
    def sample_user_create(self):
        """Sample user creation data."""
        return UserCreate(
            email="test@example.com",
            name="Test User",
            password="securepassword123",
            role=UserRole.STUDENT
        )

    @pytest.fixture
    def sample_user_login(self):
        """Sample user login data."""
        return UserLogin(
            email="test@example.com",
            password="securepassword123"
        )

    @pytest.fixture
    def sample_db_user(self):
        """Sample database user."""
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
        return user

    @pytest.mark.asyncio
    async def test_register_success(self, auth_service, mock_db, sample_user_create, sample_db_user):
        """Test successful user registration."""
        # Mock the _get_user_by_email method directly
        with patch.object(auth_service, '_get_user_by_email', return_value=None):
            # Mock database operations
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Mock the refresh to set the user ID
            async def mock_refresh(user):
                user.id = sample_db_user.id
                user.created_at = sample_db_user.created_at
                user.updated_at = sample_db_user.updated_at
                user.last_activity = sample_db_user.last_activity
            
            mock_db.refresh.side_effect = mock_refresh
            
            # Call register
            result = await auth_service.register(sample_user_create)
            
            # Verify result
            assert result.access_token is not None
            assert result.token_type == "bearer"
            assert result.expires_in == 1800  # 30 minutes * 60 seconds
            assert result.user.email == "test@example.com"
            assert result.user.name == "Test User"
            assert result.user.role == "student"
            
            # Verify database operations
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_email_exists(self, auth_service, mock_db, sample_user_create, sample_db_user):
        """Test registration with existing email."""
        # Mock the _get_user_by_email method to return existing user
        with patch.object(auth_service, '_get_user_by_email', return_value=sample_db_user):
            # Call register and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.register(sample_user_create)
            
            assert exc_info.value.status_code == 400
            assert "Email already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_db, sample_user_login, sample_db_user):
        """Test successful user login."""
        # Mock the _get_user_by_email method to return user
        with patch.object(auth_service, '_get_user_by_email', return_value=sample_db_user):
            # Mock database operations
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Call login
            result = await auth_service.login(sample_user_login)
            
            # Verify result
            assert result.access_token is not None
            assert result.token_type == "bearer"
            assert result.user.email == "test@example.com"
            assert result.user.status == "online"  # Should be updated to online
            
            # Verify user status was updated
            assert sample_db_user.status == UserStatusEnum.ONLINE
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service, mock_db, sample_user_login):
        """Test login with non-existent user."""
        # Mock the _get_user_by_email method to return None
        with patch.object(auth_service, '_get_user_by_email', return_value=None):
            # Call login and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login(sample_user_login)
            
            assert exc_info.value.status_code == 401
            assert "Invalid email or password" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_service, mock_db, sample_db_user):
        """Test login with wrong password."""
        # Mock the _get_user_by_email method to return user
        with patch.object(auth_service, '_get_user_by_email', return_value=sample_db_user):
            wrong_credentials = UserLogin(
                email="test@example.com",
                password="wrongpassword"
            )
            
            # Call login and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login(wrong_credentials)
            
            assert exc_info.value.status_code == 401
            assert "Invalid email or password" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_token_success(self, auth_service, mock_db, sample_db_user):
        """Test successful token validation."""
        from app.core.security import create_access_token
        
        # Create a valid token
        token = create_access_token(data={"sub": str(sample_db_user.id), "email": sample_db_user.email})
        
        # Mock the _get_user_by_id method to return user
        with patch.object(auth_service, '_get_user_by_id', return_value=sample_db_user):
            # Mock database operations
            mock_db.commit = AsyncMock()
            
            # Call validate_token
            result = await auth_service.validate_token(token)
            
            # Verify result
            assert result.email == "test@example.com"
            assert result.id == str(sample_db_user.id)
            
            # Verify last activity was updated
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, auth_service, mock_db):
        """Test validation with invalid token."""
        invalid_token = "invalid.jwt.token"
        
        # Call validate_token and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.validate_token(invalid_token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_token_user_not_found(self, auth_service, mock_db):
        """Test validation when user no longer exists."""
        from app.core.security import create_access_token
        
        # Create token for non-existent user
        token = create_access_token(data={"sub": "non-existent-id", "email": "test@example.com"})
        
        # Mock the _get_user_by_id method to return None
        with patch.object(auth_service, '_get_user_by_id', return_value=None):
            # Call validate_token and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.validate_token(token)
            
            assert exc_info.value.status_code == 401
            assert "User not found" in str(exc_info.value.detail)


class TestSecurityUtilities:
    """Test security utility functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "securepassword123"
        
        # Hash password
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify wrong password
        assert verify_password("wrongpassword", hashed) is False

    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        from app.core.security import create_access_token, verify_token
        
        # Create token
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        
        # Verify token
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload  # Expiration should be set
        
        # Verify invalid token
        invalid_payload = verify_token("invalid.token.here")
        assert invalid_payload is None