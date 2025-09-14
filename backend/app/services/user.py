"""
User profile and preferences management service.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserStatusEnum
from app.schemas.user import UserUpdate, UserStatusUpdate, UserPreferences, User as UserSchema
from app.core.security import get_password_hash


class UserService:
    """Service for user profile and preferences management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_profile(self, user_id: str) -> UserSchema:
        """
        Get user profile by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile data
            
        Raises:
            HTTPException: If user not found
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return await self._user_to_schema(user)

    async def update_user_profile(self, user_id: str, update_data: UserUpdate) -> UserSchema:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            update_data: Profile update data
            
        Returns:
            Updated user profile
            
        Raises:
            HTTPException: If user not found
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if update_data.name is not None:
            user.name = update_data.name
        
        if update_data.avatar is not None:
            user.avatar = update_data.avatar
        
        if update_data.preferences is not None:
            # Merge with existing preferences
            current_prefs = user.preferences or {}
            new_prefs = update_data.preferences.model_dump()
            user.preferences = {**current_prefs, **new_prefs}
        
        # Update timestamp
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return await self._user_to_schema(user)

    async def update_user_status(self, user_id: str, status_update: UserStatusUpdate) -> UserSchema:
        """
        Update user online status.
        
        Args:
            user_id: User ID
            status_update: Status update data
            
        Returns:
            Updated user profile
            
        Raises:
            HTTPException: If user not found
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update status and last activity
        user.status = UserStatusEnum(status_update.status.value)
        user.last_activity = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return await self._user_to_schema(user)

    async def update_user_preferences(self, user_id: str, preferences: UserPreferences) -> UserSchema:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            preferences: New preferences
            
        Returns:
            Updated user profile
            
        Raises:
            HTTPException: If user not found
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update preferences
        user.preferences = preferences.model_dump()
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return await self._user_to_schema(user)

    async def get_user_activity_status(self, user_id: str) -> dict:
        """
        Get user activity status information.
        
        Args:
            user_id: User ID
            
        Returns:
            Activity status information
            
        Raises:
            HTTPException: If user not found
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Calculate time since last activity
        time_since_activity = datetime.utcnow() - user.last_activity
        minutes_since_activity = int(time_since_activity.total_seconds() / 60)
        
        return {
            "user_id": str(user.id),
            "status": user.status.value,
            "last_activity": user.last_activity,
            "minutes_since_activity": minutes_since_activity,
            "is_active": user.status != UserStatusEnum.OFFLINE and minutes_since_activity < 5
        }

    async def update_last_activity(self, user_id: str) -> None:
        """
        Update user's last activity timestamp.
        
        Args:
            user_id: User ID
            
        Raises:
            HTTPException: If user not found
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.last_activity = datetime.utcnow()
        await self.db.commit()

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> dict:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            Success message
            
        Raises:
            HTTPException: If user not found or current password is incorrect
        """
        from app.core.security import verify_password
        
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
        
        return {"message": "Password updated successfully"}

    async def delete_user_account(self, user_id: str, password: str) -> dict:
        """
        Delete user account (soft delete by setting status to offline).
        
        Args:
            user_id: User ID
            password: Password for verification
            
        Returns:
            Success message
            
        Raises:
            HTTPException: If user not found or password is incorrect
        """
        from app.core.security import verify_password
        
        user = await self._get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is incorrect"
            )
        
        # Soft delete - set status to offline and clear sensitive data
        user.status = UserStatusEnum.OFFLINE
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return {"message": "Account deactivated successfully"}

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