"""Event handlers for automatic notification triggering."""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment, DeploymentStatus
from app.models.activity import Activity
from app.models.user import User
from app.models.project import Project
from app.services.notification_triggers import get_notification_trigger_service

logger = logging.getLogger(__name__)


class EventHandlerService:
    """Service for handling events and triggering notifications automatically."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.trigger_service = get_notification_trigger_service(db)
    
    async def on_deployment_status_changed(
        self,
        deployment: Deployment,
        old_status: DeploymentStatus,
        new_status: DeploymentStatus,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle deployment status changes and trigger appropriate notifications.
        
        Args:
            deployment: Deployment object
            old_status: Previous deployment status
            new_status: New deployment status
            error_details: Error details if deployment failed
        """
        try:
            event_type = None
            additional_data = {}
            
            # Map deployment status to event type
            if new_status == DeploymentStatus.BUILDING and old_status == DeploymentStatus.PENDING:
                event_type = "deployment_started"
            elif new_status == DeploymentStatus.SUCCESS:
                event_type = "deployment_success"
                if deployment.completed_at and deployment.started_at:
                    duration = (deployment.completed_at - deployment.started_at).total_seconds()
                    additional_data["duration"] = duration
            elif new_status == DeploymentStatus.FAILED:
                event_type = "deployment_failed"
                if error_details:
                    additional_data["error"] = error_details
            
            if event_type:
                await self.trigger_service.handle_deployment_event(
                    deployment, event_type, additional_data
                )
                logger.info(f"Triggered {event_type} for deployment {deployment.id}")
        
        except Exception as e:
            logger.error(f"Error handling deployment status change: {str(e)}")
    
    async def on_deployment_created(self, deployment: Deployment) -> None:
        """
        Handle new deployment creation.
        
        Args:
            deployment: Newly created deployment
        """
        try:
            await self.trigger_service.handle_deployment_event(
                deployment, "deployment_started", {}
            )
            logger.info(f"Triggered deployment_started for new deployment {deployment.id}")
        
        except Exception as e:
            logger.error(f"Error handling deployment creation: {str(e)}")
    
    async def on_deployment_cancelled(self, deployment: Deployment) -> None:
        """
        Handle deployment cancellation.
        
        Args:
            deployment: Cancelled deployment
        """
        try:
            await self.trigger_service.handle_deployment_event(
                deployment, "deployment_cancelled", {}
            )
            logger.info(f"Triggered deployment_cancelled for deployment {deployment.id}")
        
        except Exception as e:
            logger.error(f"Error handling deployment cancellation: {str(e)}")
    
    async def on_activity_created(self, activity: Activity) -> None:
        """
        Handle new activity creation and check for collaboration opportunities.
        
        Args:
            activity: Newly created activity
        """
        try:
            # Trigger activity started notification
            await self.trigger_service.handle_activity_event(
                activity, "activity_started", {}
            )
            
            # Check for potential conflicts
            await self._check_for_conflicts(activity)
            
            # Check for collaboration opportunities
            await self._check_for_collaboration_opportunities(activity)
            
            logger.debug(f"Processed activity creation for activity {activity.id}")
        
        except Exception as e:
            logger.error(f"Error handling activity creation: {str(e)}")
    
    async def on_activity_updated(
        self,
        activity: Activity,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> None:
        """
        Handle activity updates and detect changes that require notifications.
        
        Args:
            activity: Updated activity
            old_data: Previous activity data
            new_data: New activity data
        """
        try:
            # Check if location changed (potential conflict)
            if old_data.get("location") != new_data.get("location"):
                await self._check_for_conflicts(activity)
            
            # Check if activity type changed to something that requires attention
            if (old_data.get("type") != new_data.get("type") and 
                new_data.get("type") in ["reviewing", "testing"]):
                await self._handle_activity_type_change(activity, new_data.get("type"))
            
            logger.debug(f"Processed activity update for activity {activity.id}")
        
        except Exception as e:
            logger.error(f"Error handling activity update: {str(e)}")
    
    async def on_user_status_changed(
        self,
        user: User,
        old_status: str,
        new_status: str,
        project_id: Optional[str] = None
    ) -> None:
        """
        Handle user status changes and notify team members.
        
        Args:
            user: User whose status changed
            old_status: Previous status
            new_status: New status
            project_id: Project context (optional)
        """
        try:
            # Only notify for significant status changes
            if old_status == "offline" and new_status == "online":
                await self._handle_user_came_online(user, project_id)
            elif old_status in ["online", "away"] and new_status == "offline":
                await self._handle_user_went_offline(user, project_id)
            
            logger.debug(f"Processed status change for user {user.id}: {old_status} -> {new_status}")
        
        except Exception as e:
            logger.error(f"Error handling user status change: {str(e)}")
    
    async def on_comment_created(
        self,
        comment_content: str,
        author: User,
        project: Project,
        context: Dict[str, Any]
    ) -> None:
        """
        Handle new comment creation and detect mentions.
        
        Args:
            comment_content: Comment text content
            author: Comment author
            project: Project context
            context: Additional context (activity, issue, etc.)
        """
        try:
            # Detect and handle mentions
            mentions = await self.trigger_service.detect_and_handle_mentions(
                comment_content, author, project, context
            )
            
            if mentions:
                logger.info(f"Processed {len(mentions)} mentions in comment by {author.id}")
            
            # Check for help requests or other collaboration keywords
            await self._analyze_comment_for_collaboration_triggers(
                comment_content, author, project, context
            )
        
        except Exception as e:
            logger.error(f"Error handling comment creation: {str(e)}")
    
    async def on_repository_push(
        self,
        repository_id: str,
        branch: str,
        commit_data: Dict[str, Any],
        user: User
    ) -> None:
        """
        Handle repository push events and trigger deployment if configured.
        
        Args:
            repository_id: Repository ID
            branch: Branch that was pushed to
            commit_data: Commit information
            user: User who pushed
        """
        try:
            # This would typically trigger a deployment
            # For now, we'll just log the event
            logger.info(f"Repository push detected: {repository_id}/{branch} by {user.id}")
            
            # If this is a push to main/master, it might trigger deployment notifications
            if branch in ["main", "master", "production"]:
                # This would integrate with the deployment service
                # await self._trigger_auto_deployment(repository_id, branch, commit_data, user)
                pass
        
        except Exception as e:
            logger.error(f"Error handling repository push: {str(e)}")
    
    # Private helper methods
    
    async def _check_for_conflicts(self, activity: Activity) -> None:
        """Check if the new activity conflicts with existing activities."""
        try:
            # Get recent activities in the same location
            from sqlalchemy import select, and_
            from datetime import timedelta
            
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            
            result = await self.db.execute(
                select(Activity).where(
                    and_(
                        Activity.project_id == activity.project_id,
                        Activity.location == activity.location,
                        Activity.user_id != activity.user_id,
                        Activity.timestamp > five_minutes_ago
                    )
                )
            )
            
            conflicting_activities = result.scalars().all()
            
            if conflicting_activities:
                conflicting_users = [str(a.user_id) for a in conflicting_activities] + [str(activity.user_id)]
                
                await self.trigger_service.handle_activity_event(
                    activity,
                    "conflict_detected",
                    {
                        "conflicting_users": conflicting_users,
                        "severity": "medium",
                        "conflict_type": "concurrent_work"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error checking for conflicts: {str(e)}")
    
    async def _check_for_collaboration_opportunities(self, activity: Activity) -> None:
        """Check for collaboration opportunities based on activity patterns."""
        try:
            # Look for related work in similar locations or components
            related_locations = self._get_related_locations(activity.location)
            
            if related_locations:
                from sqlalchemy import select, and_, or_
                from datetime import timedelta
                
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                
                result = await self.db.execute(
                    select(Activity).where(
                        and_(
                            Activity.project_id == activity.project_id,
                            Activity.user_id != activity.user_id,
                            Activity.timestamp > one_hour_ago,
                            or_(*[Activity.location.like(f"%{loc}%") for loc in related_locations])
                        )
                    )
                )
                
                related_activities = result.scalars().all()
                
                if related_activities:
                    related_users = [str(a.user_id) for a in related_activities]
                    
                    await self.trigger_service.handle_activity_event(
                        activity,
                        "collaboration_opportunity",
                        {
                            "related_users": related_users,
                            "type": "related_work",
                            "related_locations": related_locations
                        }
                    )
        
        except Exception as e:
            logger.error(f"Error checking for collaboration opportunities: {str(e)}")
    
    def _get_related_locations(self, location: str) -> List[str]:
        """Get locations related to the given location."""
        # Simple heuristic: look for files in the same directory or with similar names
        related = []
        
        if "/" in location:
            # Same directory
            directory = "/".join(location.split("/")[:-1])
            related.append(directory)
        
        # Similar file names (same base name, different extensions)
        if "." in location:
            base_name = ".".join(location.split(".")[:-1])
            related.append(base_name)
        
        return related
    
    async def _handle_activity_type_change(self, activity: Activity, new_type: str) -> None:
        """Handle activity type changes that might require notifications."""
        try:
            if new_type == "reviewing":
                # Someone started reviewing - notify the original author
                await self.trigger_service.handle_collaboration_trigger(
                    "review_started",
                    activity.project_id,
                    activity.user_id,
                    {
                        "component": activity.location,
                        "review_type": "code"
                    }
                )
            elif new_type == "testing":
                # Someone started testing - might be relevant to others
                await self.trigger_service.handle_collaboration_trigger(
                    "testing_started",
                    activity.project_id,
                    activity.user_id,
                    {
                        "component": activity.location,
                        "test_type": "manual"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error handling activity type change: {str(e)}")
    
    async def _handle_user_came_online(self, user: User, project_id: Optional[str]) -> None:
        """Handle user coming online."""
        # Could notify team members that someone is now available
        # For now, just log it
        logger.debug(f"User {user.id} came online in project {project_id}")
    
    async def _handle_user_went_offline(self, user: User, project_id: Optional[str]) -> None:
        """Handle user going offline."""
        # Could notify if they were working on something critical
        # For now, just log it
        logger.debug(f"User {user.id} went offline in project {project_id}")
    
    async def _analyze_comment_for_collaboration_triggers(
        self,
        content: str,
        author: User,
        project: Project,
        context: Dict[str, Any]
    ) -> None:
        """Analyze comment content for collaboration triggers."""
        try:
            content_lower = content.lower()
            
            # Check for help requests
            help_keywords = ["help", "stuck", "issue", "problem", "error", "can't", "unable"]
            if any(keyword in content_lower for keyword in help_keywords):
                await self.trigger_service.handle_collaboration_trigger(
                    "help_requested",
                    project.id,
                    str(author.id),
                    {
                        "component": context.get("location", "unknown"),
                        "description": content[:200],  # First 200 chars
                        "urgency": "medium"
                    }
                )
            
            # Check for review requests
            review_keywords = ["review", "feedback", "check", "look at", "thoughts"]
            if any(keyword in content_lower for keyword in review_keywords):
                await self.trigger_service.handle_collaboration_trigger(
                    "review_requested",
                    project.id,
                    str(author.id),
                    {
                        "component": context.get("location", "unknown"),
                        "description": content[:200],
                        "type": "peer_review"
                    }
                )
            
            # Check for completion announcements
            completion_keywords = ["done", "finished", "completed", "ready"]
            if any(keyword in content_lower for keyword in completion_keywords):
                await self.trigger_service.handle_collaboration_trigger(
                    "work_completed",
                    project.id,
                    str(author.id),
                    {
                        "component": context.get("location", "unknown"),
                        "type": "task"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error analyzing comment for collaboration triggers: {str(e)}")


# Global event handler service
def get_event_handler_service(db: AsyncSession) -> EventHandlerService:
    """Get event handler service instance."""
    return EventHandlerService(db)