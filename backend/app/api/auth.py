"""
Authentication API endpoints for user registration and login.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.schemas.user import (
    UserCreate, UserLogin, AuthResult, User, PasswordChange,
    PasswordResetRequest, PasswordReset, RefreshTokenRequest
)
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
    request: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AuthResult:
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request data
        auth_service: Authentication service instance
        
    Returns:
        New authentication result with fresh access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        return await auth_service.refresh_token(request.refresh_token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Logout current user and update status to offline.
    
    Args:
        current_user: Current authenticated user
        auth_service: Authentication service instance
        
    Returns:
        Success message
    """
    try:
        return await auth_service.logout(current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


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


@router.post("/password/reset-request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    request: PasswordResetRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Request password reset for user email.
    
    Args:
        request: Password reset request with email
        auth_service: Authentication service instance
        
    Returns:
        Success message (always returns success for security)
    """
    try:
        return await auth_service.request_password_reset(request.email)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/password/reset", status_code=status.HTTP_200_OK)
async def reset_password(
    request: PasswordReset,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Reset password using reset token.
    
    Args:
        request: Password reset data with token and new password
        auth_service: Authentication service instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        return await auth_service.reset_password(request.token, request.new_password)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/password/change", status_code=status.HTTP_200_OK)
async def change_password(
    request: PasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Change user password (requires current password).
    
    Args:
        request: Password change request with current and new passwords
        current_user: Current authenticated user
        auth_service: Authentication service instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If current password is incorrect
    """
    try:
        return await auth_service.change_password(
            current_user.id, 
            request.current_password, 
            request.new_password
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )