"""Pydantic schemas for notification-related data structures."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.notification import (
    NotificationType, NotificationChannel, NotificationPriority, 
    NotificationStatus
)


class NotificationBase(BaseModel):
    """Base notification schema."""
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., max_length=255, description="Notification title")
    message: str = Field(..., description="Notification message")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Notification priority")
    category: Optional[str] = Field(None, max_length=50, description="Notification category")
    action_url: Optional[str] = Field(None, max_length=500, description="Action URL")
    action_text: Optional[str] = Field(None, max_length=100, description="Action button text")
    
    @validator('title')
    def validate_title(cls, v):
        """Validate title is not empty."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message is not empty."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    user_id: str = Field(..., description="Target user ID")
    project_id: Optional[str] = Field(None, description="Related project ID")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    channels: List[NotificationChannel] = Field(default=[NotificationChannel.IN_APP], description="Delivery channels")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule notification for future delivery")
    expires_at: Optional[datetime] = Field(None, description="Notification expiration time")
    
    @validator('channels')
    def validate_channels(cls, v):
        """Validate at least one channel is specified."""
        if not v:
            raise ValueError("At least one delivery channel must be specified")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "project_id": "123e4567-e89b-12d3-a456-426614174001",
                "type": "deployment_success",
                "title": "Deployment Successful",
                "message": "Your deployment to production was successful!",
                "priority": "normal",
                "category": "deployment",
                "action_url": "https://app.example.com/deployments/123",
                "action_text": "View Deployment",
                "channels": ["in_app", "email"],
                "data": {
                    "deployment_id": "deployment-123",
                    "repository_name": "my-app",
                    "preview_url": "https://preview.example.com"
                }
            }
        }


class NotificationUpdate(BaseModel):
    """Schema for updating notification status."""
    status: Optional[NotificationStatus] = Field(None, description="Notification status")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "read",
                "read_at": "2024-01-01T12:00:00Z"
            }
        }


class Notification(NotificationBase):
    """Complete notification schema."""
    id: str = Field(..., description="Notification ID")
    user_id: str = Field(..., description="Target user ID")
    project_id: Optional[str] = Field(None, description="Related project ID")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    status: NotificationStatus = Field(..., description="Notification status")
    channels: List[NotificationChannel] = Field(..., description="Delivery channels")
    delivery_attempts: int = Field(..., description="Number of delivery attempts")
    last_delivery_attempt: Optional[datetime] = Field(None, description="Last delivery attempt timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled delivery time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "project_id": "123e4567-e89b-12d3-a456-426614174002",
                "type": "deployment_success",
                "title": "Deployment Successful",
                "message": "Your deployment to production was successful!",
                "priority": "normal",
                "category": "deployment",
                "status": "sent",
                "channels": ["in_app", "email"],
                "delivery_attempts": 1,
                "created_at": "2024-01-01T12:00:00Z",
                "read_at": None
            }
        }


class NotificationSummary(BaseModel):
    """Summary notification information for lists."""
    id: str = Field(..., description="Notification ID")
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    priority: NotificationPriority = Field(..., description="Notification priority")
    status: NotificationStatus = Field(..., description="Notification status")
    created_at: datetime = Field(..., description="Creation timestamp")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    
    class Config:
        from_attributes = True


