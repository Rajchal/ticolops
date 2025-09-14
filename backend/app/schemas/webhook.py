"""Pydantic schemas for webhook-related data structures."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.repository import GitProvider


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    MERGE_REQUEST = "merge_request"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    RELEASE = "release"
    UNKNOWN = "unknown"


class WebhookStatus(str, Enum):
    """Webhook processing status."""
    SUCCESS = "success"
    PROCESSED = "processed"
    IGNORED = "ignored"
    ERROR = "error"
    FAILED = "failed"


class WebhookCommit(BaseModel):
    """Represents a commit in a webhook payload."""
    sha: str = Field(..., description="Commit SHA hash")
    message: str = Field(..., description="Commit message")
    author: Dict[str, str] = Field(..., description="Commit author information")
    url: Optional[str] = Field(None, description="Commit URL")
    timestamp: Optional[datetime] = Field(None, description="Commit timestamp")
    
    @validator('message')
    def validate_message(cls, v):
        """Ensure commit message is not empty."""
        if not v or not v.strip():
            return "No commit message"
        return v.strip()


class WebhookPusher(BaseModel):
    """Represents the user who pushed commits."""
    name: Optional[str] = Field(None, description="Pusher name")
    email: Optional[str] = Field(None, description="Pusher email")
    username: Optional[str] = Field(None, description="Pusher username")


class WebhookRepository(BaseModel):
    """Represents repository information in webhook payload."""
    id: int = Field(..., description="Repository ID from Git provider")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/repo)")
    url: str = Field(..., description="Repository URL")
    clone_url: Optional[str] = Field(None, description="Clone URL")
    default_branch: str = Field(..., description="Default branch name")
    private: bool = Field(..., description="Whether repository is private")


class WebhookPullRequest(BaseModel):
    """Represents pull/merge request information."""
    number: int = Field(..., description="PR/MR number")
    title: str = Field(..., description="PR/MR title")
    body: Optional[str] = Field(None, description="PR/MR description")
    state: str = Field(..., description="PR/MR state (open, closed, merged)")
    author: Dict[str, str] = Field(..., description="PR/MR author information")
    source_branch: str = Field(..., description="Source branch")
    target_branch: str = Field(..., description="Target branch")
    url: str = Field(..., description="PR/MR URL")


class WebhookEventData(BaseModel):
    """Base webhook event data structure."""
    provider: GitProvider = Field(..., description="Git provider")
    event_type: WebhookEventType = Field(..., description="Event type")
    repository: WebhookRepository = Field(..., description="Repository information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    signature: Optional[str] = Field(None, description="Webhook signature")
    delivery_id: Optional[str] = Field(None, description="Delivery ID from provider")


class WebhookPushEvent(WebhookEventData):
    """Push event webhook data."""
    event_type: WebhookEventType = Field(WebhookEventType.PUSH, const=True)
    branch: str = Field(..., description="Branch that was pushed to")
    before_sha: Optional[str] = Field(None, description="SHA before push")
    after_sha: str = Field(..., description="SHA after push")
    commits: List[WebhookCommit] = Field(..., description="List of commits")
    pusher: Optional[WebhookPusher] = Field(None, description="User who pushed")
    forced: bool = Field(False, description="Whether push was forced")
    
    @validator('commits')
    def validate_commits(cls, v):
        """Ensure at least one commit for push events."""
        if not v:
            raise ValueError("Push events must have at least one commit")
        return v


class WebhookPullRequestEvent(WebhookEventData):
    """Pull/merge request event webhook data."""
    event_type: WebhookEventType = Field(WebhookEventType.PULL_REQUEST, const=True)
    action: str = Field(..., description="PR action (opened, closed, merged, etc.)")
    pull_request: WebhookPullRequest = Field(..., description="Pull request information")


class WebhookProcessingResult(BaseModel):
    """Result of webhook processing."""
    status: WebhookStatus = Field(..., description="Processing status")
    action: Optional[str] = Field(None, description="Action taken")
    reason: Optional[str] = Field(None, description="Reason for status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class WebhookRegistrationRequest(BaseModel):
    """Request to register a webhook."""
    webhook_url: str = Field(..., description="Webhook URL to register")
    events: List[str] = Field(
        default=["push", "pull_request"],
        description="List of events to subscribe to"
    )
    secret: Optional[str] = Field(None, description="Webhook secret for signature verification")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        """Validate webhook URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v
    
    @validator('events')
    def validate_events(cls, v):
        """Validate event types."""
        valid_events = {
            "push", "pull_request", "merge_request", "issues", 
            "issue_comment", "release", "create", "delete"
        }
        for event in v:
            if event not in valid_events:
                raise ValueError(f"Invalid event type: {event}")
        return v


class WebhookRegistrationResponse(BaseModel):
    """Response from webhook registration."""
    status: str = Field(..., description="Registration status")
    webhook_id: Optional[str] = Field(None, description="Webhook ID from provider")
    webhook_url: str = Field(..., description="Registered webhook URL")
    events: List[str] = Field(..., description="Subscribed events")
    repository_id: str = Field(..., description="Repository ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Registration timestamp")


class WebhookEventLog(BaseModel):
    """Webhook event log entry."""
    id: str = Field(..., description="Event log ID")
    repository_id: str = Field(..., description="Repository ID")
    provider: GitProvider = Field(..., description="Git provider")
    event_type: WebhookEventType = Field(..., description="Event type")
    status: WebhookStatus = Field(..., description="Processing status")
    payload_summary: Dict[str, Any] = Field(..., description="Summary of webhook payload")
    processing_result: WebhookProcessingResult = Field(..., description="Processing result")
    timestamp: datetime = Field(..., description="Event timestamp")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")


class WebhookEventsResponse(BaseModel):
    """Response containing webhook events."""
    repository_id: str = Field(..., description="Repository ID")
    events: List[WebhookEventLog] = Field(..., description="List of webhook events")
    count: int = Field(..., description="Number of events returned")
    total_count: Optional[int] = Field(None, description="Total number of events available")


class WebhookTestResponse(BaseModel):
    """Response from webhook test endpoint."""
    status: str = Field(..., description="Test status")
    message: str = Field(..., description="Test message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Test timestamp")
    connectivity: bool = Field(True, description="Whether webhook endpoint is accessible")


class WebhookUnregistrationResponse(BaseModel):
    """Response from webhook unregistration."""
    status: str = Field(..., description="Unregistration status")
    repository_id: str = Field(..., description="Repository ID")
    webhook_id: str = Field(..., description="Webhook ID that was unregistered")
    message: Optional[str] = Field(None, description="Additional message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Unregistration timestamp")