"""Pydantic schemas for deployment-related data structures."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.deployment import DeploymentStatus, DeploymentTrigger, ProjectType


class DeploymentBase(BaseModel):
    """Base deployment schema."""
    commit_sha: str = Field(..., description="Git commit SHA")
    branch: str = Field(..., description="Git branch name")
    trigger: DeploymentTrigger = Field(DeploymentTrigger.PUSH, description="Deployment trigger")
    project_type: ProjectType = Field(ProjectType.UNKNOWN, description="Detected project type")
    
    @validator('commit_sha')
    def validate_commit_sha(cls, v):
        """Validate commit SHA format."""
        if not v or len(v) < 7:
            raise ValueError("Commit SHA must be at least 7 characters")
        return v.lower()
    
    @validator('branch')
    def validate_branch(cls, v):
        """Validate branch name."""
        if not v or not v.strip():
            raise ValueError("Branch name cannot be empty")
        return v.strip()


class DeploymentCreate(DeploymentBase):
    """Schema for creating a new deployment."""
    repository_id: str = Field(..., description="Repository ID")
    build_config: Optional[Dict[str, Any]] = Field(None, description="Build configuration")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    
    class Config:
        schema_extra = {
            "example": {
                "repository_id": "123e4567-e89b-12d3-a456-426614174000",
                "commit_sha": "abc123def456",
                "branch": "main",
                "trigger": "push",
                "project_type": "react",
                "build_config": {
                    "build_command": "npm run build",
                    "output_directory": "dist",
                    "install_command": "npm install"
                },
                "environment_variables": {
                    "NODE_ENV": "production",
                    "API_URL": "https://api.example.com"
                }
            }
        }


class DeploymentUpdate(BaseModel):
    """Schema for updating deployment status and metadata."""
    status: Optional[DeploymentStatus] = Field(None, description="Deployment status")
    preview_url: Optional[str] = Field(None, description="Preview URL")
    build_logs: Optional[str] = Field(None, description="Build logs")
    deployment_logs: Optional[str] = Field(None, description="Deployment logs")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    @validator('preview_url')
    def validate_preview_url(cls, v):
        """Validate preview URL format."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Preview URL must start with http:// or https://")
        return v


class Deployment(DeploymentBase):
    """Complete deployment schema."""
    id: str = Field(..., description="Deployment ID")
    repository_id: str = Field(..., description="Repository ID")
    project_id: str = Field(..., description="Project ID")
    status: DeploymentStatus = Field(..., description="Current deployment status")
    
    # Build and deployment details
    build_config: Optional[Dict[str, Any]] = Field(None, description="Build configuration")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    
    # URLs and logs
    preview_url: Optional[str] = Field(None, description="Preview URL")
    build_logs: Optional[str] = Field(None, description="Build logs")
    deployment_logs: Optional[str] = Field(None, description="Deployment logs")
    error_message: Optional[str] = Field(None, description="Error message")
    
    # Timing information
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Performance metrics
    build_duration_seconds: Optional[int] = Field(None, description="Build duration in seconds")
    deployment_duration_seconds: Optional[int] = Field(None, description="Deployment duration in seconds")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "repository_id": "123e4567-e89b-12d3-a456-426614174001",
                "project_id": "123e4567-e89b-12d3-a456-426614174002",
                "commit_sha": "abc123def456",
                "branch": "main",
                "trigger": "push",
                "status": "success",
                "project_type": "react",
                "preview_url": "https://preview-abc123.example.com",
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:05:00Z",
                "build_duration_seconds": 120,
                "deployment_duration_seconds": 180
            }
        }


