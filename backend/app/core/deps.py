"""
FastAPI dependencies for authentication and database access.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth import AuthService
from app.schemas.user import User


# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Dependency to get authentication service instance.
    
    Args:
        db: Database session
        
    Returns:
        AuthService instance
    """
    return AuthService(db)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> User:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer token credentials
        auth_service: Authentication service instance
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        user = await auth_service.validate_token(credentials.credentials)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get current active user (not offline).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is offline
    """
    if current_user.status == "offline":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is offline"
        )
    return current_user


def require_role(required_role: str):
    """
    Dependency factory to require specific user role.
    
    Args:
        required_role: Required user role (student, coordinator, admin)
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role} role"
            )
        return current_user
    
    return role_checker


# Common role dependencies
require_admin = require_role("admin")
require_coordinator = require_role("coordinator")