"""
Authentication API endpoints for user registration and login.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.schemas.user import UserCreate, UserLogin, AuthResult, User
from app.services.auth import AuthService
from app.core.deps import get_auth_service, get_current_user


router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=AuthResult, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AuthResult:
    """
    Register a new user account.
    
    Args:
        user_data: User registration data
        auth_service: Authentication service instance
        
    Returns:
        Authentication result with access token and user data
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    try:
        return await auth_service.register(user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResult)
async def login(
    credentials: UserLogin,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AuthResult:
    """
    Authenticate user and return access token.
    
    Args:
        credentials: User login credentials
        auth_service: Authentication service instance
        
    Returns:
        Authentication result with access token and user data
        
    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        return await auth_service.login(credentials)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from token
        
    Returns:
        Current user data
    """
    return current_user


@router.post("/refresh", response_model=AuthResult)
async def refresh_access_token(
    refresh_token: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AuthResult:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_token: JWT refresh token
        auth_service: Authentication service instance
        
    Returns:
        New authentication result with fresh access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        return await auth_service.refresh_token(refresh_token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Logout current user (client should discard token).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
        
    Note:
        In a stateless JWT implementation, logout is handled client-side
        by discarding the token. For enhanced security, you could implement
        a token blacklist or use shorter token expiration times.
    """
    return {"message": "Successfully logged out"}


@router.get("/validate", response_model=User)
async def validate_token(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Validate current access token and return user data.
    
    Args:
        current_user: Current authenticated user from token validation
        
    Returns:
        Current user data if token is valid
    """
    return current_user