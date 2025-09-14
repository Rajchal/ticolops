"""API endpoints for notification management."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.notification import NotificationType, NotificationChannel, NotificationPriority
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    Notification, NotificationCreate, NotificationUpdate, NotificationSummary,
    NotificationPreferences, NotificationPreferencesUpdate, NotificationStats,
    NotificationBulkCreate, NotificationBulkUpdate
)
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/notifications", response_model=Notification, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new notification."""
    try:
        notification_service = NotificationService(db)
        
        notification = await notification_service.create_notification(
            user_id=notification_data.user_id,
            notification_type=notification_data.type,
            title=notification_data.title,
            message=notification_data.message,
            project_id=notification_data.project_id,
            data=notification_data.data,
            priority=notification_data.priority,
            category=notification_data.category,
            action_url=notification_data.action_url,
            action_text=notification_data.action_text,
            channels=notification_data.channels,
            scheduled_for=notification_data.scheduled_for,
            expires_at=notification_data.expires_at
        )
        
        return notification
    
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/notifications/bulk", response_model=List[Notification], status_code=status.HTTP_201_CREATED)
async def create_bulk_notifications(
    bulk_data: NotificationBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple notifications in bulk."""
    try:
        notification_service = NotificationService(db)
        
        # Convert Pydantic models to dictionaries
        notifications_data = [notification.dict() for notification in bulk_data.notifications]
        
        notifications = await notification_service.create_bulk_notifications(notifications_data)
        
        return notifications
    
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating bulk notifications: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/notifications", response_model=List[NotificationSummary])
async def get_user_notifications(
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the current user."""
    try:
        notification_service = NotificationService(db)
        
        notifications = await notification_service.get_user_notifications(
            user_id=str(current_user.id),
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            notification_type=notification_type,
            category=category
        )
        
        return notifications
    
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/notifications/{notification_id}", response_model=Notification)
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific notification."""
    try:
        notification_service = NotificationService(db)
        
        # Get user notifications and find the specific one
        notifications = await notification_service.get_user_notifications(
            user_id=str(current_user.id),
            limit=1000  # Large limit to find the notification
        )
        
        notification = next((n for n in notifications if str(n.id) == notification_id), None)
        if not notification:
            raise NotFoundError(f"Notification {notification_id} not found")
        
        return notification
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving notification: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/notifications/{notification_id}", response_model=Notification)
async def update_notification(
    notification_id: str,
    notification_update: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a notification (typically to mark as read)."""
    try:
        notification_service = NotificationService(db)
        
        if notification_update.status == "read" or notification_update.read_at:
            notification = await notification_service.mark_notification_as_read(
                notification_id, str(current_user.id)
            )
            return notification
        
        # For other updates, you'd implement additional logic here
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only read status updates are supported")
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notification: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification."""
    try:
        notification_service = NotificationService(db)
        
        success = await notification_service.delete_notification(
            notification_id, str(current_user.id)
        )
        
        return {
            "success": success,
            "message": "Notification deleted successfully",
            "notification_id": notification_id
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for the current user."""
    try:
        notification_service = NotificationService(db)
        
        count = await notification_service.mark_all_notifications_as_read(str(current_user.id))
        
        return {
            "success": True,
            "message": f"Marked {count} notifications as read",
            "count": count
        }
    
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/notifications/bulk", response_model=Dict[str, Any])
async def bulk_update_notifications(
    bulk_update: NotificationBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk update multiple notifications."""
    try:
        notification_service = NotificationService(db)
        
        updated_count = 0
        failed_count = 0
        
        for notification_id in bulk_update.notification_ids:
            try:
                if bulk_update.updates.status == "read" or bulk_update.updates.read_at:
                    await notification_service.mark_notification_as_read(
                        notification_id, str(current_user.id)
                    )
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update notification {notification_id}: {str(e)}")
                failed_count += 1
        
        return {
            "success": True,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "total_requested": len(bulk_update.notification_ids)
        }
    
    except Exception as e:
        logger.error(f"Error bulk updating notifications: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/notifications/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics for the current user."""
    try:
        notification_service = NotificationService(db)
        
        stats = await notification_service.get_notification_stats(str(current_user.id))
        
        return stats
    
    except Exception as e:
        logger.error(f"Error retrieving notification stats: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/notification-preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification preferences for the current user."""
    try:
        notification_service = NotificationService(db)
        
        preferences = await notification_service.get_user_preferences(str(current_user.id))
        
        return preferences
    
    except Exception as e:
        logger.error(f"Error retrieving notification preferences: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/notification-preferences", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences_update: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update notification preferences for the current user."""
    try:
        notification_service = NotificationService(db)
        
        # Convert Pydantic model to dict, excluding None values
        updates = preferences_update.dict(exclude_none=True)
        
        preferences = await notification_service.update_user_preferences(
            str(current_user.id), updates
        )
        
        return preferences
    
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/notifications/test")
async def test_notification(
    test_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a test notification to the current user."""
    try:
        notification_service = NotificationService(db)
        
        notification = await notification_service.create_notification(
            user_id=str(current_user.id),
            notification_type=NotificationType(test_data.get("type", "system_maintenance")),
            title=test_data.get("title", "Test Notification"),
            message=test_data.get("message", "This is a test notification to verify your notification settings."),
            priority=NotificationPriority(test_data.get("priority", "normal")),
            category="test",
            channels=[NotificationChannel(ch) for ch in test_data.get("channels", ["in_app"])]
        )
        
        return {
            "success": True,
            "message": "Test notification sent successfully",
            "notification_id": str(notification.id)
        }
    
    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/notifications/unread/count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications for the current user."""
    try:
        notification_service = NotificationService(db)
        
        stats = await notification_service.get_notification_stats(str(current_user.id))
        
        return {
            "unread_count": stats["unread_notifications"],
            "total_count": stats["total_notifications"]
        }
    
    except Exception as e:
        logger.error(f"Error retrieving unread count: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/notifications/types")
async def get_notification_types():
    """Get available notification types."""
    return {
        "notification_types": [
            {
                "value": nt.value,
                "label": nt.value.replace("_", " ").title(),
                "category": _get_notification_category(nt)
            }
            for nt in NotificationType
        ],
        "channels": [
            {
                "value": ch.value,
                "label": ch.value.replace("_", " ").title(),
                "description": _get_channel_description(ch)
            }
            for ch in NotificationChannel
        ],
        "priorities": [
            {
                "value": pr.value,
                "label": pr.value.title(),
                "description": _get_priority_description(pr)
            }
            for pr in NotificationPriority
        ]
    }


@router.delete("/notifications/cleanup")
async def cleanup_old_notifications(
    days: int = Query(30, ge=7, le=365, description="Delete notifications older than this many days"),
    dry_run: bool = Query(True, description="If true, only return what would be deleted"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up old notifications for the current user."""
    try:
        from sqlalchemy import select, delete
        from app.models.notification import Notification
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old notifications
        old_notifications_query = select(Notification).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.created_at < cutoff_date,
                or_(
                    Notification.read_at.is_not(None),  # Read notifications
                    Notification.status.in_(["failed", "cancelled"])  # Failed notifications
                )
            )
        )
        old_notifications_result = await db.execute(old_notifications_query)
        old_notifications = old_notifications_result.scalars().all()
        
        cleanup_summary = {
            "cutoff_date": cutoff_date.isoformat(),
            "notifications_found": len(old_notifications),
            "dry_run": dry_run,
            "notifications": [
                {
                    "id": str(notification.id),
                    "type": notification.type,
                    "title": notification.title,
                    "created_at": notification.created_at.isoformat(),
                    "status": notification.status
                }
                for notification in old_notifications[:10]  # Show first 10
            ]
        }
        
        if not dry_run and old_notifications:
            # Actually delete the notifications
            notification_ids = [notification.id for notification in old_notifications]
            delete_query = delete(Notification).where(
                Notification.id.in_(notification_ids)
            )
            await db.execute(delete_query)
            await db.commit()
            
            cleanup_summary["deleted"] = True
            logger.info(f"Cleaned up {len(old_notifications)} old notifications for user {current_user.id}")
        else:
            cleanup_summary["deleted"] = False
        
        return cleanup_summary
    
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


def _get_notification_category(notification_type: NotificationType) -> str:
    """Get category for notification type."""
    if notification_type.value.startswith("deployment_"):
        return "deployment"
    elif notification_type.value.startswith("project_"):
        return "project"
    elif notification_type.value.startswith("repository_"):
        return "repository"
    elif notification_type.value.startswith("user_"):
        return "activity"
    elif notification_type.value.startswith("system_"):
        return "system"
    else:
        return "other"


def _get_channel_description(channel: NotificationChannel) -> str:
    """Get description for notification channel."""
    descriptions = {
        NotificationChannel.IN_APP: "Notifications within the application",
        NotificationChannel.EMAIL: "Email notifications to your registered email address",
        NotificationChannel.WEBHOOK: "HTTP POST requests to your configured webhook URL",
        NotificationChannel.SLACK: "Messages sent to your Slack workspace",
        NotificationChannel.DISCORD: "Messages sent to your Discord server",
        NotificationChannel.SMS: "Text messages to your phone number"
    }
    return descriptions.get(channel, "Custom notification channel")


def _get_priority_description(priority: NotificationPriority) -> str:
    """Get description for notification priority."""
    descriptions = {
        NotificationPriority.LOW: "Low priority notifications for informational updates",
        NotificationPriority.NORMAL: "Normal priority notifications for regular updates",
        NotificationPriority.HIGH: "High priority notifications requiring attention",
        NotificationPriority.URGENT: "Urgent notifications requiring immediate attention"
    }
    return descriptions.get(priority, "Standard notification priority")