"""
User profile and preferences management API endpoints.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.user import (
    User, UserUpdate, UserStatusUpdate, UserPreferences, 
    PasswordChange, AccountDeletion, ActivityStatus
)
from app.services.user import UserService
from app.core.deps import get_current_user, get_db
from app.core.database import AsyncSession


router = APIRouter(prefix="/users", tags=["users"])


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get user service instance."""
    return UserService(db)


@router.get("/profile", response_model=User)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current user's profile information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile data
    """
    return current_user


@router.get("/{user_id}/profile", response_model=User)
async def get_user_profile(
    user_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get user profile by ID.
    
    Args:
        user_id: Target user ID
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        User profile data
        
    Raises:
        HTTPException: If user not found
    """
    try:
        return await user_service.get_user_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put("/profile", response_model=User)
async def update_my_profile(
    update_data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Update current user's profile information.
    
    Args:
        update_data: Profile update data
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Updated user profile
    """
    try:
        return await user_service.update_user_profile(current_user.id, update_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.put("/status", response_model=User)
async def update_my_status(
    status_update: UserStatusUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Update current user's online status.
    
    Args:
        status_update: Status update data
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Updated user profile
    """
    try:
        return await user_service.update_user_status(current_user.id, status_update)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update status"
        )


@router.put("/preferences", response_model=User)
async def update_my_preferences(
    preferences: UserPreferences,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Update current user's preferences.
    
    Args:
        preferences: New preferences
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Updated user profile
    """
    try:
        return await user_service.update_user_preferences(current_user.id, preferences)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/activity", response_model=ActivityStatus)
async def get_my_activity_status(
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> ActivityStatus:
    """
    Get current user's activity status.
    
    Args:
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Activity status information
    """
    try:
        activity_data = await user_service.get_user_activity_status(current_user.id)
        return ActivityStatus(**activity_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity status"
        )


@router.get("/{user_id}/activity", response_model=ActivityStatus)
async def get_user_activity_status(
    user_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> ActivityStatus:
    """
    Get user activity status by ID.
    
    Args:
        user_id: Target user ID
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Activity status information
        
    Raises:
        HTTPException: If user not found
    """
    try:
        activity_data = await user_service.get_user_activity_status(user_id)
        return ActivityStatus(**activity_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity status"
        )


@router.post("/activity/ping", status_code=status.HTTP_200_OK)
async def ping_activity(
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Update current user's last activity timestamp (heartbeat).
    
    Args:
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        await user_service.update_last_activity(current_user.id)
        return {"message": "Activity updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update activity"
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Change current user's password.
    
    Args:
        password_data: Password change data
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If current password is incorrect
    """
    try:
        return await user_service.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_my_account(
    deletion_data: AccountDeletion,
    user_service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Delete current user's account.
    
    Args:
        deletion_data: Account deletion data
        user_service: User service instance
        current_user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If password is incorrect
    """
    try:
        return await user_service.delete_user_account(
            current_user.id,
            deletion_data.password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )