"""Database models for notification system."""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationType(str, Enum):
    """Types of notifications in the system."""
    # Activity notifications
    USER_ACTIVITY = "user_activity"
    TEAM_PRESENCE = "team_presence"
    CONFLICT_DETECTED = "conflict_detected"
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"
    
    # Deployment notifications
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_SUCCESS = "deployment_success"
    DEPLOYMENT_FAILED = "deployment_failed"
    DEPLOYMENT_RECOVERED = "deployment_recovered"
    AUTO_RETRY_INITIATED = "auto_retry_initiated"
    ROLLBACK_COMPLETED = "rollback_completed"
    
    # Project notifications
    PROJECT_INVITATION = "project_invitation"
    PROJECT_MEMBER_JOINED = "project_member_joined"
    PROJECT_MEMBER_LEFT = "project_member_left"
    PROJECT_SETTINGS_CHANGED = "project_settings_changed"
    
    # Repository notifications
    REPOSITORY_CONNECTED = "repository_connected"
    REPOSITORY_DISCONNECTED = "repository_disconnected"
    WEBHOOK_CONFIGURED = "webhook_configured"
    
    # System notifications
    SYSTEM_MAINTENANCE = "system_maintenance"
    FEATURE_ANNOUNCEMENT = "feature_announcement"
    SECURITY_ALERT = "security_alert"
    
    # Mention notifications
    USER_MENTIONED = "user_mentioned"
    COMMENT_REPLY = "comment_reply"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    SMS = "sms"


