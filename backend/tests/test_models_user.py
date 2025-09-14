"""
Unit tests for user models and schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.user import (
    User, UserCreate, UserUpdate, UserLogin, UserRegistration,
    UserStatusUpdate, UserRole, UserStatus, UserPreferences, AuthResult
)
from app.models.user import User as UserModel, UserRoleEnum, UserStatusEnum


class TestUserSchemas:
    """Test user Pydantic schemas."""

    def test_user_preferences_defaults(self):
        """Test UserPreferences with default values."""
        prefs = UserPreferences()
        assert prefs.email_notifications is True
        assert prefs.push_notifications is True
        assert prefs.activity_visibility is True
        assert prefs.conflict_alerts is True
        assert prefs.deployment_notifications is True

    def test_user_preferences_custom(self):
        """Test UserPreferences with custom values."""
        prefs = UserPreferences(
            email_notifications=False,
            push_notifications=True,
            activity_visibility=False,
            conflict_alerts=True,
            deployment_notifications=False
        )
        assert prefs.email_notifications is False
        assert prefs.push_notifications is True
        assert prefs.activity_visibility is False
        assert prefs.conflict_alerts is True
        assert prefs.deployment_notifications is False

    def test_user_create_valid(self):
        """Test valid UserCreate schema."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password": "securepassword123",
            "role": UserRole.STUDENT
        }
        user = UserCreate(**user_data)
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.password == "securepassword123"
        assert user.role == UserRole.STUDENT

    def test_user_create_invalid_email(self):
        """Test UserCreate with invalid email."""
        user_data = {
            "email": "invalid-email",
            "name": "Test User",
            "password": "securepassword123"
        }
        with pytest.raises(ValidationError):
            UserCreate(**user_data)

    def test_user_create_short_password(self):
        """Test UserCreate with password too short."""
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "password": "short"
        }
        with pytest.raises(ValidationError):
            UserCreate(**user_data)

    def test_user_create_empty_name(self):
        """Test UserCreate with empty name."""
        user_data = {
            "email": "test@example.com",
            "name": "",
            "password": "securepassword123"
        }
        with pytest.raises(ValidationError):
            UserCreate(**user_data)

    def test_user_update_partial(self):
        """Test UserUpdate with partial data."""
        update_data = {"name": "Updated Name"}
        user_update = UserUpdate(**update_data)
        assert user_update.name == "Updated Name"
        assert user_update.avatar is None
        assert user_update.preferences is None

    def test_user_status_update(self):
        """Test UserStatusUpdate schema."""
        status_update = UserStatusUpdate(status=UserStatus.AWAY)
        assert status_update.status == UserStatus.AWAY

    def test_user_login_valid(self):
        """Test valid UserLogin schema."""
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        user_login = UserLogin(**login_data)
        assert user_login.email == "test@example.com"
        assert user_login.password == "securepassword123"

    def test_auth_result(self):
        """Test AuthResult schema."""
        user_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "name": "Test User",
            "role": UserRole.STUDENT,
            "status": UserStatus.ONLINE,
            "last_activity": datetime.now(),
            "preferences": UserPreferences(),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        user = User(**user_data)
        
        auth_result = AuthResult(
            access_token="jwt-token-here",
            expires_in=1800,
            user=user
        )
        assert auth_result.access_token == "jwt-token-here"
        assert auth_result.token_type == "bearer"
        assert auth_result.expires_in == 1800
        assert auth_result.user.email == "test@example.com"


class TestUserEnums:
    """Test user enumeration values."""

    def test_user_role_enum(self):
        """Test UserRole enum values."""
        assert UserRole.STUDENT == "student"
        assert UserRole.COORDINATOR == "coordinator"
        assert UserRole.ADMIN == "admin"

    def test_user_status_enum(self):
        """Test UserStatus enum values."""
        assert UserStatus.ONLINE == "online"
        assert UserStatus.AWAY == "away"
        assert UserStatus.OFFLINE == "offline"

    def test_user_role_enum_db(self):
        """Test UserRoleEnum database enum values."""
        assert UserRoleEnum.STUDENT.value == "student"
        assert UserRoleEnum.COORDINATOR.value == "coordinator"
        assert UserRoleEnum.ADMIN.value == "admin"

    def test_user_status_enum_db(self):
        """Test UserStatusEnum database enum values."""
        assert UserStatusEnum.ONLINE.value == "online"
        assert UserStatusEnum.AWAY.value == "away"
        assert UserStatusEnum.OFFLINE.value == "offline"


class TestUserModel:
    """Test user SQLAlchemy model."""

    def test_user_model_repr(self):
        """Test User model string representation."""
        # Note: This test doesn't require database connection
        # We're just testing the __repr__ method logic
        user = UserModel()
        user.id = "123e4567-e89b-12d3-a456-426614174000"
        user.email = "test@example.com"
        user.name = "Test User"
        
        expected = "<User(id=123e4567-e89b-12d3-a456-426614174000, email=test@example.com, name=Test User)>"
        assert repr(user) == expected

    def test_user_model_attributes(self):
        """Test User model has required attributes."""
        # Test that the model class has the expected attributes
        assert hasattr(UserModel, 'id')
        assert hasattr(UserModel, 'email')
        assert hasattr(UserModel, 'name')
        assert hasattr(UserModel, 'hashed_password')
        assert hasattr(UserModel, 'avatar')
        assert hasattr(UserModel, 'role')
        assert hasattr(UserModel, 'status')
        assert hasattr(UserModel, 'last_activity')
        assert hasattr(UserModel, 'preferences')
        assert hasattr(UserModel, 'created_at')
        assert hasattr(UserModel, 'updated_at')

    def test_user_model_table_name(self):
        """Test User model table name."""
        assert UserModel.__tablename__ == "users"