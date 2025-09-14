"""Custom exception classes for the application."""

from typing import Optional, Any, Dict


class BaseAppException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(BaseAppException):
    """Exception raised when a requested resource is not found."""
    pass


class PermissionError(BaseAppException):
    """Exception raised when user lacks permission for an operation."""
    pass


class ValidationError(BaseAppException):
    """Exception raised when data validation fails."""
    pass


class AuthenticationError(BaseAppException):
    """Exception raised when authentication fails."""
    pass


class ConflictError(BaseAppException):
    """Exception raised when there's a conflict with existing data."""
    pass


class ExternalServiceError(BaseAppException):
    """Exception raised when external service calls fail."""
    pass


class RateLimitError(BaseAppException):
    """Exception raised when rate limits are exceeded."""
    pass


class DeploymentError(BaseAppException):
    """Exception raised when deployment operations fail."""
    pass