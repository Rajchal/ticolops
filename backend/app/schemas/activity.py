"""Activity tracking Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ActivityType(str, Enum):
    """Activity type enumeration."""
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


class ActivityPriority(str, Enum):
    """Activity priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserPresenceStatus(str, Enum):
    """User presence status enumeration."""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"
    ACTIVE = "active"


class ActivityBase(BaseModel):
    """Base activity schema with common fields."""
    type: ActivityType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=500)
    priority: ActivityPriority = ActivityPriority.MEDIUM
    metadata: Optional[Dict[str, Any]] = None


class ActivityCreate(ActivityBase):
    """Schema for activity creation."""
    project_id: Optional[str] = None
    related_file_id: Optional[str] = None
    related_deployment_id: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class ActivityUpdate(BaseModel):
    """Schema for activity updates."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=500)
    priority: Optional[ActivityPriority] = None
    metadata: Optional[Dict[str, Any]] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class Activity(ActivityBase):
    """Complete activity schema for responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    project_id: Optional[str] = None
    related_file_id: Optional[str] = None
    related_deployment_id: Optional[str] = None
    duration_seconds: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Optional related data
    user_name: Optional[str] = None
    project_name: Optional[str] = None
    file_name: Optional[str] = None


class UserPresenceBase(BaseModel):
    """Base user presence schema."""
    status: UserPresenceStatus = UserPresenceStatus.OFFLINE
    current_location: Optional[str] = Field(None, max_length=500)
    current_activity: Optional[ActivityType] = None


class UserPresenceCreate(UserPresenceBase):
    """Schema for user presence creation."""
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UserPresenceUpdate(BaseModel):
    """Schema for user presence updates."""
    status: Optional[UserPresenceStatus] = None
    current_location: Optional[str] = Field(None, max_length=500)
    current_activity: Optional[ActivityType] = None
    metadata: Optional[Dict[str, Any]] = None


class UserPresence(UserPresenceBase):
    """Complete user presence schema for responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    last_seen: datetime
    session_started: datetime
    last_activity: datetime
    metadata: Dict[str, Any]
    
    # Optional related data
    user_name: Optional[str] = None
    project_name: Optional[str] = None


class ActivitySummaryBase(BaseModel):
    """Base activity summary schema."""
    summary_date: datetime
    activity_counts: Dict[str, int]
    total_active_time_seconds: int = 0
    locations_worked: List[str] = []
    collaborations_count: int = 0
    conflicts_detected: int = 0


class ActivitySummaryCreate(ActivitySummaryBase):
    """Schema for activity summary creation."""
    user_id: str
    project_id: Optional[str] = None
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class ActivitySummary(ActivitySummaryBase):
    """Complete activity summary schema for responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    project_id: Optional[str] = None
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Optional related data
    user_name: Optional[str] = None
    project_name: Optional[str] = None


class ActivityFilter(BaseModel):
    """Schema for activity filtering."""
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    activity_types: Optional[List[ActivityType]] = None
    location: Optional[str] = None
    priority: Optional[ActivityPriority] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class ActivityStats(BaseModel):
    """Schema for activity statistics."""
    total_activities: int
    activities_by_type: Dict[str, int]
    activities_by_priority: Dict[str, int]
    most_active_locations: List[Dict[str, Any]]
    activity_timeline: List[Dict[str, Any]]
    collaboration_metrics: Dict[str, Any]


class PresenceFilter(BaseModel):
    """Schema for presence filtering."""
    project_id: Optional[str] = None
    status: Optional[UserPresenceStatus] = None
    active_since: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=200)


class CollaborationOpportunity(BaseModel):
    """Schema for collaboration opportunities."""
    type: str  # "same_file", "related_files", "complementary_skills"
    users: List[str]  # User IDs
    location: str
    description: str
    priority: ActivityPriority
    metadata: Dict[str, Any]


class ConflictDetection(BaseModel):
    """Schema for conflict detection."""
    type: str  # "concurrent_editing", "overlapping_work", "resource_conflict"
    users: List[str]  # User IDs involved
    location: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    suggested_resolution: Optional[str] = None
    metadata: Dict[str, Any]


class ActivityBatch(BaseModel):
    """Schema for batch activity operations."""
    activities: List[ActivityCreate]
    batch_metadata: Optional[Dict[str, Any]] = None


class PresenceBroadcast(BaseModel):
    """Schema for presence broadcast messages."""
    user_id: str
    project_id: Optional[str] = None
    presence: UserPresence
    timestamp: datetime
    event_type: str  # "presence_update", "location_change", "activity_change"