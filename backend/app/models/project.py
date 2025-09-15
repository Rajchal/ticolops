"""
Project and project member database models using SQLAlchemy.
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Boolean, Integer, Table, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base

# Some services expect to import Deployment from app.models.project
# Import Deployment from the deployment module and expose it below.
try:
    from app.models.deployment import Deployment as _DeploymentImported
except Exception:
    _DeploymentImported = None

# Note: project_members association table will be exposed from the
# declarative ProjectMember model below (project_members = ProjectMember.__table__)


class ProjectStatus(enum.Enum):
    """Project status enum (minimal for demo)."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProjectRole(enum.Enum):
    """Project role enum (minimal for demo)."""
    OWNER = "owner"
    COLLABORATOR = "collaborator"
    MEMBER = "member"


class ProjectMemberRole(enum.Enum):
    """Project member role enumeration for database."""
    OWNER = "owner"
    COORDINATOR = "coordinator"
    MEMBER = "member"


class Project(Base):
    """Project database model."""
    __tablename__ = "projects"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Status, settings, metadata and activity columns expected by services
    # Use plain VARCHAR for demo compatibility (avoids requiring Postgres enum type)
    status = Column(String(50), default=ProjectStatus.ACTIVE.value, nullable=False)
    settings = Column(JSON, default=dict, nullable=True)
    metadata_info = Column(JSON, default=dict, nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="project", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="project", cascade="all, delete-orphan")
    # Files belonging to this project (service code expects `files`)
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    # keep legacy name also available (avoid duplicate attribute binding warnings)
    # if other code expects `project_files`, access via the `files` attribute.
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan")
    presence_records = relationship("UserPresence", back_populates="project", cascade="all, delete-orphan")
    activity_summaries = relationship("ActivitySummary", back_populates="project", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")
    deployment_environments = relationship("DeploymentEnvironment", back_populates="project", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, owner_id={self.owner_id})>"


class ProjectMember(Base):
    """Project member database model."""
    __tablename__ = "project_members"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(
        String(50),
        default=ProjectMemberRole.MEMBER.value,
        nullable=False
    )
    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")

    def __repr__(self):
        return f"<ProjectMember(id={self.id}, project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"

    __table_args__ = {"extend_existing": True}


# Add relationships to User model
from app.models.user import User
User.owned_projects = relationship("Project", back_populates="owner")
User.project_memberships = relationship("ProjectMember", back_populates="user")
User.notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
User.notification_preferences = relationship("NotificationPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
User.notification_subscriptions = relationship("NotificationSubscription", back_populates="user", cascade="all, delete-orphan")
User.notification_digests = relationship("NotificationDigest", back_populates="user", cascade="all, delete-orphan")


class ProjectFile(Base):
    """Minimal ProjectFile model to satisfy imports used by services during demo."""
    __tablename__ = "project_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=False)
    size = Column(String(20), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    version = Column(String(50), default="1.0.0", nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    last_modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship back to project
    # NOTE: back_populates must match the relationship name on Project
    # Relationship back to project
    # NOTE: back_populates must match the relationship name on Project
    project = relationship("Project", back_populates="files", viewonly=True)


# Expose a table-like object for legacy code that expects `project_members` from models
project_members = ProjectMember.__table__

# Make enums available under the expected names
ProjectStatus = ProjectStatus
ProjectRole = ProjectRole

# Expose Deployment if available
Deployment = _DeploymentImported