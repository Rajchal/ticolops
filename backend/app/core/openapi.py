"""
OpenAPI documentation configuration and examples.
"""

from typing import Dict, Any
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with comprehensive examples and documentation.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Ticolops API",
        version="1.0.0",
        description="""
        ## Ticolops - Track. Collaborate. Deploy. Succeed.
        
        A comprehensive real-time collaborative platform designed for student project management 
        with integrated automated DevOps workflows.
        
        ### Key Features
        
        * **Real-time Collaboration**: Track team member activities and presence in real-time
        * **Conflict Detection**: Automatically detect and resolve collaboration conflicts
        * **Automated DevOps**: Seamless repository integration with automated deployments
        * **Team Management**: Comprehensive project and team member management
        * **Activity Tracking**: Detailed activity logging and analytics
        * **Notification System**: Multi-channel notification delivery
        
        ### Authentication
        
        This API uses JWT (JSON Web Tokens) for authentication. Include the token in the 
        Authorization header as `Bearer <token>`.
        
        ### Rate Limiting
        
        API endpoints are rate-limited to ensure fair usage:
        - Authentication endpoints: 10 requests per minute
        - General API endpoints: 100 requests per minute
        - WebSocket connections: 5 concurrent connections per user
        
        ### WebSocket Support
        
        Real-time features are powered by WebSocket connections. Connect to `/ws/{project_id}` 
        for real-time updates including:
        - Team member presence updates
        - Activity notifications
        - Deployment status changes
        - Conflict alerts
        
        ### Error Handling
        
        The API uses standard HTTP status codes and returns detailed error information:
        - `400` - Bad Request: Invalid input data
        - `401` - Unauthorized: Authentication required
        - `403` - Forbidden: Insufficient permissions
        - `404` - Not Found: Resource not found
        - `422` - Unprocessable Entity: Validation error
        - `429` - Too Many Requests: Rate limit exceeded
        - `500` - Internal Server Error: Server error
        
        ### Pagination
        
        List endpoints support pagination with the following parameters:
        - `page`: Page number (default: 1)
        - `limit`: Items per page (default: 20, max: 100)
        - `sort_by`: Field to sort by
        - `order`: Sort order (`asc` or `desc`)
        """,
        routes=app.routes,
    )
    
    # Add comprehensive examples for common schemas
    openapi_schema["components"]["examples"] = {
        "UserRegistration": {
            "summary": "Student Registration",
            "description": "Example of student user registration",
            "value": {
                "name": "Jane Doe",
                "email": "jane.doe@university.edu",
                "password": "SecurePassword123!",
                "role": "student"
            }
        },
        "CoordinatorRegistration": {
            "summary": "Coordinator Registration", 
            "description": "Example of coordinator user registration",
            "value": {
                "name": "Prof. John Smith",
                "email": "j.smith@university.edu",
                "password": "SecurePassword123!",
                "role": "coordinator"
            }
        },
        "UserLogin": {
            "summary": "User Login",
            "description": "Example login credentials",
            "value": {
                "email": "jane.doe@university.edu",
                "password": "SecurePassword123!"
            }
        },
        "ProjectCreation": {
            "summary": "Create Project",
            "description": "Example project creation",
            "value": {
                "name": "Web Development Project",
                "description": "A collaborative web application built with React and Node.js"
            }
        },
        "RepositoryConnection": {
            "summary": "Connect Repository",
            "description": "Example repository connection",
            "value": {
                "provider": "github",
                "url": "https://github.com/username/project-repo",
                "access_token": "ghp_xxxxxxxxxxxxxxxxxxxx",
                "branch": "main"
            }
        },
        "ActivityTracking": {
            "summary": "Track Activity",
            "description": "Example activity tracking",
            "value": {
                "type": "coding",
                "location": "src/components/UserProfile.tsx",
                "metadata": {
                    "action": "edit",
                    "lines_changed": 25,
                    "function": "updateUserProfile"
                }
            }
        },
        "DeploymentTrigger": {
            "summary": "Trigger Deployment",
            "description": "Example deployment trigger",
            "value": {
                "repository_id": "repo-123",
                "branch": "main",
                "environment": "staging"
            }
        },
        "WebhookPayload": {
            "summary": "GitHub Webhook",
            "description": "Example GitHub push webhook payload",
            "value": {
                "ref": "refs/heads/main",
                "head_commit": {
                    "id": "abc123def456",
                    "message": "Add user authentication feature",
                    "author": {
                        "name": "Jane Doe",
                        "email": "jane.doe@university.edu"
                    }
                },
                "repository": {
                    "full_name": "username/project-repo",
                    "clone_url": "https://github.com/username/project-repo.git"
                }
            }
        }
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from login endpoint"
        }
    }
    
    # Add common response schemas
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "detail": {
                "type": "string",
                "description": "Error message"
            },
            "code": {
                "type": "string", 
                "description": "Error code"
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "Error timestamp"
            }
        },
        "example": {
            "detail": "Invalid credentials provided",
            "code": "INVALID_CREDENTIALS",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    }
    
    openapi_schema["components"]["schemas"]["PaginatedResponse"] = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of items"
            },
            "total": {
                "type": "integer",
                "description": "Total number of items"
            },
            "page": {
                "type": "integer",
                "description": "Current page number"
            },
            "limit": {
                "type": "integer", 
                "description": "Items per page"
            },
            "pages": {
                "type": "integer",
                "description": "Total number of pages"
            }
        }
    }
    
    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "users",
            "description": "User profile and management endpoints"
        },
        {
            "name": "projects",
            "description": "Project creation and management endpoints"
        },
        {
            "name": "repository",
            "description": "Repository integration and management endpoints"
        },
        {
            "name": "deployment",
            "description": "Deployment pipeline and monitoring endpoints"
        },
        {
            "name": "activity",
            "description": "Activity tracking and analytics endpoints"
        },
        {
            "name": "collaboration",
            "description": "Real-time collaboration and conflict detection endpoints"
        },
        {
            "name": "presence",
            "description": "User presence and status tracking endpoints"
        },
        {
            "name": "notifications",
            "description": "Notification management and delivery endpoints"
        },
        {
            "name": "webhooks",
            "description": "Webhook handling for external integrations"
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time communication"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Response examples for common HTTP status codes
RESPONSE_EXAMPLES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid input data provided",
                    "code": "BAD_REQUEST"
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Authentication credentials were not provided or are invalid",
                    "code": "UNAUTHORIZED"
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "detail": "You do not have permission to perform this action",
                    "code": "FORBIDDEN"
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "detail": "The requested resource was not found",
                    "code": "NOT_FOUND"
                }
            }
        }
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
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
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded. Please try again later.",
                    "code": "RATE_LIMIT_EXCEEDED"
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "An internal server error occurred",
                    "code": "INTERNAL_ERROR"
                }
            }
        }
    }
}