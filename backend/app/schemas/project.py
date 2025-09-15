from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import enum


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProjectRole(str, enum.Enum):
    OWNER = "owner"
    COLLABORATOR = "collaborator"
    MEMBER = "member"


class FileType(str, enum.Enum):
    CODE = "code"
    TEXT = "text"
    BINARY = "binary"


class DeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Environment(BaseModel):
    name: str
    domain: Optional[str] = None


class ProjectSettings(BaseModel):
    key_values: Dict[str, Any] = Field(default_factory=dict)


class ProjectFile(BaseModel):
    id: Optional[str]
    project_id: Optional[str]
    name: Optional[str]
    path: Optional[str]
    content: Optional[str]
    file_type: Optional[FileType]
    size: Optional[str]
    is_deleted: Optional[bool]
    version: Optional[str]
    created_by: Optional[str]


class ProjectFileCreate(BaseModel):
    name: str
    path: str
    content: Optional[str] = None
    file_type: FileType = FileType.CODE


class ProjectFileUpdate(BaseModel):
    name: Optional[str]
    path: Optional[str]
    content: Optional[str]
    file_type: Optional[FileType]


class Deployment(BaseModel):
    id: Optional[str]
    project_id: Optional[str]
    commit_sha: Optional[str]
    branch: Optional[str]
    status: Optional[DeploymentStatus]


class DeploymentCreate(BaseModel):
    repository_id: str
    project_id: str
    commit_sha: str
    branch: str


class DeploymentUpdate(BaseModel):
    status: Optional[DeploymentStatus]


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    settings: Optional[ProjectSettings] = None
    metadata_info: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    status: Optional[ProjectStatus]
    settings: Optional[ProjectSettings]
    metadata_info: Optional[Dict[str, Any]]


class Project(BaseModel):
    id: Optional[str]
    name: str
    description: Optional[str]
    status: ProjectStatus
    owner_id: Optional[str]
    settings: Optional[ProjectSettings]
    metadata_info: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]


class ProjectMember(BaseModel):
    user_id: str
    name: str
    email: str
    role: ProjectRole
    joined_at: Optional[str]
    invited_by: Optional[str]


class ProjectInvitation(BaseModel):
    email: str
    role: ProjectRole


class ProjectStats(BaseModel):
    total_files: int = 0
    total_size: str = "0"
    last_modified: Optional[str]
    active_collaborators: int = 0
    total_deployments: int = 0
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


class BulkFileOperation(BaseModel):
    operation: str
    file_ids: List[str]
    target_path: Optional[str]


class DeploymentConfig(BaseModel):
    build_command: Optional[str]
    output_directory: Optional[str]
    environment_variables: Optional[Dict[str, Any]]
