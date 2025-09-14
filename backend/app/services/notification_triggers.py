"""Notification trigger system for deployment and activity events."""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.deployment import Deployment, DeploymentStatus
from app.models.activity import Activity, ActivityType
from app.models.notification import Notification, NotificationPriority, NotificationCategory
from app.services.notification_service import NotificationService
from app.services.websocket_notification_manager import notification_websocket_manager

logger = logging.getLogger(__name__)


class NotificationTriggerService:
    """Service for handling automatic notification triggers."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = NotificationService(db)
        
        # Mention pattern for detecting @username mentions
        self.mention_pattern = re.compile(r'@([a-zA-Z0-9_.-]+)')
        
        # Activity keywords that trigger collaboration notifications
        self.collaboration_keywords = {
            'conflict': ['conflict', 'merge conflict', 'collision'],
            'help': ['help', 'stuck', 'issue', 'problem', 'error'],
            'review': ['review', 'feedback', 'check', 'look at'],
            'complete': ['done', 'finished', 'completed', 'ready']
        }
    
    async def handle_deployment_event(
        self,
        deployment: Deployment,
        event_type: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle deployment-related notification triggers.
        
        Args:
            deployment: Deployment object
            event_type: Type of deployment event (started, success, failed, etc.)
            additional_data: Additional event data
        """
        try:
            # Get repository and project information
            repository = await self._get_repository(deployment.repository_id)
            if not repository:
                logger.warning(f"Repository not found for deployment {deployment.id}")
                return
            
            project = await self._get_project(repository.project_id)
            if not project:
                logger.warning(f"Project not found for repository {repository.id}")
                return
            
            # Get project members to notify
            project_members = await self._get_project_members(project.id)
            
            if event_type == "deployment_started":
                await self._handle_deployment_started(deployment, repository, project, project_members)
            
            elif event_type == "deployment_success":
                await self._handle_deployment_success(deployment, repository, project, project_members)
            
            elif event_type == "deployment_failed":
                await self._handle_deployment_failure(deployment, repository, project, project_members, additional_data)
            
            elif event_type == "deployment_cancelled":
                await self._handle_deployment_cancelled(deployment, repository, project, project_members)
            
            logger.info(f"Processed deployment event {event_type} for deployment {deployment.id}")
        
        except Exception as e:
            logger.error(f"Error handling deployment event {event_type}: {str(e)}")
    
    async def handle_activity_event(
        self,
        activity: Activity,
        event_type: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle activity-related notification triggers.
        
        Args:
            activity: Activity object
            event_type: Type of activity event
            additional_data: Additional event data
        """
        try:
            # Get project and user information
            project = await self._get_project(activity.project_id)
            if not project:
                logger.warning(f"Project not found for activity {activity.id}")
                return
            
            user = await self._get_user(activity.user_id)
            if not user:
                logger.warning(f"User not found for activity {activity.id}")
                return
            
            # Get project members
            project_members = await self._get_project_members(project.id)
            
            if event_type == "activity_started":
                await self._handle_activity_started(activity, user, project, project_members)
            
            elif event_type == "conflict_detected":
                await self._handle_conflict_detected(activity, user, project, project_members, additional_data)
            
            elif event_type == "collaboration_opportunity":
                await self._handle_collaboration_opportunity(activity, user, project, project_members, additional_data)
            
            elif event_type == "mention_detected":
                await self._handle_mention_detected(activity, user, project, additional_data)
            
            logger.debug(f"Processed activity event {event_type} for activity {activity.id}")
        
        except Exception as e:\n            logger.error(f"Error handling activity event {event_type}: {str(e)}")
    
    async def detect_and_handle_mentions(
        self,
        content: str,
        source_user: User,
        project: Project,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Detect mentions in content and trigger notifications.
        
        Args:
            content: Text content to scan for mentions
            source_user: User who created the content
            project: Project context
            context: Additional context (activity, comment, etc.)
            
        Returns:
            List of mentioned usernames
        """
        try:
            # Find all mentions in the content
            mentions = self.mention_pattern.findall(content)
            
            if not mentions:
                return []
            
            # Get project members to validate mentions
            project_members = await self._get_project_members(project.id)
            member_usernames = {member.user.username.lower(): member.user for member in project_members}
            
            valid_mentions = []
            
            for mention in mentions:
                username_lower = mention.lower()
                if username_lower in member_usernames and username_lower != source_user.username.lower():
                    mentioned_user = member_usernames[username_lower]
                    
                    # Create mention notification
                    await self._create_mention_notification(
                        mentioned_user, source_user, project, content, context
                    )
                    
                    valid_mentions.append(mention)
            
            return valid_mentions
        
        except Exception as e:
            logger.error(f"Error detecting mentions: {str(e)}")
            return []
    
    async def handle_collaboration_trigger(
        self,
        trigger_type: str,
        project_id: str,
        user_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Handle collaboration-specific triggers.
        
        Args:
            trigger_type: Type of collaboration trigger
            project_id: Project ID
            user_id: User ID who triggered the event
            data: Trigger data
        """
        try:
            project = await self._get_project(project_id)
            user = await self._get_user(user_id)
            
            if not project or not user:
                return
            
            project_members = await self._get_project_members(project.id)
            
            if trigger_type == "help_requested":
                await self._handle_help_request(user, project, project_members, data)
            
            elif trigger_type == "work_completed":
                await self._handle_work_completion(user, project, project_members, data)
            
            elif trigger_type == "review_requested":
                await self._handle_review_request(user, project, project_members, data)
            
            elif trigger_type == "critical_path_update":
                await self._handle_critical_path_update(user, project, project_members, data)
            
        except Exception as e:
            logger.error(f"Error handling collaboration trigger {trigger_type}: {str(e)}")
    
    # Deployment event handlers
    
    async def _handle_deployment_started(
        self,
        deployment: Deployment,
        repository: Any,
        project: Project,
        members: List[Any]
    ) -> None:
        """Handle deployment started notifications."""
        notification_data = {
            "type": "deployment_started",
            "title": f"Deployment Started - {repository.name}",
            "message": f"Deployment of {repository.name} to {deployment.environment} has started",
            "priority": NotificationPriority.MEDIUM,
            "category": NotificationCategory.DEPLOYMENT,
            "action_url": f"/projects/{project.id}/deployments/{deployment.id}",
            "action_text": "View Deployment",
            "data": {
                "deployment_id": str(deployment.id),
                "repository_id": str(repository.id),
                "branch": deployment.branch,
                "commit_hash": deployment.commit_hash[:8]
            }
        }
        
        # Notify repository owner and interested members
        interested_users = await self._get_interested_users(repository.id, "deployment")
        
        for user in interested_users:
            await self.notification_service.create_notification(
                user_id=user.id,
                project_id=project.id,
                **notification_data
            )
    
    async def _handle_deployment_success(
        self,
        deployment: Deployment,
        repository: Any,
        project: Project,
        members: List[Any]
    ) -> None:
        """Handle successful deployment notifications."""
        notification_data = {
            "type": "deployment_success",
            "title": f"✅ Deployment Successful - {repository.name}",
            "message": f"{repository.name} has been successfully deployed to {deployment.environment}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.DEPLOYMENT,
            "action_url": deployment.url or f"/projects/{project.id}/deployments/{deployment.id}",
            "action_text": "View Live Site" if deployment.url else "View Deployment",
            "data": {
                "deployment_id": str(deployment.id),
                "repository_id": str(repository.id),
                "preview_url": deployment.url,
                "branch": deployment.branch,
                "commit_hash": deployment.commit_hash[:8],
                "duration": str(deployment.completed_at - deployment.started_at) if deployment.completed_at else None
            }
        }
        
        # Notify all project members about successful deployment
        for member in members:
            await self.notification_service.create_notification(
                user_id=member.user_id,
                project_id=project.id,
                **notification_data
            )
        
        # Send real-time WebSocket notification
        await notification_websocket_manager.send_deployment_update(
            {
                "id": str(deployment.id),
                "status": "success",
                "url": deployment.url,
                "repository_name": repository.name,
                "branch": deployment.branch
            },
            [str(member.user_id) for member in members]
        )
    
    async def _handle_deployment_failure(
        self,
        deployment: Deployment,
        repository: Any,
        project: Project,
        members: List[Any],
        error_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle failed deployment notifications."""
        error_summary = "Unknown error"
        if error_data and "error" in error_data:
            error_summary = str(error_data["error"])[:100] + "..." if len(str(error_data["error"])) > 100 else str(error_data["error"])
        
        notification_data = {
            "type": "deployment_failed",
            "title": f"❌ Deployment Failed - {repository.name}",
            "message": f"Deployment of {repository.name} failed: {error_summary}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.DEPLOYMENT,
            "action_url": f"/projects/{project.id}/deployments/{deployment.id}",
            "action_text": "View Error Details",
            "data": {
                "deployment_id": str(deployment.id),
                "repository_id": str(repository.id),
                "error": error_summary,
                "branch": deployment.branch,
                "commit_hash": deployment.commit_hash[:8],
                "logs": deployment.logs[-5:] if deployment.logs else []  # Last 5 log entries
            }
        }
        
        # Notify repository owner and interested members with high priority
        interested_users = await self._get_interested_users(repository.id, "deployment")
        
        for user in interested_users:
            await self.notification_service.create_notification(
                user_id=user.id,
                project_id=project.id,
                **notification_data
            )
        
        # Send real-time WebSocket notification
        await notification_websocket_manager.send_deployment_update(
            {
                "id": str(deployment.id),
                "status": "failed",
                "error": error_summary,
                "repository_name": repository.name,
                "branch": deployment.branch
            },
            [str(user.id) for user in interested_users]
        )
    
    async def _handle_deployment_cancelled(
        self,
        deployment: Deployment,
        repository: Any,
        project: Project,
        members: List[Any]
    ) -> None:
        """Handle cancelled deployment notifications."""
        notification_data = {
            "type": "deployment_cancelled",
            "title": f"⏹️ Deployment Cancelled - {repository.name}",
            "message": f"Deployment of {repository.name} was cancelled",
            "priority": NotificationPriority.MEDIUM,
            "category": NotificationCategory.DEPLOYMENT,
            "action_url": f"/projects/{project.id}/deployments/{deployment.id}",
            "action_text": "View Details",
            "data": {
                "deployment_id": str(deployment.id),
                "repository_id": str(repository.id),
                "branch": deployment.branch,
                "commit_hash": deployment.commit_hash[:8]
            }
        }
        
        # Notify interested users
        interested_users = await self._get_interested_users(repository.id, "deployment")
        
        for user in interested_users:
            await self.notification_service.create_notification(
                user_id=user.id,
                project_id=project.id,
                **notification_data
            )
    
    # Activity event handlers
    
    async def _handle_activity_started(
        self,
        activity: Activity,
        user: User,
        project: Project,
        members: List[Any]
    ) -> None:
        """Handle activity started notifications."""
        # Check if other members are interested in this location/component
        interested_members = await self._get_members_interested_in_location(
            project.id, activity.location, exclude_user_id=user.id
        )
        
        if not interested_members:
            return
        
        notification_data = {
            "type": "activity_started",
            "title": f"👤 {user.name} started working",
            "message": f"{user.name} is now working on {activity.location}",
            "priority": NotificationPriority.LOW,
            "category": NotificationCategory.ACTIVITY,
            "action_url": f"/projects/{project.id}/activity",
            "action_text": "View Activity",
            "data": {
                "activity_id": str(activity.id),
                "user_id": str(user.id),
                "location": activity.location,
                "activity_type": activity.type
            }
        }
        
        for member in interested_members:
            await self.notification_service.create_notification(
                user_id=member.user_id,
                project_id=project.id,
                **notification_data
            )
    
    async def _handle_conflict_detected(
        self,
        activity: Activity,
        user: User,
        project: Project,
        members: List[Any],
        conflict_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle conflict detection notifications."""
        conflicting_users = conflict_data.get("conflicting_users", []) if conflict_data else []
        
        notification_data = {
            "type": "conflict_detected",
            "title": f"⚠️ Potential Conflict Detected",
            "message": f"Multiple team members are working on {activity.location}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.COLLABORATION,
            "action_url": f"/projects/{project.id}/conflicts",
            "action_text": "Resolve Conflict",
            "data": {
                "activity_id": str(activity.id),
                "location": activity.location,
                "conflicting_users": conflicting_users,
                "severity": conflict_data.get("severity", "medium") if conflict_data else "medium"
            }
        }
        
        # Notify all conflicting users
        for user_id in conflicting_users:
            await self.notification_service.create_notification(
                user_id=user_id,
                project_id=project.id,
                **notification_data
            )
    
    async def _handle_collaboration_opportunity(
        self,
        activity: Activity,
        user: User,
        project: Project,
        members: List[Any],
        opportunity_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle collaboration opportunity notifications."""
        related_users = opportunity_data.get("related_users", []) if opportunity_data else []
        
        notification_data = {
            "type": "collaboration_opportunity",
            "title": f"🤝 Collaboration Opportunity",
            "message": f"You and {user.name} are working on related components",
            "priority": NotificationPriority.MEDIUM,
            "category": NotificationCategory.COLLABORATION,
            "action_url": f"/projects/{project.id}/activity",
            "action_text": "View Details",
            "data": {
                "activity_id": str(activity.id),
                "initiator_user_id": str(user.id),
                "related_location": activity.location,
                "opportunity_type": opportunity_data.get("type", "related_work") if opportunity_data else "related_work"
            }
        }
        
        # Notify related users
        for user_id in related_users:
            if user_id != str(user.id):  # Don't notify the initiator
                await self.notification_service.create_notification(
                    user_id=user_id,
                    project_id=project.id,
                    **notification_data
                )
    
    async def _handle_mention_detected(
        self,
        activity: Activity,
        user: User,
        project: Project,
        mention_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle mention detection in activity content."""
        if not mention_data or "content" not in mention_data:
            return
        
        content = mention_data["content"]
        context = mention_data.get("context", {})
        
        # Detect and handle mentions
        await self.detect_and_handle_mentions(content, user, project, context)
    
    # Collaboration trigger handlers
    
    async def _handle_help_request(
        self,
        user: User,
        project: Project,
        members: List[Any],
        data: Dict[str, Any]
    ) -> None:
        """Handle help request notifications."""
        notification_data = {
            "type": "help_requested",
            "title": f"🆘 Help Requested",
            "message": f"{user.name} needs help with {data.get('component', 'their work')}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.COLLABORATION,
            "action_url": f"/projects/{project.id}/help/{data.get('request_id', '')}",
            "action_text": "Offer Help",
            "data": {
                "requester_id": str(user.id),
                "component": data.get("component"),
                "description": data.get("description"),
                "urgency": data.get("urgency", "medium")
            }
        }
        
        # Notify all other project members
        for member in members:
            if member.user_id != user.id:
                await self.notification_service.create_notification(
                    user_id=member.user_id,
                    project_id=project.id,
                    **notification_data
                )
    
    async def _handle_work_completion(
        self,
        user: User,
        project: Project,
        members: List[Any],
        data: Dict[str, Any]
    ) -> None:
        """Handle work completion notifications."""
        notification_data = {
            "type": "work_completed",
            "title": f"✅ Work Completed",
            "message": f"{user.name} completed work on {data.get('component', 'a component')}",
            "priority": NotificationPriority.MEDIUM,
            "category": NotificationCategory.ACTIVITY,
            "action_url": f"/projects/{project.id}/activity",
            "action_text": "View Details",
            "data": {
                "completer_id": str(user.id),
                "component": data.get("component"),
                "completion_type": data.get("type", "task")
            }
        }
        
        # Notify interested team members
        interested_members = await self._get_members_interested_in_location(
            project.id, data.get("component", ""), exclude_user_id=user.id
        )
        
        for member in interested_members:
            await self.notification_service.create_notification(
                user_id=member.user_id,
                project_id=project.id,
                **notification_data
            )
    
    async def _handle_review_request(
        self,
        user: User,
        project: Project,
        members: List[Any],
        data: Dict[str, Any]
    ) -> None:
        """Handle review request notifications."""
        reviewers = data.get("reviewers", [])
        
        notification_data = {
            "type": "review_requested",
            "title": f"👀 Review Requested",
            "message": f"{user.name} requested a review of {data.get('component', 'their work')}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.COLLABORATION,
            "action_url": f"/projects/{project.id}/reviews/{data.get('review_id', '')}",
            "action_text": "Start Review",
            "data": {
                "requester_id": str(user.id),
                "component": data.get("component"),
                "review_type": data.get("type", "code"),
                "deadline": data.get("deadline")
            }
        }
        
        # Notify specific reviewers or all members if no specific reviewers
        target_users = reviewers if reviewers else [member.user_id for member in members if member.user_id != user.id]
        
        for user_id in target_users:
            await self.notification_service.create_notification(
                user_id=user_id,
                project_id=project.id,
                **notification_data
            )
    
    async def _handle_critical_path_update(
        self,
        user: User,
        project: Project,
        members: List[Any],
        data: Dict[str, Any]
    ) -> None:
        """Handle critical path update notifications."""
        notification_data = {
            "type": "critical_path_update",
            "title": f"🔥 Critical Path Update",
            "message": f"{user.name} is working on critical path item: {data.get('item', 'Unknown')}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.ACTIVITY,
            "action_url": f"/projects/{project.id}/critical-path",
            "action_text": "View Critical Path",
            "data": {
                "user_id": str(user.id),
                "item": data.get("item"),
                "priority_level": data.get("priority", "high"),
                "estimated_completion": data.get("estimated_completion")
            }
        }
        
        # Notify all project members about critical path updates
        for member in members:
            if member.user_id != user.id:
                await self.notification_service.create_notification(
                    user_id=member.user_id,
                    project_id=project.id,
                    **notification_data
                )
    
    # Helper methods
    
    async def _create_mention_notification(
        self,
        mentioned_user: User,
        source_user: User,
        project: Project,
        content: str,
        context: Dict[str, Any]
    ) -> None:
        """Create a mention notification."""
        # Truncate content for notification
        content_preview = content[:100] + "..." if len(content) > 100 else content
        
        notification_data = {
            "type": "mention",
            "title": f"💬 You were mentioned",
            "message": f"{source_user.name} mentioned you: {content_preview}",
            "priority": NotificationPriority.HIGH,
            "category": NotificationCategory.COLLABORATION,
            "action_url": context.get("url", f"/projects/{project.id}"),
            "action_text": "View Message",
            "data": {
                "source_user_id": str(source_user.id),
                "content": content,
                "context_type": context.get("type", "comment"),
                "context_id": context.get("id")
            }
        }
        
        await self.notification_service.create_notification(
            user_id=mentioned_user.id,
            project_id=project.id,
            **notification_data
        )
    
    async def _get_repository(self, repository_id: str) -> Optional[Any]:
        """Get repository by ID."""
        # This would be implemented based on your repository model
        # For now, returning a mock object
        return type('Repository', (), {
            'id': repository_id,
            'name': 'sample-repo',
            'project_id': 'project-123'
        })()
    
    async def _get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        try:
            result = await self.db.execute(
                select(Project).where(Project.id == project_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}")
            return None
    
    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None
    
    async def _get_project_members(self, project_id: str) -> List[Any]:
        """Get all members of a project."""
        try:
            result = await self.db.execute(
                select(ProjectMember).where(ProjectMember.project_id == project_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting project members for {project_id}: {str(e)}")
            return []
    
    async def _get_interested_users(self, repository_id: str, event_type: str) -> List[User]:
        """Get users interested in specific repository events."""
        # This would check user preferences and project membership
        # For now, returning empty list - would be implemented based on user preferences model
        return []
    
    async def _get_members_interested_in_location(
        self,
        project_id: str,
        location: str,
        exclude_user_id: Optional[str] = None
    ) -> List[Any]:
        """Get project members interested in a specific location/component."""
        # This would check user activity history and preferences
        # For now, returning empty list - would be implemented based on activity patterns
        return []


# Global notification trigger service instance
notification_trigger_service = None

def get_notification_trigger_service(db: AsyncSession) -> NotificationTriggerService:
    """Get notification trigger service instance."""
    return NotificationTriggerService(db)