class NotificationPreferencesBase(BaseModel):
    """Base notification preferences schema."""
    enabled: bool = Field(True, description="Global notification toggle")
    quiet_hours_enabled: bool = Field(False, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours end time (HH:MM)")
    timezone: str = Field("UTC", description="User timezone")
    
    # Channel preferences
    email_enabled: bool = Field(True, description="Enable email notifications")
    email_address: Optional[str] = Field(None, description="Override email address")
    email_frequency: str = Field("immediate", regex="^(immediate|hourly|daily)$", description="Email delivery frequency")
    
    in_app_enabled: bool = Field(True, description="Enable in-app notifications")
    webhook_enabled: bool = Field(False, description="Enable webhook notifications")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    
    slack_enabled: bool = Field(False, description="Enable Slack notifications")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    slack_channel: Optional[str] = Field(None, description="Slack channel")
    
    @validator('webhook_url', 'slack_webhook_url')
    def validate_webhook_urls(cls, v):
        """Validate webhook URLs."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


class NotificationPreferencesCreate(NotificationPreferencesBase):
    """Schema for creating notification preferences."""
    user_id: str = Field(..., description="User ID")
    type_preferences: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict, description="Type-specific preferences")
    project_preferences: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict, description="Project-specific preferences")


class NotificationPreferencesUpdate(BaseModel):
    """Schema for updating notification preferences."""
    enabled: Optional[bool] = Field(None, description="Global notification toggle")
    quiet_hours_enabled: Optional[bool] = Field(None, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours start time")
    quiet_hours_end: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Quiet hours end time")
    timezone: Optional[str] = Field(None, description="User timezone")
    
    email_enabled: Optional[bool] = Field(None, description="Enable email notifications")
    email_address: Optional[str] = Field(None, description="Override email address")
    email_frequency: Optional[str] = Field(None, regex="^(immediate|hourly|daily)$", description="Email frequency")
    
    in_app_enabled: Optional[bool] = Field(None, description="Enable in-app notifications")
    webhook_enabled: Optional[bool] = Field(None, description="Enable webhook notifications")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    
    slack_enabled: Optional[bool] = Field(None, description="Enable Slack notifications")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    slack_channel: Optional[str] = Field(None, description="Slack channel")
    
    type_preferences: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Type-specific preferences")
    project_preferences: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Project-specific preferences")


class NotificationPreferences(NotificationPreferencesBase):
    """Complete notification preferences schema."""
    id: str = Field(..., description="Preferences ID")
    user_id: str = Field(..., description="User ID")
    type_preferences: Dict[str, Dict[str, Any]] = Field(..., description="Type-specific preferences")
    project_preferences: Dict[str, Dict[str, Any]] = Field(..., description="Project-specific preferences")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class NotificationDeliveryLogBase(BaseModel):
    """Base notification delivery log schema."""
    channel: NotificationChannel = Field(..., description="Delivery channel")
    status: NotificationStatus = Field(..., description="Delivery status")
    attempt_number: int = Field(..., description="Attempt number")
    provider: Optional[str] = Field(None, description="Delivery provider")
    external_id: Optional[str] = Field(None, description="External service ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class NotificationDeliveryLog(NotificationDeliveryLogBase):
    """Complete notification delivery log schema."""
    id: str = Field(..., description="Log entry ID")
    notification_id: str = Field(..., description="Notification ID")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Provider response data")
    attempted_at: datetime = Field(..., description="Attempt timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    
    class Config:
        from_attributes = True


class NotificationSubscriptionBase(BaseModel):
    """Base notification subscription schema."""
    topic: str = Field(..., max_length=100, description="Subscription topic")
    notification_types: List[NotificationType] = Field(..., description="Subscribed notification types")
    channels: List[NotificationChannel] = Field(..., description="Preferred channels")
    is_active: bool = Field(True, description="Subscription active status")
    
    @validator('notification_types')
    def validate_notification_types(cls, v):
        """Validate at least one notification type."""
        if not v:
            raise ValueError("At least one notification type must be specified")
        return v
    
    @validator('channels')
    def validate_channels(cls, v):
        """Validate at least one channel."""
        if not v:
            raise ValueError("At least one channel must be specified")
        return v


class NotificationSubscriptionCreate(NotificationSubscriptionBase):
    """Schema for creating notification subscription."""
    user_id: str = Field(..., description="User ID")


class NotificationSubscription(NotificationSubscriptionBase):
    """Complete notification subscription schema."""
    id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    auto_subscribed: bool = Field(..., description="Auto-subscribed flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class NotificationBulkCreate(BaseModel):
    """Schema for creating multiple notifications."""
    notifications: List[NotificationCreate] = Field(..., description="List of notifications to create")
    
    @validator('notifications')
    def validate_notifications(cls, v):
        """Validate notification list."""
        if not v:
            raise ValueError("At least one notification must be provided")
        if len(v) > 100:
            raise ValueError("Cannot create more than 100 notifications at once")
        return v


class NotificationBulkUpdate(BaseModel):
    """Schema for bulk updating notifications."""
    notification_ids: List[str] = Field(..., description="List of notification IDs")
    updates: NotificationUpdate = Field(..., description="Updates to apply")
    
    @validator('notification_ids')
    def validate_notification_ids(cls, v):
        """Validate notification IDs list."""
        if not v:
            raise ValueError("At least one notification ID must be provided")
        if len(v) > 100:
            raise ValueError("Cannot update more than 100 notifications at once")
        return v


class NotificationStats(BaseModel):
    """Notification statistics schema."""
    total_notifications: int = Field(..., description="Total notifications")
    unread_notifications: int = Field(..., description="Unread notifications")
    notifications_by_type: Dict[str, int] = Field(..., description="Notifications grouped by type")
    notifications_by_status: Dict[str, int] = Field(..., description="Notifications grouped by status")
    notifications_by_priority: Dict[str, int] = Field(..., description="Notifications grouped by priority")
    recent_notifications: List[NotificationSummary] = Field(..., description="Recent notifications")
    delivery_success_rate: float = Field(..., description="Delivery success rate percentage")
    
    class Config:
        schema_extra = {
            "example": {
                "total_notifications": 150,
                "unread_notifications": 12,
                "notifications_by_type": {
                    "deployment_success": 45,
                    "deployment_failed": 8,
                    "user_mentioned": 15
                },
                "notifications_by_status": {
                    "sent": 120,
                    "read": 108,
                    "failed": 5
                },
                "notifications_by_priority": {
                    "normal": 130,
                    "high": 15,
                    "urgent": 5
                },
                "recent_notifications": [],
                "delivery_success_rate": 96.7
            }
        }


class NotificationDigestCreate(BaseModel):
    """Schema for creating notification digest."""
    user_id: str = Field(..., description="User ID")
    digest_type: str = Field(..., regex="^(hourly|daily|weekly)$", description="Digest type")
    period_start: datetime = Field(..., description="Digest period start")
    period_end: datetime = Field(..., description="Digest period end")
    notification_ids: List[str] = Field(..., description="Notification IDs to include")


class NotificationDigest(BaseModel):
    """Complete notification digest schema."""
    id: str = Field(..., description="Digest ID")
    user_id: str = Field(..., description="User ID")
    digest_type: str = Field(..., description="Digest type")
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")
    notification_count: int = Field(..., description="Number of notifications")
    summary_data: Optional[Dict[str, Any]] = Field(None, description="Summary data")
    status: NotificationStatus = Field(..., description="Digest status")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True