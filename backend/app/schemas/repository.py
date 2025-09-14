"""Repository Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class GitProvider(str, Enum):
    """Git provider enumeration."""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class RepositoryConnectionRequest(BaseModel):
    """Schema for repository connection request."""
    provider: GitProvider
    repository_url: str = Field(..., min_length=1, description="Repository URL")
    access_token: str = Field(..., min_length=1, description="Git provider access token")
    branch: str = Field("main", description="Branch to track")
    deployment_config: Optional[Dict[str, Any]] = Field(
        default={
            "auto_deploy": True,
            "build_command": "",
            "output_directory": "",
            "environment_variables": {}
        },
        description="Deployment configuration"
    )
    
    @validator('repository_url')
    def validate_repository_url(cls, v):
        """Validate repository URL format."""
        if not any(domain in v.lower() for domain in ['github.com', 'gitlab.com', 'bitbucket.org']):
            raise ValueError('Repository URL must be from a supported Git provider')
        return v


class RepositoryValidationRequest(BaseModel):
    """Schema for repository validation request."""
    provider: GitProvider
    repository_url: str = Field(..., min_length=1)
    access_token: str = Field(..., min_length=1)


class RepositoryConfigUpdate(BaseModel):
    """Schema for repository configuration updates."""
    branch: Optional[str] = None
    auto_deploy: Optional[bool] = None
    build_command: Optional[str] = None
    output_directory: Optional[str] = None
    environment_variables: Optional[Dict[str, str]] = None


class DeploymentConfig(BaseModel):
    """Schema for deployment configuration."""
    auto_deploy: bool = True
    build_command: str = ""
    output_directory: str = ""
    environment_variables: Dict[str, str] = {}


class Repository(BaseModel):
    """Complete repository schema for responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    project_id: str
    name: str
    url: str
    provider: GitProvider
    branch: str
    webhook_id: Optional[str] = None
    is_active: bool
    deployment_config: DeploymentConfig
    created_at: datetime
    updated_at: datetime


class RepositoryInfo(BaseModel):
    """Extended repository information schema."""
    id: str
    name: str
    url: str
    provider: GitProvider
    branch: str
    is_active: bool
    deployment_config: DeploymentConfig
    created_at: datetime
    updated_at: datetime
    owner: str
    repo_name: str


class GitUser(BaseModel):
    """Git provider user information."""
    username: str
    name: Optional[str] = None
    email: Optional[str] = None


class GitRepository(BaseModel):
    """Git provider repository information."""
    name: str
    full_name: str
    description: Optional[str] = None
    default_branch: str
    private: bool
    language: Optional[str] = None


class RepositoryPermissions(BaseModel):
    """Repository permissions."""
    read: bool
    write: bool
    admin: bool


class RepositoryValidationResult(BaseModel):
    """Repository validation result."""
    valid: bool
    user: Optional[GitUser] = None
    repository: Optional[GitRepository] = None
    branches: Optional[List[str]] = None
    permissions: Optional[RepositoryPermissions] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class GitCommit(BaseModel):
    """Git commit information."""
    sha: str
    message: str
    author: Dict[str, str]  # name, email
    date: str
    url: str


class GitBranch(BaseModel):
    """Git branch information."""
    name: str
    commit_sha: str
    protected: bool = False


class UserRepository(BaseModel):
    """User's repository from Git provider."""
    id: int
    name: str
    full_name: str
    url: str
    clone_url: str
    default_branch: str
    private: bool
    description: Optional[str] = None
    language: Optional[str] = None
    updated_at: str


class RepositoryStats(BaseModel):
    """Repository statistics."""
    total_repositories: int
    repositories_by_provider: Dict[str, int]
    active_repositories: int
    repositories_with_webhooks: int
    recent_connections: List[Dict[str, Any]]


class WebhookEvent(BaseModel):
    """Webhook event data."""
    event_type: str  # push, pull_request, etc.
    repository: Dict[str, Any]
    commits: Optional[List[Dict[str, Any]]] = None
    pull_request: Optional[Dict[str, Any]] = None
    sender: Dict[str, Any]
    timestamp: datetime


class RepositoryActivity(BaseModel):
    """Repository activity summary."""
    repository_id: str
    recent_commits: List[GitCommit]
    active_branches: List[str]
    last_push: Optional[datetime] = None
    commit_frequency: Dict[str, int]  # commits per day/week
    contributors: List[Dict[str, Any]]


class RepositoryHealth(BaseModel):
    """Repository health check."""
    repository_id: str
    status: str  # healthy, warning, error
    issues: List[str]
    last_sync: Optional[datetime] = None
    webhook_status: str  # active, inactive, error
    deployment_status: str  # ready, building, deployed, failed


class RepositoryFilter(BaseModel):
    """Repository filtering options."""
    provider: Optional[GitProvider] = None
    is_active: Optional[bool] = None
    has_webhook: Optional[bool] = None
    branch: Optional[str] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class RepositorySearchResult(BaseModel):
    """Repository search result."""
    repositories: List[Repository]
    total_count: int
    has_more: bool