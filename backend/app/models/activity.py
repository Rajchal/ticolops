"""Activity tracking database models using SQLAlchemy."""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class ActivityType(enum.Enum):
    """Activity type enumeration for database."""
    # File operations
    FILE_CREATED = "file_created"
    FILE_UPDATED = "file_updated"
    FILE_DELETED = "file_deleted"
    FILE_RESTORED = "file_restored"
    FILE_MOVED = "file_moved"
    
    # Project operations
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    
    # Member operations
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    MEMBER_INVITED = "member_invited"
    
    # Collaboration activities
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"
    MENTION_CREATED = "mention_created"
    
    # Development activities
    CODING = "coding"
    REVIEWING = "reviewing"
    TESTING = "testing"
    DOCUMENTING = "documenting"
    DEBUGGING = "debugging"
    
    # Deployment activities
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_SUCCESS = "deployment_success"
    DEPLOYMENT_FAILED = "deployment_failed"
    
    # Repository activities
    REPOSITORY_CONNECTED = "repository_connected"
    REPOSITORY_DISCONNECTED = "repository_disconnected"
    COMMIT_PUSHED = "commit_pushed"
    BRANCH_CREATED = "branch_created"
    BRANCH_MERGED = "branch_merged"
    
    # Settings and configuration
    SETTINGS_UPDATED = "settings_updated"
    TEMPLATE_APPLIED = "template_applied"
    
    # User presence
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    USER_AWAY = "user_away"
    USER_ACTIVE = "user_active"


class ActivityPriority(enum.Enum):
    """Activity priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Activity(Base):
    """Activity tracking database model."""
    __tablename__ = "activities"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Core activity information
    type = Column(
        String(50),
        nullable=False,
        index=True
    )
    title = Column(
        String(200),
        nullable=False
    )
    description = Column(
        Text,
        nullable=True
    )
    
    # User and project context
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        index=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id'),
        nullable=True,
        index=True
    )
    
    # Location and context information
    location = Column(
        String(500),
        nullable=True,
        index=True
    )  # File path, component name, or general location
    
    # Additional metadata
    metadata = Column(
        JSONB,
        default={},
        nullable=False
    )
    
    # Activity properties
    priority = Column(
        String(20),
        default=ActivityPriority.MEDIUM.value,
        nullable=False
    )
    duration_seconds = Column(
        String(20),
        nullable=True
    )  # Duration of the activity in seconds (as string for flexibility)
    
    # Related entities
    related_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey('project_files.id'),
        nullable=True
    )
    related_deployment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('deployments.id'),
        nullable=True
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    ended_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    user = relationship("User", back_populates="activities")
    project = relationship("Project", back_populates="activities")
    related_file = relationship("ProjectFile", foreign_keys=[related_file_id])
    related_deployment = relationship("Deployment", foreign_keys=[related_deployment_id])

    def __repr__(self):
        return f"<Activity(id={self.id}, type={self.type}, user_id={self.user_id})>"


class UserPresence(Base):
    """User presence tracking for real-time collaboration."""
    __tablename__ = "user_presence"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        index=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id'),
        nullable=True,
        index=True
    )
    
    # Presence information
    status = Column(
        String(20),
        nullable=False,
        default="offline"
    )  # online, away, offline, active
    
    current_location = Column(
        String(500),
        nullable=True
    )  # Current file or component being worked on
    
    current_activity = Column(
        String(50),
        nullable=True
    )  # Current activity type
    
    # Session information
    session_id = Column(
        String(100),
        nullable=True,
        index=True
    )
    ip_address = Column(
        String(45),
        nullable=True
    )
    user_agent = Column(
        Text,
        nullable=True
    )
    
    # Timestamps
    last_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    session_started = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_activity = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Additional context
    metadata = Column(
        JSONB,
        default={},
        nullable=False
    )
    
    # Relationships
    user = relationship("User", back_populates="presence_records")
    project = relationship("Project", back_populates="presence_records")

    def __repr__(self):
        return f"<UserPresence(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ActivitySummary(Base):
    """Daily activity summaries for performance optimization."""
    __tablename__ = "activity_summaries"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        index=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id'),
        nullable=True,
        index=True
    )
    
    # Summary date
    summary_date = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Activity counts by type
    activity_counts = Column(
        JSONB,
        default={},
        nullable=False
    )  # {"file_created": 5, "file_updated": 12, ...}
    
    # Time tracking
    total_active_time_seconds = Column(
        String(20),
        nullable=False,
        default="0"
    )
    first_activity = Column(
        DateTime(timezone=True),
        nullable=True
    )
    last_activity = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Location tracking
    locations_worked = Column(
        JSONB,
        default=[],
        nullable=False
    )  # List of files/components worked on
    
    # Collaboration metrics
    collaborations_count = Column(
        String(10),
        nullable=False,
        default="0"
    )
    conflicts_detected = Column(
        String(10),
        nullable=False,
        default="0"
    )
    
    # Timestamps
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
    user = relationship("User", back_populates="activity_summaries")
    project = relationship("Project", back_populates="activity_summaries")

    def __repr__(self):
        return f"<ActivitySummary(id={self.id}, user_id={self.user_id}, date={self.summary_date})>"


# Create indexes for better query performance
Index('idx_activities_user_project_created', Activity.user_id, Activity.project_id, Activity.created_at)
Index('idx_activities_type_created', Activity.type, Activity.created_at)
Index('idx_activities_location_created', Activity.location, Activity.created_at)
Index('idx_user_presence_user_project', UserPresence.user_id, UserPresence.project_id)
Index('idx_user_presence_status_last_seen', UserPresence.status, UserPresence.last_seen)
Index('idx_activity_summaries_user_date', ActivitySummary.user_id, ActivitySummary.summary_date)