class NotificationCategory(str, Enum):
    """High-level categories for notifications used by the trigger system."""
    ACTIVITY = "activity"
    COLLABORATION = "collaboration"
    DEPLOYMENT = "deployment"
    SYSTEM = "system"
    PROJECT = "project"
    REPOSITORY = "repository"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Notification(Base):
    """Notification model for storing notification data."""
    
    __tablename__ = "notifications"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    
    # Notification content
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional structured data
    
    # Notification metadata
    priority = Column(String(20), nullable=False, default=NotificationPriority.NORMAL.value)
    category = Column(String(50), nullable=True)  # Grouping category
    action_url = Column(String(500), nullable=True)  # URL for action button
    action_text = Column(String(100), nullable=True)  # Text for action button
    
    # Delivery tracking
    status = Column(String(20), nullable=False, default=NotificationStatus.PENDING.value)
    channels = Column(JSON, nullable=False, default=list)  # List of delivery channels
    delivery_attempts = Column(Integer, nullable=False, default=0)
    last_delivery_attempt = Column(DateTime, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_for = Column(DateTime, nullable=True)  # For scheduled notifications
    expires_at = Column(DateTime, nullable=True)  # Expiration time
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    project = relationship("Project", back_populates="notifications")
    delivery_logs = relationship("NotificationDeliveryLog", back_populates="notification", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, user_id={self.user_id})>"
    
    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled for future delivery."""
        if not self.scheduled_for:
            return False
        return datetime.utcnow() < self.scheduled_for


class NotificationPreferences(Base):
    """User notification preferences model."""
    
    __tablename__ = "notification_preferences"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    # Global notification settings
    enabled = Column(Boolean, nullable=False, default=True)
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(5), nullable=True)  # Format: "22:00"
    quiet_hours_end = Column(String(5), nullable=True)    # Format: "08:00"
    timezone = Column(String(50), nullable=False, default="UTC")
    
    # Channel preferences
    email_enabled = Column(Boolean, nullable=False, default=True)
    email_address = Column(String(255), nullable=True)  # Override user's primary email
    email_frequency = Column(String(20), nullable=False, default="immediate")  # immediate, hourly, daily
    
    in_app_enabled = Column(Boolean, nullable=False, default=True)
    webhook_enabled = Column(Boolean, nullable=False, default=False)
    webhook_url = Column(String(500), nullable=True)
    
    slack_enabled = Column(Boolean, nullable=False, default=False)
    slack_webhook_url = Column(String(500), nullable=True)
    slack_channel = Column(String(100), nullable=True)
    
    # Notification type preferences (JSON object with type -> settings mapping)
    type_preferences = Column(JSON, nullable=False, default=dict)
    
    # Project-specific preferences
    project_preferences = Column(JSON, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences")
    
    def __repr__(self):
        return f"<NotificationPreferences(id={self.id}, user_id={self.user_id})>"
    
    def is_type_enabled(self, notification_type: str, channel: str = "in_app") -> bool:
        """Check if a specific notification type is enabled for a channel."""
        if not self.enabled:
            return False
        
        type_prefs = self.type_preferences.get(notification_type, {})
        return type_prefs.get(f"{channel}_enabled", True)
    
    def is_in_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        # This is a simplified implementation
        # In production, you'd want proper timezone handling
        from datetime import time
        now = datetime.utcnow().time()
        start = time.fromisoformat(self.quiet_hours_start)
        end = time.fromisoformat(self.quiet_hours_end)
        
        if start <= end:
            return start <= now <= end
        else:  # Quiet hours span midnight
            return now >= start or now <= end


class NotificationDeliveryLog(Base):
    """Log of notification delivery attempts."""
    
    __tablename__ = "notification_delivery_logs"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    notification_id = Column(PostgresUUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False)
    
    # Delivery details
    channel = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    
    # Delivery metadata
    provider = Column(String(50), nullable=True)  # Email provider, webhook service, etc.
    external_id = Column(String(255), nullable=True)  # External service message ID
    response_data = Column(JSON, nullable=True)  # Response from delivery service
    error_message = Column(Text, nullable=True)
    
    # Timing
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    
    # Relationships
    notification = relationship("Notification", back_populates="delivery_logs")
    
    def __repr__(self):
        return f"<NotificationDeliveryLog(id={self.id}, channel={self.channel}, status={self.status})>"


class NotificationTemplate(Base):
    """Template for notification content generation."""
    
    __tablename__ = "notification_templates"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Template identification
    type = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False)
    language = Column(String(10), nullable=False, default="en")
    
    # Template content
    subject_template = Column(String(255), nullable=True)  # For email
    title_template = Column(String(255), nullable=False)
    message_template = Column(Text, nullable=False)
    
    # Template metadata
    variables = Column(JSON, nullable=True)  # List of available template variables
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, type={self.type}, channel={self.channel})>"


class NotificationSubscription(Base):
    """User subscriptions to specific notification topics."""
    
    __tablename__ = "notification_subscriptions"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Subscription details
    topic = Column(String(100), nullable=False)  # e.g., "project:123", "repository:456"
    notification_types = Column(JSON, nullable=False, default=list)  # List of subscribed types
    channels = Column(JSON, nullable=False, default=list)  # Preferred channels for this subscription
    
    # Subscription metadata
    is_active = Column(Boolean, nullable=False, default=True)
    auto_subscribed = Column(Boolean, nullable=False, default=False)  # Auto-subscribed vs manual
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notification_subscriptions")
    
    def __repr__(self):
        return f"<NotificationSubscription(id={self.id}, user_id={self.user_id}, topic={self.topic})>"


class NotificationDigest(Base):
    """Digest notifications for batched delivery."""
    
    __tablename__ = "notification_digests"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Digest details
    digest_type = Column(String(20), nullable=False)  # hourly, daily, weekly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Digest content
    notification_count = Column(Integer, nullable=False, default=0)
    notifications = Column(JSON, nullable=False, default=list)  # List of notification IDs
    summary_data = Column(JSON, nullable=True)  # Aggregated summary data
    
    # Delivery status
    status = Column(String(20), nullable=False, default=NotificationStatus.PENDING.value)
    sent_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notification_digests")
    
    def __repr__(self):
        return f"<NotificationDigest(id={self.id}, user_id={self.user_id}, type={self.digest_type})>"