"""Deployment notification service for failure alerts and recovery updates."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment, DeploymentStatus
from app.models.user import User
from app.models.project import Project
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of deployment notifications."""
    DEPLOYMENT_FAILED = "deployment_failed"
    DEPLOYMENT_RECOVERED = "deployment_recovered"
    AUTO_RETRY_INITIATED = "auto_retry_initiated"
    ROLLBACK_COMPLETED = "rollback_completed"
    HEALTH_ALERT = "health_alert"
    PATTERN_DETECTED = "pattern_detected"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SLACK = "slack"


class DeploymentNotificationService:
    """Service for sending deployment-related notifications."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def notify_deployment_failure(
        self,
        deployment: Deployment,
        error_analysis: Dict[str, Any],
        recovery_options: Dict[str, Any]
    ) -> None:
        """
        Send notification for deployment failure.
        
        Args:
            deployment: Failed deployment
            error_analysis: Error analysis results
            recovery_options: Available recovery options
        """
        try:
            # Get project and team members
            project_members = await self._get_project_members(deployment.project_id)
            
            # Create notification content
            notification_data = {
                "type": NotificationType.DEPLOYMENT_FAILED,
                "deployment_id": str(deployment.id),
                "repository_name": await self._get_repository_name(deployment.repository_id),
                "commit_sha": deployment.commit_sha[:8],
                "branch": deployment.branch,
                "error_category": error_analysis.get("category", "unknown"),
                "error_severity": error_analysis.get("severity", "medium"),
                "auto_retry_available": recovery_options.get("retry", False),
                "rollback_available": len(recovery_options.get("rollback_targets", [])) > 0,
                "troubleshooting_url": f"{settings.BASE_URL}/deployments/{deployment.id}/troubleshooting",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send notifications to team members
            for member in project_members:
                await self._send_notification(
                    user=member,
                    notification_type=NotificationType.DEPLOYMENT_FAILED,
                    data=notification_data,
                    channels=await self._get_user_notification_preferences(member.id)
                )
            
            logger.info(f"Sent deployment failure notifications for deployment {deployment.id}")
            
        except Exception as e:
            logger.error(f"Failed to send deployment failure notification: {str(e)}")
    
    async def notify_auto_retry_initiated(
        self,
        original_deployment: Deployment,
        new_deployment: Deployment
    ) -> None:
        """
        Send notification when auto-retry is initiated.
        
        Args:
            original_deployment: Original failed deployment
            new_deployment: New retry deployment
        """
        try:
            project_members = await self._get_project_members(original_deployment.project_id)
            
            notification_data = {
                "type": NotificationType.AUTO_RETRY_INITIATED,
                "original_deployment_id": str(original_deployment.id),
                "new_deployment_id": str(new_deployment.id),
                "repository_name": await self._get_repository_name(original_deployment.repository_id),
                "commit_sha": original_deployment.commit_sha[:8],
                "branch": original_deployment.branch,
                "retry_reason": "Automatic retry for transient failure",
                "monitor_url": f"{settings.BASE_URL}/deployments/{new_deployment.id}/status",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for member in project_members:
                await self._send_notification(
                    user=member,
                    notification_type=NotificationType.AUTO_RETRY_INITIATED,
                    data=notification_data,
                    channels=[NotificationChannel.IN_APP]  # Less urgent, in-app only
                )
            
            logger.info(f"Sent auto-retry notifications for deployment {original_deployment.id}")
            
        except Exception as e:
            logger.error(f"Failed to send auto-retry notification: {str(e)}")
    
    async def notify_rollback_completed(
        self,
        failed_deployment: Deployment,
        rollback_deployment: Deployment,
        target_deployment: Deployment
    ) -> None:
        """
        Send notification when rollback is completed.
        
        Args:
            failed_deployment: Original failed deployment
            rollback_deployment: Rollback deployment
            target_deployment: Target deployment that was rolled back to
        """
        try:
            project_members = await self._get_project_members(failed_deployment.project_id)
            
            notification_data = {
                "type": NotificationType.ROLLBACK_COMPLETED,
                "failed_deployment_id": str(failed_deployment.id),
                "rollback_deployment_id": str(rollback_deployment.id),
                "target_deployment_id": str(target_deployment.id),
                "repository_name": await self._get_repository_name(failed_deployment.repository_id),
                "rolled_back_to_commit": target_deployment.commit_sha[:8],
                "rollback_status": rollback_deployment.status,
                "preview_url": rollback_deployment.preview_url,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for member in project_members:
                await self._send_notification(
                    user=member,
                    notification_type=NotificationType.ROLLBACK_COMPLETED,
                    data=notification_data,
                    channels=await self._get_user_notification_preferences(member.id)
                )
            
            logger.info(f"Sent rollback completion notifications for deployment {failed_deployment.id}")
            
        except Exception as e:
            logger.error(f"Failed to send rollback notification: {str(e)}")
    
    async def notify_deployment_recovered(
        self,
        failed_deployment: Deployment,
        successful_deployment: Deployment
    ) -> None:
        """
        Send notification when deployment is successfully recovered.
        
        Args:
            failed_deployment: Original failed deployment
            successful_deployment: Successful recovery deployment
        """
        try:
            project_members = await self._get_project_members(failed_deployment.project_id)
            
            notification_data = {
                "type": NotificationType.DEPLOYMENT_RECOVERED,
                "failed_deployment_id": str(failed_deployment.id),
                "successful_deployment_id": str(successful_deployment.id),
                "repository_name": await self._get_repository_name(failed_deployment.repository_id),
                "commit_sha": successful_deployment.commit_sha[:8],
                "branch": successful_deployment.branch,
                "preview_url": successful_deployment.preview_url,
                "recovery_method": "retry" if failed_deployment.commit_sha == successful_deployment.commit_sha else "rollback",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for member in project_members:
                await self._send_notification(
                    user=member,
                    notification_type=NotificationType.DEPLOYMENT_RECOVERED,
                    data=notification_data,
                    channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
                )
            
            logger.info(f"Sent deployment recovery notifications for deployment {failed_deployment.id}")
            
        except Exception as e:
            logger.error(f"Failed to send recovery notification: {str(e)}")
    
    async def notify_health_alert(
        self,
        repository_id: str,
        health_data: Dict[str, Any],
        alert_level: str = "warning"
    ) -> None:
        """
        Send notification for deployment health alerts.
        
        Args:
            repository_id: Repository ID
            health_data: Health score and metrics
            alert_level: Alert severity level
        """
        try:
            # Get repository and project info
            repository_name = await self._get_repository_name(repository_id)
            project_id = await self._get_project_id_for_repository(repository_id)
            project_members = await self._get_project_members(project_id)
            
            notification_data = {
                "type": NotificationType.HEALTH_ALERT,
                "repository_id": repository_id,
                "repository_name": repository_name,
                "health_score": health_data["health_score"],
                "success_rate": health_data["success_rate"],
                "alert_level": alert_level,
                "recommendations": health_data["recommendations"][:3],  # Top 3 recommendations
                "dashboard_url": f"{settings.BASE_URL}/repositories/{repository_id}/health",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Only notify project owners and coordinators for health alerts
            for member in project_members:
                if member.role in ["owner", "coordinator"]:
                    await self._send_notification(
                        user=member,
                        notification_type=NotificationType.HEALTH_ALERT,
                        data=notification_data,
                        channels=[NotificationChannel.EMAIL]
                    )
            
            logger.info(f"Sent health alert notifications for repository {repository_id}")
            
        except Exception as e:
            logger.error(f"Failed to send health alert notification: {str(e)}")
    
    async def notify_failure_pattern_detected(
        self,
        repository_id: str,
        pattern_data: Dict[str, Any]
    ) -> None:
        """
        Send notification when recurring failure pattern is detected.
        
        Args:
            repository_id: Repository ID
            pattern_data: Pattern analysis data
        """
        try:
            repository_name = await self._get_repository_name(repository_id)
            project_id = await self._get_project_id_for_repository(repository_id)
            project_members = await self._get_project_members(project_id)
            
            top_pattern = pattern_data["failure_trends"][0] if pattern_data["failure_trends"] else None
            
            if not top_pattern or top_pattern["percentage"] < 50:
                return  # Only notify for significant patterns
            
            notification_data = {
                "type": NotificationType.PATTERN_DETECTED,
                "repository_id": repository_id,
                "repository_name": repository_name,
                "pattern_category": top_pattern["category"],
                "pattern_percentage": top_pattern["percentage"],
                "total_failures": pattern_data["total_failures"],
                "analysis_period": pattern_data["analysis_period_days"],
                "recommendations": pattern_data["recommendations"][:2],
                "patterns_url": f"{settings.BASE_URL}/repositories/{repository_id}/failure-patterns",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for member in project_members:
                await self._send_notification(
                    user=member,
                    notification_type=NotificationType.PATTERN_DETECTED,
                    data=notification_data,
                    channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
                )
            
            logger.info(f"Sent failure pattern notifications for repository {repository_id}")
            
        except Exception as e:
            logger.error(f"Failed to send pattern detection notification: {str(e)}")
    
    async def _send_notification(
        self,
        user: User,
        notification_type: NotificationType,
        data: Dict[str, Any],
        channels: List[NotificationChannel]
    ) -> None:
        """
        Send notification through specified channels.
        
        Args:
            user: User to notify
            notification_type: Type of notification
            data: Notification data
            channels: Delivery channels
        """
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    await self._send_email_notification(user, notification_type, data)
                elif channel == NotificationChannel.IN_APP:
                    await self._send_in_app_notification(user, notification_type, data)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook_notification(user, notification_type, data)
                elif channel == NotificationChannel.SLACK:
                    await self._send_slack_notification(user, notification_type, data)
                    
            except Exception as e:
                logger.error(f"Failed to send {channel} notification to user {user.id}: {str(e)}")
    
    async def _send_email_notification(
        self,
        user: User,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> None:
        """Send email notification (mock implementation)."""
        # In a real implementation, this would integrate with an email service
        logger.info(f"Sending email notification to {user.email}: {notification_type}")
        
        # Mock email content generation
        subject = self._generate_email_subject(notification_type, data)
        body = self._generate_email_body(notification_type, data)
        
        # Mock email sending
        logger.info(f"Email sent - Subject: {subject}")
    
    async def _send_in_app_notification(
        self,
        user: User,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> None:
        """Send in-app notification (mock implementation)."""
        # In a real implementation, this would store the notification in the database
        # and send it via WebSocket to connected clients
        logger.info(f"Sending in-app notification to user {user.id}: {notification_type}")
        
        notification_content = {
            "user_id": str(user.id),
            "type": notification_type,
            "title": self._generate_notification_title(notification_type, data),
            "message": self._generate_notification_message(notification_type, data),
            "data": data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Mock WebSocket broadcast
        logger.info(f"In-app notification queued: {notification_content['title']}")
    
    async def _send_webhook_notification(
        self,
        user: User,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> None:
        """Send webhook notification (mock implementation)."""
        # In a real implementation, this would send HTTP POST to user's webhook URL
        logger.info(f"Sending webhook notification for user {user.id}: {notification_type}")
    
    async def _send_slack_notification(
        self,
        user: User,
        notification_type: NotificationType,
        data: Dict[str, Any]
    ) -> None:
        """Send Slack notification (mock implementation)."""
        # In a real implementation, this would integrate with Slack API
        logger.info(f"Sending Slack notification for user {user.id}: {notification_type}")
    
    def _generate_email_subject(self, notification_type: NotificationType, data: Dict[str, Any]) -> str:
        """Generate email subject line."""
        if notification_type == NotificationType.DEPLOYMENT_FAILED:
            return f"Deployment Failed: {data['repository_name']} ({data['commit_sha']})"
        elif notification_type == NotificationType.DEPLOYMENT_RECOVERED:
            return f"Deployment Recovered: {data['repository_name']} ({data['commit_sha']})"
        elif notification_type == NotificationType.ROLLBACK_COMPLETED:
            return f"Rollback Completed: {data['repository_name']}"
        elif notification_type == NotificationType.HEALTH_ALERT:
            return f"Health Alert: {data['repository_name']} (Score: {data['health_score']})"
        elif notification_type == NotificationType.PATTERN_DETECTED:
            return f"Failure Pattern Detected: {data['repository_name']}"
        else:
            return f"Deployment Notification: {data.get('repository_name', 'Unknown')}"
    
    def _generate_email_body(self, notification_type: NotificationType, data: Dict[str, Any]) -> str:
        """Generate email body content."""
        if notification_type == NotificationType.DEPLOYMENT_FAILED:
            return f"""
            Your deployment has failed with a {data['error_severity']} severity {data['error_category']} error.
            
            Repository: {data['repository_name']}
            Commit: {data['commit_sha']}
            Branch: {data['branch']}
            
            Recovery options:
            - Auto-retry: {'Available' if data['auto_retry_available'] else 'Not recommended'}
            - Rollback: {'Available' if data['rollback_available'] else 'No previous deployments'}
            
            View troubleshooting guide: {data['troubleshooting_url']}
            """
        elif notification_type == NotificationType.DEPLOYMENT_RECOVERED:
            return f"""
            Your deployment has been successfully recovered!
            
            Repository: {data['repository_name']}
            Commit: {data['commit_sha']}
            Recovery method: {data['recovery_method']}
            
            Preview URL: {data.get('preview_url', 'Not available')}
            """
        else:
            return f"Deployment notification for {data.get('repository_name', 'your repository')}."
    
    def _generate_notification_title(self, notification_type: NotificationType, data: Dict[str, Any]) -> str:
        """Generate notification title."""
        if notification_type == NotificationType.DEPLOYMENT_FAILED:
            return f"Deployment Failed"
        elif notification_type == NotificationType.DEPLOYMENT_RECOVERED:
            return f"Deployment Recovered"
        elif notification_type == NotificationType.AUTO_RETRY_INITIATED:
            return f"Auto-retry Initiated"
        elif notification_type == NotificationType.ROLLBACK_COMPLETED:
            return f"Rollback Completed"
        elif notification_type == NotificationType.HEALTH_ALERT:
            return f"Health Alert"
        elif notification_type == NotificationType.PATTERN_DETECTED:
            return f"Failure Pattern Detected"
        else:
            return "Deployment Notification"
    
    def _generate_notification_message(self, notification_type: NotificationType, data: Dict[str, Any]) -> str:
        """Generate notification message."""
        if notification_type == NotificationType.DEPLOYMENT_FAILED:
            return f"{data['repository_name']} deployment failed with {data['error_category']} error"
        elif notification_type == NotificationType.DEPLOYMENT_RECOVERED:
            return f"{data['repository_name']} deployment recovered successfully"
        elif notification_type == NotificationType.AUTO_RETRY_INITIATED:
            return f"Auto-retry started for {data['repository_name']} deployment"
        elif notification_type == NotificationType.ROLLBACK_COMPLETED:
            return f"{data['repository_name']} rolled back to previous version"
        elif notification_type == NotificationType.HEALTH_ALERT:
            return f"{data['repository_name']} health score is {data['health_score']}"
        elif notification_type == NotificationType.PATTERN_DETECTED:
            return f"Recurring {data['pattern_category']} failures detected in {data['repository_name']}"
        else:
            return f"Deployment notification for {data.get('repository_name', 'repository')}"
    
    async def _get_project_members(self, project_id: str) -> List[User]:
        """Get project members (mock implementation)."""
        # In a real implementation, this would query the database
        return []
    
    async def _get_repository_name(self, repository_id: str) -> str:
        """Get repository name (mock implementation)."""
        # In a real implementation, this would query the database
        return f"repository-{repository_id[:8]}"
    
    async def _get_project_id_for_repository(self, repository_id: str) -> str:
        """Get project ID for repository (mock implementation)."""
        # In a real implementation, this would query the database
        return f"project-{repository_id[:8]}"
    
    async def _get_user_notification_preferences(self, user_id: str) -> List[NotificationChannel]:
        """Get user notification preferences (mock implementation)."""
        # In a real implementation, this would query user preferences
        return [NotificationChannel.IN_APP, NotificationChannel.EMAIL]