"""Database models for deployment management."""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    BUILDING = "building"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentTrigger(str, Enum):
    """Deployment trigger types."""
    PUSH = "push"
    MANUAL = "manual"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"


class ProjectType(str, Enum):
    """Supported project types for deployment."""
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"
    STATIC = "static"
    NODE = "node"
    PYTHON = "python"
    DJANGO = "django"
    FLASK = "flask"
    FASTAPI = "fastapi"
    UNKNOWN = "unknown"


class Deployment(Base):
    """Deployment model for tracking deployment instances."""
    
    __tablename__ = "deployments"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    repository_id = Column(PostgresUUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Deployment metadata
    commit_sha = Column(String(40), nullable=False)
    branch = Column(String(255), nullable=False)
    trigger = Column(String(50), nullable=False, default=DeploymentTrigger.PUSH.value)
    status = Column(String(50), nullable=False, default=DeploymentStatus.PENDING.value)
    
    # Build and deployment configuration
    project_type = Column(String(50), nullable=False, default=ProjectType.UNKNOWN.value)
    build_config = Column(JSON, nullable=True)
    environment_variables = Column(JSON, nullable=True)
    
    # Deployment URLs and metadata
    preview_url = Column(String(500), nullable=True)
    build_logs = Column(Text, nullable=True)
    deployment_logs = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timing information
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Performance metrics
    build_duration_seconds = Column(Integer, nullable=True)
    deployment_duration_seconds = Column(Integer, nullable=True)
    
    # Relationships
    repository = relationship("Repository", back_populates="deployments")
    project = relationship("Project", back_populates="deployments")
    
    def __repr__(self):
        return f"<Deployment(id={self.id}, status={self.status}, commit={self.commit_sha[:8]})>"
    
    @property
    def is_active(self) -> bool:
        """Check if deployment is currently active (building or deploying)."""
        return self.status in [DeploymentStatus.PENDING, DeploymentStatus.QUEUED, 
                              DeploymentStatus.BUILDING, DeploymentStatus.DEPLOYING]
    
    @property
    def is_completed(self) -> bool:
        """Check if deployment is completed (success or failed)."""
        return self.status in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED, 
                              DeploymentStatus.CANCELLED]
    
    @property
    def total_duration_seconds(self) -> Optional[int]:
        """Calculate total deployment duration."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class DeploymentEnvironment(Base):
    """Deployment environment configuration."""
    
    __tablename__ = "deployment_environments"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Environment details
    name = Column(String(100), nullable=False)  # e.g., "production", "staging", "preview"
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Environment configuration
    domain = Column(String(255), nullable=True)
    subdomain_pattern = Column(String(255), nullable=True)  # e.g., "{branch}.{domain}"
    environment_variables = Column(JSON, nullable=True)
    build_command = Column(String(500), nullable=True)
    output_directory = Column(String(255), nullable=True)
    
    # Deployment settings
    auto_deploy_branches = Column(JSON, nullable=True)  # List of branches to auto-deploy
    require_approval = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="deployment_environments")
    
    def __repr__(self):
        return f"<DeploymentEnvironment(id={self.id}, name={self.name}, project_id={self.project_id})>"


class BuildConfiguration(Base):
    """Build configuration templates for different project types."""
    
    __tablename__ = "build_configurations"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Configuration details
    project_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Build settings
    build_command = Column(String(500), nullable=False)
    output_directory = Column(String(255), nullable=False)
    install_command = Column(String(500), nullable=True)
    
    # Detection patterns
    detection_files = Column(JSON, nullable=True)  # Files that indicate this project type
    detection_patterns = Column(JSON, nullable=True)  # Patterns in package.json, etc.
    
    # Default environment variables
    default_env_vars = Column(JSON, nullable=True)
    
    # Framework-specific settings
    framework_version = Column(String(50), nullable=True)
    node_version = Column(String(20), nullable=True)
    python_version = Column(String(20), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<BuildConfiguration(id={self.id}, type={self.project_type}, name={self.name})>"


class DeploymentHook(Base):
    """Deployment hooks for custom actions during deployment lifecycle."""
    
    __tablename__ = "deployment_hooks"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    deployment_id = Column(PostgresUUID(as_uuid=True), ForeignKey("deployments.id"), nullable=False)
    
    # Hook details
    hook_type = Column(String(50), nullable=False)  # pre_build, post_build, pre_deploy, post_deploy
    command = Column(Text, nullable=False)
    working_directory = Column(String(255), nullable=True)
    
    # Execution details
    executed = Column(Boolean, default=False, nullable=False)
    exit_code = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)
    error_output = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    deployment = relationship("Deployment", backref="hooks")
    
    def __repr__(self):
        return f"<DeploymentHook(id={self.id}, type={self.hook_type}, deployment_id={self.deployment_id})>"