class DeploymentSummary(BaseModel):
    """Summary deployment information for lists."""
    id: str = Field(..., description="Deployment ID")
    commit_sha: str = Field(..., description="Git commit SHA")
    branch: str = Field(..., description="Git branch name")
    status: DeploymentStatus = Field(..., description="Deployment status")
    trigger: DeploymentTrigger = Field(..., description="Deployment trigger")
    preview_url: Optional[str] = Field(None, description="Preview URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        from_attributes = True


class DeploymentEnvironmentBase(BaseModel):
    """Base deployment environment schema."""
    name: str = Field(..., description="Environment name")
    description: Optional[str] = Field(None, description="Environment description")
    is_default: bool = Field(False, description="Whether this is the default environment")
    domain: Optional[str] = Field(None, description="Custom domain")
    subdomain_pattern: Optional[str] = Field(None, description="Subdomain pattern")
    build_command: Optional[str] = Field(None, description="Build command override")
    output_directory: Optional[str] = Field(None, description="Output directory override")
    auto_deploy_branches: Optional[List[str]] = Field(None, description="Branches to auto-deploy")
    require_approval: bool = Field(False, description="Whether deployments require approval")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate environment name."""
        if not v or not v.strip():
            raise ValueError("Environment name cannot be empty")
        return v.strip().lower()


class DeploymentEnvironmentCreate(DeploymentEnvironmentBase):
    """Schema for creating a deployment environment."""
    project_id: str = Field(..., description="Project ID")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")


class DeploymentEnvironment(DeploymentEnvironmentBase):
    """Complete deployment environment schema."""
    id: str = Field(..., description="Environment ID")
    project_id: str = Field(..., description="Project ID")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class BuildConfigurationBase(BaseModel):
    """Base build configuration schema."""
    project_type: ProjectType = Field(..., description="Project type")
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    build_command: str = Field(..., description="Build command")
    output_directory: str = Field(..., description="Output directory")
    install_command: Optional[str] = Field(None, description="Install command")
    
    @validator('build_command', 'output_directory')
    def validate_required_fields(cls, v):
        """Validate required fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class BuildConfiguration(BuildConfigurationBase):
    """Complete build configuration schema."""
    id: str = Field(..., description="Configuration ID")
    detection_files: Optional[List[str]] = Field(None, description="Detection files")
    detection_patterns: Optional[Dict[str, Any]] = Field(None, description="Detection patterns")
    default_env_vars: Optional[Dict[str, str]] = Field(None, description="Default environment variables")
    framework_version: Optional[str] = Field(None, description="Framework version")
    node_version: Optional[str] = Field(None, description="Node.js version")
    python_version: Optional[str] = Field(None, description="Python version")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class DeploymentTriggerRequest(BaseModel):
    """Schema for manually triggering a deployment."""
    repository_id: str = Field(..., description="Repository ID")
    branch: Optional[str] = Field(None, description="Branch to deploy (defaults to repository default)")
    commit_sha: Optional[str] = Field(None, description="Specific commit to deploy (defaults to latest)")
    environment_id: Optional[str] = Field(None, description="Target environment ID")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Override environment variables")
    
    class Config:
        schema_extra = {
            "example": {
                "repository_id": "123e4567-e89b-12d3-a456-426614174000",
                "branch": "main",
                "commit_sha": "abc123def456",
                "environment_variables": {
                    "NODE_ENV": "production"
                }
            }
        }


class DeploymentStats(BaseModel):
    """Deployment statistics schema."""
    total_deployments: int = Field(..., description="Total number of deployments")
    successful_deployments: int = Field(..., description="Number of successful deployments")
    failed_deployments: int = Field(..., description="Number of failed deployments")
    active_deployments: int = Field(..., description="Number of currently active deployments")
    average_build_time_seconds: Optional[float] = Field(None, description="Average build time")
    average_deployment_time_seconds: Optional[float] = Field(None, description="Average deployment time")
    deployments_by_status: Dict[str, int] = Field(..., description="Deployments grouped by status")
    deployments_by_trigger: Dict[str, int] = Field(..., description="Deployments grouped by trigger")
    recent_deployments: List[DeploymentSummary] = Field(..., description="Recent deployments")
    
    class Config:
        schema_extra = {
            "example": {
                "total_deployments": 150,
                "successful_deployments": 135,
                "failed_deployments": 15,
                "active_deployments": 2,
                "average_build_time_seconds": 120.5,
                "average_deployment_time_seconds": 45.2,
                "deployments_by_status": {
                    "success": 135,
                    "failed": 15,
                    "building": 1,
                    "deploying": 1
                },
                "deployments_by_trigger": {
                    "push": 140,
                    "manual": 10
                },
                "recent_deployments": []
            }
        }


class ProjectTypeDetectionResult(BaseModel):
    """Result of project type detection."""
    project_type: ProjectType = Field(..., description="Detected project type")
    confidence: float = Field(..., description="Detection confidence (0.0 to 1.0)")
    detected_files: List[str] = Field(..., description="Files that led to detection")
    suggested_config: BuildConfiguration = Field(..., description="Suggested build configuration")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "project_type": "react",
                "confidence": 0.95,
                "detected_files": ["package.json", "src/App.js", "public/index.html"],
                "suggested_config": {
                    "build_command": "npm run build",
                    "output_directory": "build",
                    "install_command": "npm install"
                }
            }
        }