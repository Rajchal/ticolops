"""Notification service for team collaboration and project updates."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from enum import Enum

from app.models.user import User
from app.models.project import Project, project_members
from app.core.exceptions import NotFoundError


class NotificationType(str, Enum):
    """Notification type enumeration."""
    PROJECT_INVITATION = "project_invitation"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    SETTINGS_CHANGED = "settings_changed"
    FILE_CREATED = "file_created"
    FILE_UPDATED = "file_updated"
    FILE_DELETED = "file_deleted"
    DEPLOYMENT_SUCCESS = "deployment_success"
    DEPLOYMENT_FAILED = "deployment_failed"
    MENTION = "mention"
    CONFLICT_DETECTED = "conflict_detected"
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationService:
    """Service for managing team notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        notification_type: NotificationType,
        recipient_id: str,
        title: str,
        message: str,
        project_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Create a new notification.
        
        Args:
            notification_type: Type of notification
            recipient_id: User ID to receive notification
            title: Notification title
            message: Notification message
            project_id: Related project ID (optional)
            actor_id: User ID who triggered the notification (optional)
            metadata: Additional notification data (optional)
            priority: Notification priority level
            
        Returns:
            Created notification data
        """
        notification = {
            "id": str(UUID()),
            "type": notification_type.value,
            "recipient_id": recipient_id,
            "title": title,
            "message": message,
            "project_id": project_id,
            "actor_id": actor_id,
            "metadata": metadata or {},
            "priority": priority.value,
            "read": False,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30)  # Notifications expire after 30 days
        }
        
        # In a real implementation, this would be stored in a notifications table
        # For now, we'll return the notification data
        
        # TODO: Send real-time notification via WebSocket
        await self._send_realtime_notification(notification)
        
        # TODO: Send email notification if user preferences allow
        await self._send_email_notification(notification)
        
        return notification

    async def create_project_invitation_notification(
        self,
        project_id: str,
        recipient_email: str,
        inviter_id: str,
        role: str
    ) -> Dict[str, Any]:
        """Create notification for project invitation."""
        # Get project and inviter details
        project_query = select(Project).where(Project.id == UUID(project_id))
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        inviter_query = select(User).where(User.id == UUID(inviter_id))
        inviter_result = await self.db.execute(inviter_query)
        inviter = inviter_result.scalar_one_or_none()
        
        if not project or not inviter:
            raise NotFoundError("Project or inviter not found")
        
        # Get recipient user
        recipient_query = select(User).where(User.email == recipient_email)
        recipient_result = await self.db.execute(recipient_query)
        recipient = recipient_result.scalar_one_or_none()
        
        if not recipient:
            raise NotFoundError("Recipient user not found")
        
        return await self.create_notification(
            notification_type=NotificationType.PROJECT_INVITATION,
            recipient_id=str(recipient.id),
            title=f"Project Invitation: {project.name}",
            message=f"{inviter.name} invited you to join the project '{project.name}' as a {role}.",
            project_id=project_id,
            actor_id=inviter_id,
            metadata={
                "project_name": project.name,
                "inviter_name": inviter.name,
                "role": role,
                "invitation_link": f"/projects/{project_id}/join"
            },
            priority=NotificationPriority.HIGH
        )

    async def create_member_activity_notification(
        self,
        project_id: str,
        actor_id: str,
        activity_type: str,
        activity_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create notifications for member activity."""
        # Get project members (excluding the actor)
        members_query = (
            select(User, project_members.c.role)
            .join(project_members, User.id == project_members.c.user_id)
            .where(
                and_(
                    project_members.c.project_id == UUID(project_id),
                    project_members.c.user_id != UUID(actor_id)
                )
            )
        )
        
        members_result = await self.db.execute(members_query)
        members = members_result.all()
        
        # Get actor details
        actor_query = select(User).where(User.id == UUID(actor_id))
        actor_result = await self.db.execute(actor_query)
        actor = actor_result.scalar_one_or_none()
        
        if not actor:
            return []
        
        notifications = []
        
        for member, role in members:
            # Create notification based on activity type
            if activity_type == "file_created":
                title = f"New file: {activity_details.get('file_name', 'Unknown')}"
                message = f"{actor.name} created a new file in the project."
                notification_type = NotificationType.FILE_CREATED
            elif activity_type == "file_updated":
                title = f"File updated: {activity_details.get('file_name', 'Unknown')}"
                message = f"{actor.name} updated a file in the project."
                notification_type = NotificationType.FILE_UPDATED
            elif activity_type == "member_joined":
                title = "New team member"
                message = f"{actor.name} joined the project."
                notification_type = NotificationType.MEMBER_JOINED
            else:
                continue  # Skip unknown activity types
            
            notification = await self.create_notification(
                notification_type=notification_type,
                recipient_id=str(member.id),
                title=title,
                message=message,
                project_id=project_id,
                actor_id=actor_id,
                metadata=activity_details,
                priority=NotificationPriority.LOW
            )
            
            notifications.append(notification)
        
        return notifications

    async def create_settings_change_notification(
        self,
        project_id: str,
        actor_id: str,
        changes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create notifications for project settings changes."""
        # Get project members (excluding the actor)
        members_query = (
            select(User)
            .join(project_members, User.id == project_members.c.user_id)
            .where(
                and_(
                    project_members.c.project_id == UUID(project_id),
                    project_members.c.user_id != UUID(actor_id)
                )
            )
        )
        
        members_result = await self.db.execute(members_query)
        members = members_result.scalars().all()
        
        # Get actor and project details
        actor_query = select(User).where(User.id == UUID(actor_id))
        actor_result = await self.db.execute(actor_query)
        actor = actor_result.scalar_one_or_none()
        
        project_query = select(Project).where(Project.id == UUID(project_id))
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not actor or not project:
            return []
        
        notifications = []
        
        # Create summary of changes
        change_summary = ", ".join([change["setting"] for change in changes])
        
        for member in members:
            notification = await self.create_notification(
                notification_type=NotificationType.SETTINGS_CHANGED,
                recipient_id=str(member.id),
                title=f"Project settings updated: {project.name}",
                message=f"{actor.name} updated project settings: {change_summary}",
                project_id=project_id,
                actor_id=actor_id,
                metadata={
                    "changes": changes,
                    "project_name": project.name,
                    "actor_name": actor.name
                },
                priority=NotificationPriority.MEDIUM
            )
            
            notifications.append(notification)
        
        return notifications

    async def create_deployment_notification(
        self,
        project_id: str,
        deployment_id: str,
        status: str,
        deployed_by: str,
        deployment_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Create notifications for deployment status."""
        # Get project members
        members_query = (
            select(User)
            .join(project_members, User.id == project_members.c.user_id)
            .where(project_members.c.project_id == UUID(project_id))
        )
        
        members_result = await self.db.execute(members_query)
        members = members_result.scalars().all()
        
        # Get deployer and project details
        deployer_query = select(User).where(User.id == UUID(deployed_by))
        deployer_result = await self.db.execute(deployer_query)
        deployer = deployer_result.scalar_one_or_none()
        
        project_query = select(Project).where(Project.id == UUID(project_id))
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not deployer or not project:
            return []
        
        notifications = []
        
        # Determine notification details based on status
        if status == "success":
            title = f"Deployment successful: {project.name}"
            message = f"{deployer.name} successfully deployed the project."
            notification_type = NotificationType.DEPLOYMENT_SUCCESS
            priority = NotificationPriority.MEDIUM
        else:
            title = f"Deployment failed: {project.name}"
            message = f"Deployment by {deployer.name} failed."
            notification_type = NotificationType.DEPLOYMENT_FAILED
            priority = NotificationPriority.HIGH
        
        for member in members:
            notification = await self.create_notification(
                notification_type=notification_type,
                recipient_id=str(member.id),
                title=title,
                message=message,
                project_id=project_id,
                actor_id=deployed_by,
                metadata={
                    "deployment_id": deployment_id,
                    "deployment_url": deployment_url,
                    "error_message": error_message,
                    "project_name": project.name,
                    "deployer_name": deployer.name
                },
                priority=priority
            )
            
            notifications.append(notification)
        
        return notifications

    async def create_conflict_notification(
        self,
        project_id: str,
        file_path: str,
        conflicting_users: List[str]
    ) -> List[Dict[str, Any]]:
        """Create notifications for file conflicts."""
        notifications = []
        
        # Get user details
        users_query = select(User).where(User.id.in_([UUID(uid) for uid in conflicting_users]))
        users_result = await self.db.execute(users_query)
        users = users_result.scalars().all()
        
        user_names = [user.name for user in users]
        
        for user in users:
            other_users = [name for name in user_names if name != user.name]
            other_users_str = ", ".join(other_users)
            
            notification = await self.create_notification(
                notification_type=NotificationType.CONFLICT_DETECTED,
                recipient_id=str(user.id),
                title=f"Conflict detected: {file_path}",
                message=f"You and {other_users_str} are working on the same file. Consider coordinating to avoid conflicts.",
                project_id=project_id,
                metadata={
                    "file_path": file_path,
                    "conflicting_users": conflicting_users,
                    "other_users": other_users
                },
                priority=NotificationPriority.HIGH
            )
            
            notifications.append(notification)
        
        return notifications

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        # In a real implementation, this would query a notifications table
        # For now, return empty list
        return []

    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        # In a real implementation, this would update the notification in the database
        return True

    async def mark_all_notifications_read(self, user_id: str, project_id: Optional[str] = None) -> int:
        """Mark all notifications as read for a user."""
        # In a real implementation, this would update multiple notifications
        return 0

    # Private helper methods
    async def _send_realtime_notification(self, notification: Dict[str, Any]):
        """Send real-time notification via WebSocket."""
        # TODO: Implement WebSocket notification sending
        # This would typically use Redis pub/sub or similar
        pass

    async def _send_email_notification(self, notification: Dict[str, Any]):
        """Send email notification if user preferences allow."""
        # TODO: Implement email notification sending
        # This would check user preferences and send email if enabled
        pass

    async def _get_user_notification_preferences(self, user_id: str) -> Dict[str, bool]:
        """Get user's notification preferences."""
        # TODO: Implement user notification preferences
        # For now, return default preferences
        return {
            "email_notifications": True,
            "push_notifications": True,
            "project_activity": True,
            "deployment_updates": True,
            "mentions": True,
            "conflicts": True
        }