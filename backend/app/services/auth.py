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
from app.core.security import get_password_hash, verify_password, create_access_token, verify_token
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
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(db_user.id), "email": db_user.email}
        )
        
        # Convert to response schema
        user_schema = await self._user_to_schema(db_user)
        
        return AuthResult(
            access_token=access_token,
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
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Convert to response schema
        user_schema = await self._user_to_schema(user)
        
        return AuthResult(
            access_token=access_token,
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
        # For now, we'll implement this as a simple token refresh
        # In a full implementation, you'd want to store refresh tokens
        payload = verify_token(refresh_token)
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
        
        # Create new access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        user_schema = await self._user_to_schema(user)
        
        return AuthResult(
            access_token=access_token,
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