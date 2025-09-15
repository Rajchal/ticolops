"""
API Examples for OpenAPI documentation
"""

# Authentication Examples
AUTH_EXAMPLES = {
    "register": {
        "summary": "Register a new user",
        "description": "Create a new user account with email and password",
        "value": {
            "name": "John Doe",
            "email": "john.doe@university.edu",
            "password": "SecurePassword123!",
            "role": "student"
        }
    },
    "login": {
        "summary": "User login",
        "description": "Authenticate user and receive access token",
        "value": {
            "email": "john.doe@university.edu",
            "password": "SecurePassword123!"
        }
    },
    "login_response": {
        "summary": "Successful login response",
        "description": "JWT tokens and user information",
        "value": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "user-123",
                "name": "John Doe",
                "email": "john.doe@university.edu",
                "role": "student",
                "status": "active"
            }
        }
    }
}

# Project Examples
PROJECT_EXAMPLES = {
    "create_project": {
        "summary": "Create a new project",
        "description": "Create a collaborative project for team development",
        "value": {
            "name": "Web Development Project",
            "description": "A full-stack web application using React and Node.js",
            "visibility": "private",
            "settings": {
                "auto_deploy": True,
                "notifications_enabled": True,
                "conflict_detection": True
            }
        }
    },
    "project_response": {
        "summary": "Project details",
        "description": "Complete project information with metadata",
        "value": {
            "id": "project-123",
            "name": "Web Development Project",
            "description": "A full-stack web application using React and Node.js",
            "owner_id": "user-123",
            "visibility": "private",
            "status": "active",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "member_count": 4,
            "repository_count": 2,
            "settings": {
                "auto_deploy": True,
                "notifications_enabled": True,
                "conflict_detection": True
            }
        }
    },
    "invite_member": {
        "summary": "Invite team member",
        "description": "Invite a user to join the project team",
        "value": {
            "email": "teammate@university.edu",
            "role": "developer",
            "message": "Welcome to our project! Looking forward to collaborating."
        }
    }
}

# Repository Examples
REPOSITORY_EXAMPLES = {
    "connect_repository": {
        "summary": "Connect Git repository",
        "description": "Connect a GitHub/GitLab repository to the project",
        "value": {
            "provider": "github",
            "url": "https://github.com/username/awesome-project",
            "access_token": "ghp_xxxxxxxxxxxxxxxxxxxx",
            "branch": "main",
            "auto_deploy": True,
            "deployment_config": {
                "build_command": "npm run build",
                "output_directory": "dist",
                "environment_variables": {
                    "NODE_ENV": "production"
                }
            }
        }
    },
    "repository_response": {
        "summary": "Repository information",
        "description": "Connected repository details and status",
        "value": {
            "id": "repo-123",
            "project_id": "project-123",
            "name": "awesome-project",
            "provider": "github",
            "url": "https://github.com/username/awesome-project",
            "branch": "main",
            "last_commit": {
                "hash": "abc123def456",
                "message": "Add user authentication",
                "author": "John Doe",
                "timestamp": "2024-01-15T14:20:00Z"
            },
            "webhook_configured": True,
            "auto_deploy": True,
            "status": "connected",
            "connected_at": "2024-01-15T10:30:00Z"
        }
    }
}

# Activity Examples
ACTIVITY_EXAMPLES = {
    "create_activity": {
        "summary": "Log user activity",
        "description": "Record user activity for real-time collaboration tracking",
        "value": {
            "type": "coding",
            "location": "src/components/UserProfile.tsx",
            "metadata": {
                "action": "editing",
                "lines_changed": 15,
                "language": "typescript"
            }
        }
    },
    "activity_response": {
        "summary": "Activity details",
        "description": "Recorded activity with user and timestamp information",
        "value": {
            "id": "activity-123",
            "user_id": "user-123",
            "user_name": "John Doe",
            "project_id": "project-123",
            "type": "coding",
            "location": "src/components/UserProfile.tsx",
            "timestamp": "2024-01-15T14:25:30Z",
            "metadata": {
                "action": "editing",
                "lines_changed": 15,
                "language": "typescript"
            }
        }
    },
    "activity_feed": {
        "summary": "Project activity feed",
        "description": "Recent activities from all team members",
        "value": [
            {
                "id": "activity-123",
                "user_name": "John Doe",
                "type": "coding",
                "location": "src/components/UserProfile.tsx",
                "timestamp": "2024-01-15T14:25:30Z"
            },
            {
                "id": "activity-124",
                "user_name": "Jane Smith",
                "type": "reviewing",
                "location": "Pull Request #15",
                "timestamp": "2024-01-15T14:20:15Z"
            },
            {
                "id": "activity-125",
                "user_name": "Bob Johnson",
                "type": "testing",
                "location": "tests/user.test.js",
                "timestamp": "2024-01-15T14:15:45Z"
            }
        ]
    }
}

