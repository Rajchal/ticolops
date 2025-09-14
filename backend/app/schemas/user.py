"""
User-related Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    STUDENT = "student"
    COORDINATOR = "coordinator"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User status enumeration."""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class UserPreferences(BaseModel):
    """User preferences schema."""
    model_config = ConfigDict(from_attributes=True)
    
    email_notifications: bool = True
    push_notifications: bool = True
    activity_visibility: bool = True
    conflict_alerts: bool = True
    deployment_notifications: bool = True


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.STUDENT


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for user updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class UserStatusUpdate(BaseModel):
    """Schema for user status updates."""
    status: UserStatus


class User(UserBase):
    """Complete user schema for responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    avatar: Optional[str] = None
    status: UserStatus = UserStatus.OFFLINE
    last_activity: datetime
    preferences: UserPreferences
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserRegistration(UserCreate):
    """Schema for user registration (alias for UserCreate)."""
    pass


class AuthResult(BaseModel):
    """Schema for authentication results."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: User


class PasswordChange(BaseModel):
    """Schema for password change requests."""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)


class AccountDeletion(BaseModel):
    """Schema for account deletion requests."""
    password: str = Field(..., min_length=8)


class ActivityStatus(BaseModel):
    """Schema for user activity status."""
    user_id: str
    status: UserStatus
    last_activity: datetime
    minutes_since_activity: int
    is_active: bool


class PasswordResetRequest(BaseModel):
    """Schema for password reset requests."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schema for password reset with token."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token requests."""
    refresh_token: str