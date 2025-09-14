"""
Authentication service for user registration, login, and token management.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserRoleEnum, UserStatusEnum
from app.schemas.user import UserCreate, UserLogin, AuthResult, User as UserSchema
from app.core.security import (
    get_password_hash, verify_password, create_access_token, verify_token,
    create_refresh_token, verify_refresh_token, create_password_reset_token,
    verify_password_reset_token
)
from app.core.config import settings


class AuthService:
    """Authentication service for user management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_data: UserCreate) -> AuthResult:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            Authentication result with token and user data
            
        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        existing_user = await self._get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            role=UserRoleEnum(user_data.role.value),
            status=UserStatusEnum.OFFLINE,
            preferences={
                "email_notifications": True,
                "push_notifications": True,
                "activity_visibility": True,
                "conflict_alerts": True,
                "deployment_notifications": True
            }
        )
        
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        
        # Create access and refresh tokens
        token_data = {"sub": str(db_user.id), "email": db_user.email}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        # Convert to response schema
        user_schema = await self._user_to_schema(db_user)
        
        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_schema
        )

    async def login(self, credentials: UserLogin) -> AuthResult:
        """
        Authenticate user and return access token.
        
        Args:
            credentials: User login credentials
            
        Returns:
            Authentication result with token and user data
            
        Raises:
            HTTPException: If credentials are invalid
        """
        # Get user by email
        user = await self._get_user_by_email(credentials.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update user status to online
        user.status = UserStatusEnum.ONLINE
        user.last_activity = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        # Create access and refresh tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        # Convert to response schema
        user_schema = await self._user_to_schema(user)
        
        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_schema
        )

    async def validate_token(self, token: str) -> UserSchema:
        """
        Validate JWT token and return user data.
        
        Args:
            token: JWT access token
            
        Returns:
            User data if token is valid
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Update last activity
        user.last_activity = datetime.utcnow()
        await self.db.commit()
        
        return await self._user_to_schema(user)

    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New authentication result with fresh token
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        # Verify refresh token
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access and refresh tokens
        token_data = {"sub": str(user.id), "email": user.email}
        new_access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(data=token_data)
        
        user_schema = await self._user_to_schema(user)
        
        return AuthResult(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_schema
        )

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _user_to_schema(self, user: User) -> UserSchema:
        """Convert User model to UserSchema."""
        return UserSchema(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar=user.avatar,
            role=user.role.value,
            status=user.status.value,
            last_activity=user.last_activity,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    async def request_password_reset(self, email: str) -> dict:
        """
        Request password reset for user.
        
        Args:
            email: User email address
            
        Returns:
            Success message (always returns success for security)
        """
        # Always return success to prevent email enumeration
        # In a real implementation, you'd send an email if user exists
        user = await self._get_user_by_email(email)
        if user:
            # Generate password reset token
            reset_token = create_password_reset_token(email)
            # TODO: Send email with reset token
            # For now, we'll just log it (remove in production)
            print(f"Password reset token for {email}: {reset_token}")
        
        return {"message": "If the email exists, a password reset link has been sent"}

    async def reset_password(self, token: str, new_password: str) -> dict:
        """
        Reset user password using reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            Success message
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        # Verify reset token
        email = verify_password_reset_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Get user by email
        user = await self._get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return {"message": "Password has been reset successfully"}

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> dict:
        """
        Change user password (requires current password).
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            Success message
            
        Raises:
            HTTPException: If current password is incorrect
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return {"message": "Password has been changed successfully"}

    async def logout(self, user_id: str) -> dict:
        """
        Logout user (update status to offline).
        
        Args:
            user_id: User ID
            
        Returns:
            Success message
        """
        user = await self._get_user_by_id(user_id)
        if user:
            user.status = UserStatusEnum.OFFLINE
            user.last_activity = datetime.utcnow()
            await self.db.commit()
        
        return {"message": "Successfully logged out"}