"""
Enhanced API documentation decorators and examples.
"""

from functools import wraps
from typing import Dict, Any, List, Optional, Callable
from fastapi import HTTPException
from fastapi.responses import JSONResponse


def api_example(
    summary: str,
    description: str,
    examples: Dict[str, Any],
    responses: Optional[Dict[int, Dict[str, Any]]] = None
):
    """
    Decorator to add comprehensive examples and documentation to API endpoints.
    
    Args:
        summary: Brief summary of the endpoint
        description: Detailed description of the endpoint functionality
        examples: Dictionary of request/response examples
        responses: Additional response examples for different status codes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Add documentation attributes
        wrapper.__doc__ = f"""
        {summary}
        
        {description}
        
        Examples:
        {examples}
        """
        
        # Store examples for OpenAPI generation
        if not hasattr(wrapper, '_api_examples'):
            wrapper._api_examples = {}
        
        wrapper._api_examples.update(examples)
        
        if responses:
            wrapper._api_responses = responses
        
        return wrapper
    
    return decorator


# Common response examples
COMMON_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Validation Error",
                        "value": {
                            "detail": "Invalid input data",
                            "code": "VALIDATION_ERROR"
                        }
                    },
                    "missing_field": {
                        "summary": "Missing Required Field",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "email"],
                                    "msg": "field required",
                                    "type": "value_error.missing"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "examples": {
                    "missing_token": {
                        "summary": "Missing Authentication Token",
                        "value": {
                            "detail": "Not authenticated",
                            "code": "MISSING_TOKEN"
                        }
                    },
                    "invalid_token": {
                        "summary": "Invalid Token",
                        "value": {
                            "detail": "Could not validate credentials",
                            "code": "INVALID_TOKEN"
                        }
                    },
                    "expired_token": {
                        "summary": "Expired Token",
                        "value": {
                            "detail": "Token has expired",
                            "code": "EXPIRED_TOKEN"
                        }
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "detail": "You do not have permission to perform this action",
                            "code": "INSUFFICIENT_PERMISSIONS"
                        }
                    },
                    "role_required": {
                        "summary": "Role Required",
                        "value": {
                            "detail": "This action requires coordinator or admin role",
                            "code": "ROLE_REQUIRED"
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "resource_not_found": {
                        "summary": "Resource Not Found",
                        "value": {
                            "detail": "The requested resource was not found",
                            "code": "NOT_FOUND"
                        }
                    },
                    "project_not_found": {
                        "summary": "Project Not Found",
                        "value": {
                            "detail": "Project with ID 'project-123' not found",
                            "code": "PROJECT_NOT_FOUND"
                        }
                    }
                }
            }
        }
    },
    422: {
        "description": "Unprocessable Entity",
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Validation Error",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "email"],
                                    "msg": "value is not a valid email address",
                                    "type": "value_error.email"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "examples": {
                    "rate_limit_exceeded": {
                        "summary": "Rate Limit Exceeded",
                        "value": {
                            "detail": "Rate limit exceeded. Please try again later.",
                            "code": "RATE_LIMIT_EXCEEDED",
                            "retry_after": 60
                        }
                    }
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "examples": {
                    "server_error": {
                        "summary": "Internal Server Error",
                        "value": {
                            "detail": "An internal server error occurred",
                            "code": "INTERNAL_ERROR"
                        }
                    }
                }
            }
        }
    }
}


# Authentication examples
AUTH_EXAMPLES = {
    "register_student": {
        "summary": "Register Student Account",
        "description": "Register a new student user account",
        "value": {
            "name": "Alice Johnson",
            "email": "alice.johnson@university.edu",
            "password": "SecurePassword123!",
            "role": "student"
        }
    },
    "register_coordinator": {
        "summary": "Register Coordinator Account",
        "description": "Register a new coordinator user account",
        "value": {
            "name": "Prof. John Smith",
            "email": "j.smith@university.edu",
            "password": "SecurePassword123!",
            "role": "coordinator"
        }
    },
    "login": {
        "summary": "User Login",
        "description": "Login with email and password",
        "value": {
            "email": "alice.johnson@university.edu",
            "password": "SecurePassword123!"
        }
    },
    "auth_response": {
        "summary": "Authentication Response",
        "description": "Successful authentication response",
        "value": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "user-123",
                "name": "Alice Johnson",
                "email": "alice.johnson@university.edu",
                "role": "student",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    }
}


# Project examples
PROJECT_EXAMPLES = {
    "create_project": {
        "summary": "Create New Project",
        "description": "Create a new collaborative project",
        "value": {
            "name": "Machine Learning Project",
            "description": "A collaborative ML project for CS 4641 course focusing on neural networks and deep learning applications."
        }
    },
    "project_response": {
        "summary": "Project Response",
        "description": "Project data response",
        "value": {
            "id": "project-123",
            "name": "Machine Learning Project",
            "description": "A collaborative ML project for CS 4641 course",
            "owner_id": "user-123",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "members": [
                {
                    "user_id": "user-123",
                    "name": "Alice Johnson",
                    "email": "alice@university.edu",
                    "role": "owner",
                    "joined_at": "2024-01-01T00:00:00Z"
                }
            ],
            "repositories": [],
            "activity_count": 0
        }
    },
    "invite_member": {
        "summary": "Invite Team Member",
        "description": "Invite a new member to the project",
        "value": {
            "email": "bob.smith@university.edu",
            "role": "developer"
        }
    }
}


# Repository examples
REPOSITORY_EXAMPLES = {
    "connect_github": {
        "summary": "Connect GitHub Repository",
        "description": "Connect a GitHub repository to the project",
        "value": {
            "provider": "github",
            "url": "https://github.com/alice/ml-project",
            "access_token": "ghp_xxxxxxxxxxxxxxxxxxxx",
            "branch": "main"
        }
    },
    "connect_gitlab": {
        "summary": "Connect GitLab Repository",
        "description": "Connect a GitLab repository to the project",
        "value": {
            "provider": "gitlab",
            "url": "https://gitlab.com/alice/ml-project",
            "access_token": "glpat-xxxxxxxxxxxxxxxxxxxx",
            "branch": "main"
        }
    },
    "repository_response": {
        "summary": "Repository Response",
        "description": "Connected repository information",
        "value": {
            "id": "repo-123",
            "name": "ml-project",
            "url": "https://github.com/alice/ml-project",
            "provider": "github",
            "branch": "main",
            "webhook_id": "webhook-456",
            "auto_deploy": True,
            "last_deployment": {
                "id": "deploy-789",
                "status": "success",
                "url": "https://ml-project-staging.vercel.app",
                "created_at": "2024-01-01T12:00:00Z"
            },
            "created_at": "2024-01-01T00:00:00Z"
        }
    }
}


# Activity examples
ACTIVITY_EXAMPLES = {
    "track_coding": {
        "summary": "Track Coding Activity",
        "description": "Track coding activity on a specific file",
        "value": {
            "type": "coding",
            "location": "src/models/neural_network.py",
            "metadata": {
                "action": "edit",
                "lines_changed": 25,
                "function": "train_model",
                "language": "python"
            }
        }
    },
    "track_reviewing": {
        "summary": "Track Code Review Activity",
        "description": "Track code review activity",
        "value": {
            "type": "reviewing",
            "location": "src/components/Dashboard.tsx",
            "metadata": {
                "action": "review",
                "pull_request": "PR #15",
                "comments": 3
            }
        }
    },
    "activity_response": {
        "summary": "Activity Response",
        "description": "Activity tracking response",
        "value": {
            "id": "activity-123",
            "user_id": "user-123",
            "user_name": "Alice Johnson",
            "project_id": "project-123",
            "type": "coding",
            "location": "src/models/neural_network.py",
            "timestamp": "2024-01-01T12:00:00Z",
            "metadata": {
                "action": "edit",
                "lines_changed": 25,
                "function": "train_model"
            }
        }
    }
}


# Deployment examples
DEPLOYMENT_EXAMPLES = {
    "trigger_deployment": {
        "summary": "Trigger Deployment",
        "description": "Trigger a new deployment to staging environment",
        "value": {
            "repository_id": "repo-123",
            "branch": "main",
            "environment": "staging"
        }
    },
    "deployment_response": {
        "summary": "Deployment Response",
        "description": "Deployment status and information",
        "value": {
            "id": "deploy-123",
            "repository_id": "repo-123",
            "branch": "main",
            "commit_hash": "abc123def456",
            "environment": "staging",
            "status": "building",
            "progress": 45,
            "url": None,
            "logs": [
                {
                    "level": "info",
                    "message": "Starting build process",
                    "timestamp": "2024-01-01T12:00:00Z"
                },
                {
                    "level": "info", 
                    "message": "Installing dependencies",
                    "timestamp": "2024-01-01T12:01:00Z"
                }
            ],
            "started_at": "2024-01-01T12:00:00Z",
            "estimated_completion": "2024-01-01T12:05:00Z"
        }
    },
    "deployment_success": {
        "summary": "Successful Deployment",
        "description": "Completed deployment with preview URL",
        "value": {
            "id": "deploy-123",
            "status": "success",
            "url": "https://ml-project-abc123.staging.vercel.app",
            "duration": 180,
            "completed_at": "2024-01-01T12:03:00Z"
        }
    }
}


# Notification examples
NOTIFICATION_EXAMPLES = {
    "subscribe": {
        "summary": "Subscribe to Notifications",
        "description": "Subscribe to specific notification types",
        "value": {
            "events": ["deployment_success", "deployment_failure", "team_activity", "conflict_detected"],
            "channels": ["in_app", "email"]
        }
    },
    "notification_response": {
        "summary": "Notification",
        "description": "Notification message",
        "value": {
            "id": "notif-123",
            "type": "deployment_success",
            "title": "Deployment Completed",
            "message": "Your deployment to staging environment completed successfully",
            "data": {
                "deployment_id": "deploy-123",
                "url": "https://ml-project-abc123.staging.vercel.app",
                "project_name": "Machine Learning Project"
            },
            "read": False,
            "created_at": "2024-01-01T12:03:00Z"
        }
    }
}


# WebSocket examples
WEBSOCKET_EXAMPLES = {
    "presence_update": {
        "summary": "Presence Update Event",
        "description": "Real-time presence update",
        "value": {
            "type": "presence_update",
            "data": {
                "user_id": "user-123",
                "user_name": "Alice Johnson",
                "status": "online",
                "location": "src/models/neural_network.py",
                "project_id": "project-123"
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
    },
    "activity_notification": {
        "summary": "Activity Notification",
        "description": "Real-time activity notification",
        "value": {
            "type": "activity_notification",
            "data": {
                "activity_id": "activity-123",
                "user_name": "Bob Smith",
                "type": "coding",
                "location": "src/components/Dashboard.tsx",
                "message": "Bob Smith is working on Dashboard component"
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
    },
    "conflict_alert": {
        "summary": "Conflict Alert",
        "description": "Real-time conflict detection alert",
        "value": {
            "type": "conflict_detected",
            "data": {
                "conflict_id": "conflict-123",
                "type": "concurrent_work",
                "location": "src/utils/helpers.ts",
                "users": ["Alice Johnson", "Bob Smith"],
                "severity": "medium",
                "message": "Multiple team members are working on the same file"
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
    }
}


# Combine all examples
ALL_EXAMPLES = {
    "auth": AUTH_EXAMPLES,
    "projects": PROJECT_EXAMPLES,
    "repositories": REPOSITORY_EXAMPLES,
    "activities": ACTIVITY_EXAMPLES,
    "deployments": DEPLOYMENT_EXAMPLES,
    "notifications": NOTIFICATION_EXAMPLES,
    "websocket": WEBSOCKET_EXAMPLES
}