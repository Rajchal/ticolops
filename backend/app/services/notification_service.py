"""Comprehensive notification service for multi-channel delivery."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Notification, NotificationPreferences, NotificationDeliveryLog,
    NotificationSubscription, NotificationDigest, NotificationTemplate,
    NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
)
from app.models.user import User
from app.models.project import Project
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class NotificationDeliveryProvider:
    """Base class for notification delivery providers."""
    
    async def send_notification(
        self,
        notification: Notification,
        user: User,
        preferences: NotificationPreferences
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Send notification through this provider.
        
        Returns:
            Tuple of (success, error_message, response_data)
        """
        raise NotImplementedError


class EmailProvider(NotificationDeliveryProvider):
    """Email notification delivery provider."""
    
    async def send_notification(
        self,
        notification: Notification,
        user: User,
        preferences: NotificationPreferences
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send email notification."""
        try:
            # Use override email if specified, otherwise user's email
            email_address = preferences.email_address or user.email
            
            if not email_address:
                return False, "No email address available", None
            
            # Generate email content
            subject = self._generate_email_subject(notification)
            body = self._generate_email_body(notification, user)
            
            # Mock email sending (in production, integrate with email service)
            logger.info(f"Sending email to {email_address}: {subject}")
            
            # Simulate email service response
            response_data = {
                "message_id": f"email_{notification.id}_{datetime.utcnow().timestamp()}",
                "recipient": email_address,
                "subject": subject,
                "provider": "mock_email_service"
            }
            
            return True, None, response_data
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False, str(e), None
    
    def _generate_email_subject(self, notification: Notification) -> str:
        """Generate email subject line."""
        priority_prefix = ""
        if notification.priority == NotificationPriority.URGENT.value:
            priority_prefix = "[URGENT] "
        elif notification.priority == NotificationPriority.HIGH.value:
            priority_prefix = "[HIGH] "
        
        return f"{priority_prefix}{notification.title}"
    
    def _generate_email_body(self, notification: Notification, user: User) -> str:
        """Generate email body content."""
        body = f"Hi {user.name},\n\n"
        body += f"{notification.message}\n\n"
        
        if notification.action_url and notification.action_text:
            body += f"Action: {notification.action_text}\n"
            body += f"Link: {notification.action_url}\n\n"
        
        body += "Best regards,\n"
        body += "The Ticolops Team\n\n"
        body += "---\n"
        body += "You can manage your notification preferences at: "
        body += f"{settings.BASE_URL}/settings/notifications"
        
        return body


class WebhookProvider(NotificationDeliveryProvider):
    """Webhook notification delivery provider."""
    
    async def send_notification(
        self,
        notification: Notification,
        user: User,
        preferences: NotificationPreferences
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send webhook notification."""
        try:
            webhook_url = preferences.webhook_url
            if not webhook_url:
                return False, "No webhook URL configured", None
            
            # Prepare webhook payload
            payload = {
                "id": str(notification.id),
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority,
                "category": notification.category,
                "action_url": notification.action_url,
                "action_text": notification.action_text,
                "data": notification.data,
                "user_id": str(notification.user_id),
                "project_id": str(notification.project_id) if notification.project_id else None,
                "created_at": notification.created_at.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Mock webhook sending (in production, use aiohttp)
            logger.info(f"Sending webhook to {webhook_url}: {notification.type}")
            
            # Simulate webhook response
            response_data = {
                "webhook_url": webhook_url,
                "status_code": 200,
                "response_time_ms": 150,
                "provider": "webhook"
            }
            
            return True, None, response_data
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            return False, str(e), None


class SlackProvider(NotificationDeliveryProvider):
    """Slack notification delivery provider."""
    
    async def send_notification(
        self,
        notification: Notification,
        user: User,
        preferences: NotificationPreferences
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send Slack notification."""
        try:
            slack_webhook_url = preferences.slack_webhook_url
            if not slack_webhook_url:
                return False, "No Slack webhook URL configured", None
            
            # Prepare Slack message
            color = self._get_slack_color(notification.priority)
            
            slack_payload = {
                "channel": preferences.slack_channel or "#general",
                "username": "Ticolops",
                "icon_emoji": ":bell:",
                "attachments": [
                    {
                        "color": color,
                        "title": notification.title,
                        "text": notification.message,
                        "fields": [
                            {
                                "title": "Priority",
                                "value": notification.priority.title(),
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": notification.type.replace("_", " ").title(),
                                "short": True
                            }
                        ],
                        "footer": "Ticolops Notifications",
                        "ts": int(notification.created_at.timestamp())
                    }
                ]
            }
            
            if notification.action_url and notification.action_text:
                slack_payload["attachments"][0]["actions"] = [
                    {
                        "type": "button",
                        "text": notification.action_text,
                        "url": notification.action_url
                    }
                ]
            
            # Mock Slack sending
            logger.info(f"Sending Slack notification to {preferences.slack_channel}: {notification.type}")
            
            response_data = {
                "slack_webhook_url": slack_webhook_url,
                "channel": preferences.slack_channel,
                "status": "ok",
                "provider": "slack"
            }
            
            return True, None, response_data
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False, str(e), None
    
    def _get_slack_color(self, priority: str) -> str:
        """Get Slack attachment color based on priority."""
        color_map = {
            NotificationPriority.LOW.value: "#36a64f",      # Green
            NotificationPriority.NORMAL.value: "#2196F3",   # Blue
            NotificationPriority.HIGH.value: "#ff9800",     # Orange
            NotificationPriority.URGENT.value: "#f44336"    # Red
        }
        return color_map.get(priority, "#2196F3")


class InAppProvider(NotificationDeliveryProvider):
    """In-app notification delivery provider."""
    
    async def send_notification(
        self,
        notification: Notification,
        user: User,
        preferences: NotificationPreferences
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Send in-app notification (store in database and broadcast via WebSocket)."""
        try:
            # In-app notifications are already stored in the database
            # Here we would broadcast via WebSocket to connected clients
            
            # Mock WebSocket broadcast
            logger.info(f"Broadcasting in-app notification to user {user.id}: {notification.type}")
            
            # Prepare WebSocket message
            websocket_message = {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "priority": notification.priority,
                    "category": notification.category,
                    "action_url": notification.action_url,
                    "action_text": notification.action_text,
                    "created_at": notification.created_at.isoformat()
                }
            }
            
            # Mock WebSocket broadcast (in production, use WebSocket manager)
            response_data = {
                "websocket_broadcast": True,
                "user_id": str(user.id),
                "message_type": "notification",
                "provider": "in_app"
            }
            
            return True, None, response_data
            
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {str(e)}")
            return False, str(e), None


class NotificationService:
    """Comprehensive notification service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Initialize delivery providers
        self.providers = {
            NotificationChannel.EMAIL: EmailProvider(),
            NotificationChannel.WEBHOOK: WebhookProvider(),
            NotificationChannel.SLACK: SlackProvider(),
            NotificationChannel.IN_APP: InAppProvider()
        }
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        project_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: Optional[str] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None,
        scheduled_for: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            project_id: Related project ID (optional)
            data: Additional structured data (optional)
            priority: Notification priority
            category: Notification category (optional)
            action_url: Action URL (optional)
            action_text: Action button text (optional)
            channels: Delivery channels (optional, will use user preferences)
            scheduled_for: Schedule for future delivery (optional)
            expires_at: Expiration time (optional)
            
        Returns:
            Created notification
        """
        # Get user preferences to determine channels if not specified
        if not channels:
            preferences = await self.get_user_preferences(user_id)
            channels = await self._determine_channels(notification_type, preferences)
        
        # Create notification
        notification = Notification(
            user_id=UUID(user_id),
            project_id=UUID(project_id) if project_id else None,
            type=notification_type.value,
            title=title,
            message=message,
            data=data,
            priority=priority.value,
            category=category,
            action_url=action_url,
            action_text=action_text,
            channels=[channel.value for channel in channels],
            scheduled_for=scheduled_for,
            expires_at=expires_at
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Deliver notification if not scheduled
        if not scheduled_for or scheduled_for <= datetime.utcnow():
            asyncio.create_task(self._deliver_notification(notification))
        
        logger.info(f"Created notification {notification.id} for user {user_id}")
        return notification
    
    async def create_bulk_notifications(
        self,
        notifications_data: List[Dict[str, Any]]
    ) -> List[Notification]:
        """
        Create multiple notifications in bulk.
        
        Args:
            notifications_data: List of notification data dictionaries
            
        Returns:
            List of created notifications
        """
        notifications = []
        
        for data in notifications_data:
            notification = Notification(
                user_id=UUID(data["user_id"]),
                project_id=UUID(data["project_id"]) if data.get("project_id") else None,
                type=data["type"],
                title=data["title"],
                message=data["message"],
                data=data.get("data"),
                priority=data.get("priority", NotificationPriority.NORMAL.value),
                category=data.get("category"),
                action_url=data.get("action_url"),
                action_text=data.get("action_text"),
                channels=data.get("channels", [NotificationChannel.IN_APP.value]),
                scheduled_for=data.get("scheduled_for"),
                expires_at=data.get("expires_at")
            )
            notifications.append(notification)
        
        # Bulk insert
        self.db.add_all(notifications)
        await self.db.commit()
        
        # Refresh all notifications
        for notification in notifications:
            await self.db.refresh(notification)
        
        # Deliver notifications asynchronously
        for notification in notifications:
            if not notification.scheduled_for or notification.scheduled_for <= datetime.utcnow():
                asyncio.create_task(self._deliver_notification(notification))
        
        logger.info(f"Created {len(notifications)} bulk notifications")
        return notifications
    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None,
        category: Optional[str] = None
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of notifications
            offset: Offset for pagination
            unread_only: Only return unread notifications
            notification_type: Filter by notification type
            category: Filter by category
            
        Returns:
            List of notifications
        """
        query = select(Notification).where(
            Notification.user_id == UUID(user_id)
        ).order_by(desc(Notification.created_at))
        
        # Apply filters
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        
        if notification_type:
            query = query.where(Notification.type == notification_type.value)
        
        if category:
            query = query.where(Notification.category == category)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> Notification:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)
            
        Returns:
            Updated notification
        """
        query = select(Notification).where(
            and_(
                Notification.id == UUID(notification_id),
                Notification.user_id == UUID(user_id)
            )
        )
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise NotFoundError(f"Notification {notification_id} not found")
        
        if not notification.read_at:
            notification.read_at = datetime.utcnow()
            notification.status = NotificationStatus.READ.value
            await self.db.commit()
            await self.db.refresh(notification)
        
        return notification
    
    async def mark_all_notifications_as_read(self, user_id: str) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        query = update(Notification).where(
            and_(
                Notification.user_id == UUID(user_id),
                Notification.read_at.is_(None)
            )
        ).values(
            read_at=datetime.utcnow(),
            status=NotificationStatus.READ.value
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        return result.rowcount
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """
        Delete a notification.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)
            
        Returns:
            True if deleted successfully
        """
        query = select(Notification).where(
            and_(
                Notification.id == UUID(notification_id),
                Notification.user_id == UUID(user_id)
            )
        )
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise NotFoundError(f"Notification {notification_id} not found")
        
        await self.db.delete(notification)
        await self.db.commit()
        
        return True
    
    async def get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """
        Get user notification preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            User notification preferences
        """
        query = select(NotificationPreferences).where(
            NotificationPreferences.user_id == UUID(user_id)
        )
        result = await self.db.execute(query)
        preferences = result.scalar_one_or_none()
        
        if not preferences:
            # Create default preferences
            preferences = await self.create_default_preferences(user_id)
        
        return preferences
    
    async def create_default_preferences(self, user_id: str) -> NotificationPreferences:
        """
        Create default notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Created preferences
        """
        preferences = NotificationPreferences(
            user_id=UUID(user_id),
            enabled=True,
            email_enabled=True,
            in_app_enabled=True,
            type_preferences={},
            project_preferences={}
        )
        
        self.db.add(preferences)
        await self.db.commit()
        await self.db.refresh(preferences)
        
        return preferences
    
    async def update_user_preferences(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> NotificationPreferences:
        """
        Update user notification preferences.
        
        Args:
            user_id: User ID
            updates: Dictionary of updates to apply
            
        Returns:
            Updated preferences
        """
        preferences = await self.get_user_preferences(user_id)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)
        
        preferences.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(preferences)
        
        return preferences
    
    async def get_notification_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get notification statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Notification statistics
        """
        # Total notifications
        total_query = select(func.count(Notification.id)).where(
            Notification.user_id == UUID(user_id)
        )
        total_result = await self.db.execute(total_query)
        total_notifications = total_result.scalar() or 0
        
        # Unread notifications
        unread_query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == UUID(user_id),
                Notification.read_at.is_(None)
            )
        )
        unread_result = await self.db.execute(unread_query)
        unread_notifications = unread_result.scalar() or 0
        
        # Notifications by type
        type_query = select(
            Notification.type,
            func.count(Notification.id)
        ).where(
            Notification.user_id == UUID(user_id)
        ).group_by(Notification.type)
        
        type_result = await self.db.execute(type_query)
        notifications_by_type = dict(type_result.fetchall())
        
        # Notifications by status
        status_query = select(
            Notification.status,
            func.count(Notification.id)
        ).where(
            Notification.user_id == UUID(user_id)
        ).group_by(Notification.status)
        
        status_result = await self.db.execute(status_query)
        notifications_by_status = dict(status_result.fetchall())
        
        # Notifications by priority
        priority_query = select(
            Notification.priority,
            func.count(Notification.id)
        ).where(
            Notification.user_id == UUID(user_id)
        ).group_by(Notification.priority)
        
        priority_result = await self.db.execute(priority_query)
        notifications_by_priority = dict(priority_result.fetchall())
        
        # Recent notifications
        recent_query = select(Notification).where(
            Notification.user_id == UUID(user_id)
        ).order_by(desc(Notification.created_at)).limit(5)
        
        recent_result = await self.db.execute(recent_query)
        recent_notifications = recent_result.scalars().all()
        
        # Delivery success rate
        delivery_success_rate = await self._calculate_delivery_success_rate(user_id)
        
        return {
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "notifications_by_type": notifications_by_type,
            "notifications_by_status": notifications_by_status,
            "notifications_by_priority": notifications_by_priority,
            "recent_notifications": recent_notifications,
            "delivery_success_rate": delivery_success_rate
        }
    
    async def _deliver_notification(self, notification: Notification) -> None:
        """
        Deliver notification through all specified channels.
        
        Args:
            notification: Notification to deliver
        """
        try:
            # Get user and preferences
            user_query = select(User).where(User.id == notification.user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {notification.user_id} not found for notification {notification.id}")
                return
            
            preferences = await self.get_user_preferences(str(notification.user_id))
            
            # Check if notifications are enabled and not in quiet hours
            if not preferences.enabled or preferences.is_in_quiet_hours():
                logger.info(f"Skipping notification {notification.id} - disabled or quiet hours")
                return
            
            # Deliver through each channel
            delivery_success = False
            
            for channel_str in notification.channels:
                try:
                    channel = NotificationChannel(channel_str)
                    
                    # Check if channel is enabled for this notification type
                    if not self._is_channel_enabled(channel, notification.type, preferences):
                        continue
                    
                    provider = self.providers.get(channel)
                    if not provider:
                        logger.warning(f"No provider for channel {channel}")
                        continue
                    
                    # Attempt delivery
                    success, error_message, response_data = await provider.send_notification(
                        notification, user, preferences
                    )
                    
                    # Log delivery attempt
                    await self._log_delivery_attempt(
                        notification, channel, success, error_message, response_data
                    )
                    
                    if success:
                        delivery_success = True
                    
                except Exception as e:
                    logger.error(f"Error delivering notification {notification.id} via {channel_str}: {str(e)}")
                    await self._log_delivery_attempt(
                        notification, NotificationChannel(channel_str), False, str(e), None
                    )
            
            # Update notification status
            if delivery_success:
                notification.status = NotificationStatus.SENT.value
            else:
                notification.status = NotificationStatus.FAILED.value
            
            notification.delivery_attempts += 1
            notification.last_delivery_attempt = datetime.utcnow()
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification.id}: {str(e)}")
    
    async def _determine_channels(
        self,
        notification_type: NotificationType,
        preferences: NotificationPreferences
    ) -> List[NotificationChannel]:
        """Determine delivery channels based on user preferences."""
        channels = []
        
        if preferences.in_app_enabled and preferences.is_type_enabled(notification_type.value, "in_app"):
            channels.append(NotificationChannel.IN_APP)
        
        if preferences.email_enabled and preferences.is_type_enabled(notification_type.value, "email"):
            channels.append(NotificationChannel.EMAIL)
        
        if preferences.webhook_enabled and preferences.webhook_url:
            channels.append(NotificationChannel.WEBHOOK)
        
        if preferences.slack_enabled and preferences.slack_webhook_url:
            channels.append(NotificationChannel.SLACK)
        
        # Default to in-app if no channels enabled
        if not channels:
            channels.append(NotificationChannel.IN_APP)
        
        return channels
    
    def _is_channel_enabled(
        self,
        channel: NotificationChannel,
        notification_type: str,
        preferences: NotificationPreferences
    ) -> bool:
        """Check if a channel is enabled for a notification type."""
        if channel == NotificationChannel.EMAIL:
            return preferences.email_enabled and preferences.is_type_enabled(notification_type, "email")
        elif channel == NotificationChannel.IN_APP:
            return preferences.in_app_enabled and preferences.is_type_enabled(notification_type, "in_app")
        elif channel == NotificationChannel.WEBHOOK:
            return preferences.webhook_enabled and bool(preferences.webhook_url)
        elif channel == NotificationChannel.SLACK:
            return preferences.slack_enabled and bool(preferences.slack_webhook_url)
        
        return False
    
    async def _log_delivery_attempt(
        self,
        notification: Notification,
        channel: NotificationChannel,
        success: bool,
        error_message: Optional[str],
        response_data: Optional[Dict[str, Any]]
    ) -> None:
        """Log a delivery attempt."""
        log_entry = NotificationDeliveryLog(
            notification_id=notification.id,
            channel=channel.value,
            status=NotificationStatus.DELIVERED.value if success else NotificationStatus.FAILED.value,
            attempt_number=notification.delivery_attempts + 1,
            provider=response_data.get("provider") if response_data else None,
            external_id=response_data.get("message_id") if response_data else None,
            response_data=response_data,
            error_message=error_message,
            delivered_at=datetime.utcnow() if success else None
        )
        
        self.db.add(log_entry)
        await self.db.commit()
    
    async def _calculate_delivery_success_rate(self, user_id: str) -> float:
        """Calculate delivery success rate for a user."""
        # Get delivery logs for user's notifications
        query = select(func.count(NotificationDeliveryLog.id)).select_from(
            NotificationDeliveryLog.__table__.join(Notification.__table__)
        ).where(Notification.user_id == UUID(user_id))
        
        total_result = await self.db.execute(query)
        total_deliveries = total_result.scalar() or 0
        
        if total_deliveries == 0:
            return 100.0
        
        success_query = select(func.count(NotificationDeliveryLog.id)).select_from(
            NotificationDeliveryLog.__table__.join(Notification.__table__)
        ).where(
            and_(
                Notification.user_id == UUID(user_id),
                NotificationDeliveryLog.status == NotificationStatus.DELIVERED.value
            )
        )
        
        success_result = await self.db.execute(success_query)
        successful_deliveries = success_result.scalar() or 0
        
        return round((successful_deliveries / total_deliveries) * 100, 2)