# Deployment Examples
DEPLOYMENT_EXAMPLES = {
    "trigger_deployment": {
        "summary": "Trigger deployment",
        "description": "Start a new deployment for the specified branch",
        "value": {
            "repository_id": "repo-123",
            "branch": "main",
            "environment": "staging",
            "force_rebuild": False
        }
    },
    "deployment_response": {
        "summary": "Deployment status",
        "description": "Current deployment information and status",
        "value": {
            "id": "deploy-123",
            "repository_id": "repo-123",
            "project_id": "project-123",
            "branch": "main",
            "commit_hash": "abc123def456",
            "environment": "staging",
            "status": "building",
            "triggered_by": "user-123",
            "started_at": "2024-01-15T14:30:00Z",
            "estimated_completion": "2024-01-15T14:35:00Z",
            "build_logs": [
                "Starting build process...",
                "Installing dependencies...",
                "Running tests..."
            ]
        }
    },
    "deployment_success": {
        "summary": "Successful deployment",
        "description": "Completed deployment with preview URL",
        "value": {
            "id": "deploy-123",
            "status": "success",
            "url": "https://deploy-123.staging.ticolops.com",
            "completed_at": "2024-01-15T14:34:22Z",
            "duration": 262,
            "build_logs": [
                "Build completed successfully",
                "Tests passed: 45/45",
                "Deployment URL: https://deploy-123.staging.ticolops.com"
            ]
        }
    }
}

# Notification Examples
NOTIFICATION_EXAMPLES = {
    "notification": {
        "summary": "Notification object",
        "description": "Real-time notification sent to users",
        "value": {
            "id": "notif-123",
            "user_id": "user-123",
            "title": "Deployment Successful",
            "message": "Your deployment to staging environment is now live",
            "type": "success",
            "category": "deployment",
            "data": {
                "deployment_id": "deploy-123",
                "url": "https://deploy-123.staging.ticolops.com"
            },
            "read": False,
            "created_at": "2024-01-15T14:34:30Z"
        }
    },
    "notification_preferences": {
        "summary": "Notification preferences",
        "description": "User's notification settings and preferences",
        "value": {
            "email_notifications": True,
            "push_notifications": True,
            "deployment_notifications": True,
            "mention_notifications": True,
            "conflict_notifications": True,
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00",
                "timezone": "UTC"
            },
            "channels": {
                "email": "john.doe@university.edu",
                "slack": "@johndoe",
                "discord": "JohnDoe#1234"
            }
        }
    }
}

# WebSocket Examples
WEBSOCKET_EXAMPLES = {
    "presence_update": {
        "summary": "User presence update",
        "description": "Real-time user presence and status information",
        "value": {
            "type": "presence_update",
            "data": {
                "user_id": "user-123",
                "user_name": "John Doe",
                "status": "online",
                "location": "src/components/Dashboard.tsx",
                "last_activity": "2024-01-15T14:35:00Z"
            }
        }
    },
    "conflict_detected": {
        "summary": "Conflict detection",
        "description": "Real-time conflict detection between team members",
        "value": {
            "type": "conflict_detected",
            "data": {
                "location": "src/components/UserProfile.tsx",
                "users": ["user-123", "user-456"],
                "severity": "medium",
                "suggestions": [
                    "Consider working on different sections of the file",
                    "Coordinate through team chat before making changes"
                ]
            }
        }
    },
    "deployment_update": {
        "summary": "Deployment status update",
        "description": "Real-time deployment progress updates",
        "value": {
            "type": "deployment_update",
            "data": {
                "deployment_id": "deploy-123",
                "status": "building",
                "progress": 65,
                "current_step": "Running tests",
                "logs": ["Test suite: Authentication - PASSED"]
            }
        }
    }
}

# Error Examples
ERROR_EXAMPLES = {
    "validation_error": {
        "summary": "Validation error",
        "description": "Request validation failed",
        "value": {
            "detail": [
                {
                    "loc": ["body", "email"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["body", "password"],
                    "msg": "ensure this value has at least 8 characters",
                    "type": "value_error.any_str.min_length"
                }
            ]
        }
    },
    "authentication_error": {
        "summary": "Authentication error",
        "description": "Invalid or missing authentication credentials",
        "value": {
            "detail": "Invalid authentication credentials",
            "error_code": "INVALID_CREDENTIALS",
            "timestamp": "2024-01-15T14:35:00Z"
        }
    },
    "permission_error": {
        "summary": "Permission denied",
        "description": "User lacks required permissions for this action",
        "value": {
            "detail": "You don't have permission to perform this action",
            "error_code": "INSUFFICIENT_PERMISSIONS",
            "required_role": "maintainer",
            "current_role": "developer"
        }
    },
    "not_found_error": {
        "summary": "Resource not found",
        "description": "The requested resource could not be found",
        "value": {
            "detail": "Project not found",
            "error_code": "RESOURCE_NOT_FOUND",
            "resource_type": "project",
            "resource_id": "project-123"
        }
    }
}