"""Webhook handling service for Git provider events."""

import hashlib
import hmac
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.repository import Repository, GitProvider
from app.models.activity import Activity, ActivityType
from app.models.user import User
from app.services.activity import ActivityService
from app.services.websocket_pubsub import broadcast_to_project_instances
from app.core.config import settings
from app.core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Service for handling Git provider webhook events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_github_webhook(
        self, 
        payload: Dict[str, Any], 
        signature: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle GitHub webhook events.
        
        Args:
            payload: Webhook payload from GitHub
            signature: X-Hub-Signature-256 header for verification
            event_type: X-GitHub-Event header
            
        Returns:
            Processing result
        """
        try:
            # Verify webhook signature if provided
            if signature and settings.GITHUB_WEBHOOK_SECRET:
                if not self._verify_github_signature(payload, signature):
                    raise ValidationError("Invalid webhook signature")
            
            # Get repository information from payload
            repo_info = payload.get("repository", {})
            repo_url = repo_info.get("html_url") or repo_info.get("url", "")
            
            if not repo_url:
                raise ValidationError("Repository URL not found in payload")
            
            # Find connected repository
            repository = await self._find_repository_by_url(repo_url, GitProvider.GITHUB)
            if not repository:
                logger.warning(f"Webhook received for unconnected repository: {repo_url}")
                return {"status": "ignored", "reason": "repository_not_connected"}
            
            # Process event based on type
            result = await self._process_github_event(repository, event_type, payload)
            
            # Log webhook processing
            logger.info(f"GitHub webhook processed: {event_type} for {repo_url}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing GitHub webhook: {e}")
            raise

    async def handle_gitlab_webhook(
        self, 
        payload: Dict[str, Any], 
        token: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle GitLab webhook events.
        
        Args:
            payload: Webhook payload from GitLab
            token: X-Gitlab-Token header for verification
            event_type: X-Gitlab-Event header
            
        Returns:
            Processing result
        """
        try:
            # Verify webhook token if provided
            if token and settings.GITLAB_WEBHOOK_SECRET:
                if token != settings.GITLAB_WEBHOOK_SECRET:
                    raise ValidationError("Invalid webhook token")
            
            # Get repository information from payload
            project_info = payload.get("project", {})
            repo_url = project_info.get("web_url") or project_info.get("http_url", "")
            
            if not repo_url:
                raise ValidationError("Repository URL not found in payload")
            
            # Find connected repository
            repository = await self._find_repository_by_url(repo_url, GitProvider.GITLAB)
            if not repository:
                logger.warning(f"Webhook received for unconnected repository: {repo_url}")
                return {"status": "ignored", "reason": "repository_not_connected"}
            
            # Process event based on type
            result = await self._process_gitlab_event(repository, event_type, payload)
            
            # Log webhook processing
            logger.info(f"GitLab webhook processed: {event_type} for {repo_url}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing GitLab webhook: {e}")
            raise

    async def _process_github_event(
        self, 
        repository: Repository, 
        event_type: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process GitHub webhook event."""
        if event_type == "push":
            return await self._handle_push_event(repository, payload, GitProvider.GITHUB)
        elif event_type == "pull_request":
            return await self._handle_pull_request_event(repository, payload, GitProvider.GITHUB)
        elif event_type == "create":
            return await self._handle_branch_create_event(repository, payload, GitProvider.GITHUB)
        elif event_type == "delete":
            return await self._handle_branch_delete_event(repository, payload, GitProvider.GITHUB)
        elif event_type == "release":
            return await self._handle_release_event(repository, payload, GitProvider.GITHUB)
        else:
            logger.info(f"Unhandled GitHub event type: {event_type}")
            return {"status": "ignored", "reason": "unsupported_event_type"}

    async def _process_gitlab_event(
        self, 
        repository: Repository, 
        event_type: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process GitLab webhook event."""
        if event_type == "Push Hook":
            return await self._handle_push_event(repository, payload, GitProvider.GITLAB)
        elif event_type == "Merge Request Hook":
            return await self._handle_pull_request_event(repository, payload, GitProvider.GITLAB)
        elif event_type == "Tag Push Hook":
            return await self._handle_tag_event(repository, payload, GitProvider.GITLAB)
        elif event_type == "Release Hook":
            return await self._handle_release_event(repository, payload, GitProvider.GITLAB)
        else:
            logger.info(f"Unhandled GitLab event type: {event_type}")
            return {"status": "ignored", "reason": "unsupported_event_type"}

    async def _handle_push_event(
        self, 
        repository: Repository, 
        payload: Dict[str, Any], 
        provider: GitProvider
    ) -> Dict[str, Any]:
        """Handle push events from Git providers."""
        try:
            # Extract push information
            if provider == GitProvider.GITHUB:
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
                commits = payload.get("commits", [])
                pusher = payload.get("pusher", {})
                pusher_name = pusher.get("name", "Unknown")
                pusher_email = pusher.get("email", "")
            else:  # GitLab
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
                commits = payload.get("commits", [])
                user_info = payload.get("user_name", "Unknown")
                pusher_name = user_info
                pusher_email = payload.get("user_email", "")
            
            # Check if this is the tracked branch
            is_tracked_branch = branch == repository.branch
            
            # Create activity record for the push
            activity_service = ActivityService(self.db)
            
            push_activity = await activity_service.create_activity(
                user_id=str(repository.project.owner_id),  # Use project owner as fallback
                activity_data={
                    "type": ActivityType.COMMIT_PUSHED,
                    "title": f"Code pushed to {branch}",
                    "description": f"{len(commits)} commit(s) pushed by {pusher_name}",
                    "location": f"{repository.name}:{branch}",
                    "project_id": str(repository.project_id),
                    "metadata": {
                        "repository_id": str(repository.id),
                        "branch": branch,
                        "commit_count": len(commits),
                        "pusher_name": pusher_name,
                        "pusher_email": pusher_email,
                        "is_tracked_branch": is_tracked_branch,
                        "commits": [
                            {
                                "id": commit.get("id"),
                                "message": commit.get("message", ""),
                                "author": commit.get("author", {}),
                                "timestamp": commit.get("timestamp")
                            }
                            for commit in commits[:5]  # Limit to first 5 commits
                        ]
                    }
                }
            )
            
            # Broadcast push event to project members
            await self._broadcast_repository_event(
                repository,
                "repository_push",
                {
                    "repository_name": repository.name,
                    "branch": branch,
                    "commit_count": len(commits),
                    "pusher_name": pusher_name,
                    "is_tracked_branch": is_tracked_branch,
                    "activity_id": str(push_activity.id)
                }
            )
            
            # Trigger deployment if auto-deploy is enabled and this is the tracked branch
            deployment_triggered = False
            if (repository.deployment_config.get("auto_deploy", False) and 
                is_tracked_branch and 
                len(commits) > 0):
                
                deployment_triggered = await self._trigger_deployment(repository, payload)
            
            return {
                "status": "processed",
                "event_type": "push",
                "branch": branch,
                "commit_count": len(commits),
                "is_tracked_branch": is_tracked_branch,
                "deployment_triggered": deployment_triggered,
                "activity_id": str(push_activity.id)
            }
        
        except Exception as e:
            logger.error(f"Error handling push event: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_pull_request_event(
        self, 
        repository: Repository, 
        payload: Dict[str, Any], 
        provider: GitProvider
    ) -> Dict[str, Any]:
        """Handle pull request/merge request events."""
        try:
            # Extract PR information
            if provider == GitProvider.GITHUB:
                pr_info = payload.get("pull_request", {})
                action = payload.get("action", "")
                pr_number = pr_info.get("number")
                pr_title = pr_info.get("title", "")
                pr_state = pr_info.get("state", "")
                author = pr_info.get("user", {}).get("login", "Unknown")
                base_branch = pr_info.get("base", {}).get("ref", "")
                head_branch = pr_info.get("head", {}).get("ref", "")
            else:  # GitLab
                mr_info = payload.get("object_attributes", {})
                action = mr_info.get("action", "")
                pr_number = mr_info.get("iid")
                pr_title = mr_info.get("title", "")
                pr_state = mr_info.get("state", "")
                author = payload.get("user", {}).get("name", "Unknown")
                base_branch = mr_info.get("target_branch", "")
                head_branch = mr_info.get("source_branch", "")
            
            # Create activity record
            activity_service = ActivityService(self.db)
            
            activity_type = ActivityType.REVIEWING if action in ["opened", "reopened"] else ActivityType.CODING
            
            pr_activity = await activity_service.create_activity(
                user_id=str(repository.project.owner_id),
                activity_data={
                    "type": activity_type,
                    "title": f"Pull request {action}: {pr_title}",
                    "description": f"PR #{pr_number} {action} by {author}",
                    "location": f"{repository.name}:PR#{pr_number}",
                    "project_id": str(repository.project_id),
                    "metadata": {
                        "repository_id": str(repository.id),
                        "pr_number": pr_number,
                        "pr_title": pr_title,
                        "pr_state": pr_state,
                        "action": action,
                        "author": author,
                        "base_branch": base_branch,
                        "head_branch": head_branch
                    }
                }
            )
            
            # Broadcast PR event
            await self._broadcast_repository_event(
                repository,
                "repository_pull_request",
                {
                    "repository_name": repository.name,
                    "pr_number": pr_number,
                    "pr_title": pr_title,
                    "action": action,
                    "author": author,
                    "base_branch": base_branch,
                    "head_branch": head_branch,
                    "activity_id": str(pr_activity.id)
                }
            )
            
            return {
                "status": "processed",
                "event_type": "pull_request",
                "action": action,
                "pr_number": pr_number,
                "activity_id": str(pr_activity.id)
            }
        
        except Exception as e:
            logger.error(f"Error handling pull request event: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_branch_create_event(
        self, 
        repository: Repository, 
        payload: Dict[str, Any], 
        provider: GitProvider
    ) -> Dict[str, Any]:
        """Handle branch creation events."""
        try:
            ref = payload.get("ref", "")
            ref_type = payload.get("ref_type", "")
            
            if ref_type != "branch":
                return {"status": "ignored", "reason": "not_a_branch"}
            
            # Create activity record
            activity_service = ActivityService(self.db)
            
            branch_activity = await activity_service.create_activity(
                user_id=str(repository.project.owner_id),
                activity_data={
                    "type": ActivityType.BRANCH_CREATED,
                    "title": f"Branch created: {ref}",
                    "description": f"New branch '{ref}' created in {repository.name}",
                    "location": f"{repository.name}:{ref}",
                    "project_id": str(repository.project_id),
                    "metadata": {
                        "repository_id": str(repository.id),
                        "branch_name": ref,
                        "ref_type": ref_type
                    }
                }
            )
            
            # Broadcast branch creation
            await self._broadcast_repository_event(
                repository,
                "repository_branch_created",
                {
                    "repository_name": repository.name,
                    "branch_name": ref,
                    "activity_id": str(branch_activity.id)
                }
            )
            
            return {
                "status": "processed",
                "event_type": "branch_create",
                "branch_name": ref,
                "activity_id": str(branch_activity.id)
            }
        
        except Exception as e:
            logger.error(f"Error handling branch create event: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_branch_delete_event(
        self, 
        repository: Repository, 
        payload: Dict[str, Any], 
        provider: GitProvider
    ) -> Dict[str, Any]:
        """Handle branch deletion events."""
        try:
            ref = payload.get("ref", "")
            ref_type = payload.get("ref_type", "")
            
            if ref_type != "branch":
                return {"status": "ignored", "reason": "not_a_branch"}
            
            # Create activity record
            activity_service = ActivityService(self.db)
            
            branch_activity = await activity_service.create_activity(
                user_id=str(repository.project.owner_id),
                activity_data={
                    "type": ActivityType.BRANCH_MERGED,  # Assuming deletion after merge
                    "title": f"Branch deleted: {ref}",
                    "description": f"Branch '{ref}' deleted from {repository.name}",
                    "location": f"{repository.name}:{ref}",
                    "project_id": str(repository.project_id),
                    "metadata": {
                        "repository_id": str(repository.id),
                        "branch_name": ref,
                        "ref_type": ref_type
                    }
                }
            )
            
            return {
                "status": "processed",
                "event_type": "branch_delete",
                "branch_name": ref,
                "activity_id": str(branch_activity.id)
            }
        
        except Exception as e:
            logger.error(f"Error handling branch delete event: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_release_event(
        self, 
        repository: Repository, 
        payload: Dict[str, Any], 
        provider: GitProvider
    ) -> Dict[str, Any]:
        """Handle release events."""
        try:
            if provider == GitProvider.GITHUB:
                release_info = payload.get("release", {})
                action = payload.get("action", "")
                tag_name = release_info.get("tag_name", "")
                release_name = release_info.get("name", "")
                author = release_info.get("author", {}).get("login", "Unknown")
            else:  # GitLab
                # GitLab release webhook structure
                tag_name = payload.get("tag", "")
                release_name = payload.get("name", "")
                action = "published"  # GitLab doesn't have action field
                author = payload.get("user_name", "Unknown")
            
            # Create activity record
            activity_service = ActivityService(self.db)
            
            release_activity = await activity_service.create_activity(
                user_id=str(repository.project.owner_id),
                activity_data={
                    "type": ActivityType.DEPLOYMENT_SUCCESS,  # Treat release as deployment
                    "title": f"Release {action}: {release_name or tag_name}",
                    "description": f"Release '{release_name or tag_name}' {action} by {author}",
                    "location": f"{repository.name}:release/{tag_name}",
                    "project_id": str(repository.project_id),
                    "metadata": {
                        "repository_id": str(repository.id),
                        "tag_name": tag_name,
                        "release_name": release_name,
                        "action": action,
                        "author": author
                    }
                }
            )
            
            # Broadcast release event
            await self._broadcast_repository_event(
                repository,
                "repository_release",
                {
                    "repository_name": repository.name,
                    "tag_name": tag_name,
                    "release_name": release_name,
                    "action": action,
                    "author": author,
                    "activity_id": str(release_activity.id)
                }
            )
            
            return {
                "status": "processed",
                "event_type": "release",
                "action": action,
                "tag_name": tag_name,
                "activity_id": str(release_activity.id)
            }
        
        except Exception as e:
            logger.error(f"Error handling release event: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_tag_event(
        self, 
        repository: Repository, 
        payload: Dict[str, Any], 
        provider: GitProvider
    ) -> Dict[str, Any]:
        """Handle tag push events (GitLab)."""
        try:
            ref = payload.get("ref", "")
            tag_name = ref.replace("refs/tags/", "") if ref.startswith("refs/tags/") else ref
            
            # Create activity record
            activity_service = ActivityService(self.db)
            
            tag_activity = await activity_service.create_activity(
                user_id=str(repository.project.owner_id),
                activity_data={
                    "type": ActivityType.SETTINGS_UPDATED,  # Use as tag creation
                    "title": f"Tag created: {tag_name}",
                    "description": f"New tag '{tag_name}' created in {repository.name}",
                    "location": f"{repository.name}:tag/{tag_name}",
                    "project_id": str(repository.project_id),
                    "metadata": {
                        "repository_id": str(repository.id),
                        "tag_name": tag_name
                    }
                }
            )
            
            return {
                "status": "processed",
                "event_type": "tag",
                "tag_name": tag_name,
                "activity_id": str(tag_activity.id)
            }
        
        except Exception as e:
            logger.error(f"Error handling tag event: {e}")
            return {"status": "error", "error": str(e)}

    async def _trigger_deployment(self, repository: Repository, payload: Dict[str, Any]) -> bool:
        """Trigger deployment for repository."""
        try:
            # This would integrate with the deployment service
            # For now, we'll just log the deployment trigger
            
            logger.info(f"Deployment triggered for repository {repository.name}")
            
            # TODO: Integrate with deployment service
            # deployment_service = DeploymentService(self.db)
            # deployment = await deployment_service.create_deployment(
            #     repository_id=str(repository.id),
            #     trigger_type="webhook",
            #     trigger_data=payload
            # )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to trigger deployment: {e}")
            return False

    async def _broadcast_repository_event(
        self, 
        repository: Repository, 
        event_type: str, 
        event_data: Dict[str, Any]
    ):
        """Broadcast repository event to project members."""
        try:
            message = {
                "type": event_type,
                "data": {
                    "repository_id": str(repository.id),
                    "project_id": str(repository.project_id),
                    "timestamp": datetime.utcnow().isoformat(),
                    **event_data
                }
            }
            
            await broadcast_to_project_instances(
                str(repository.project_id),
                message
            )
        
        except Exception as e:
            logger.error(f"Failed to broadcast repository event: {e}")

    async def _find_repository_by_url(self, repo_url: str, provider: GitProvider) -> Optional[Repository]:
        """Find repository by URL and provider."""
        # Normalize URL for comparison
        normalized_url = repo_url.rstrip('/').lower()
        
        query = select(Repository).where(
            and_(
                Repository.provider == provider,
                Repository.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        repositories = result.scalars().all()
        
        # Find matching repository by URL
        for repo in repositories:
            repo_normalized = repo.url.rstrip('/').lower()
            if repo_normalized == normalized_url:
                return repo
        
        return None

    def _verify_github_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify GitHub webhook signature."""
        try:
            # GitHub sends signature as "sha256=<hash>"
            if not signature.startswith("sha256="):
                return False
            
            expected_signature = signature[7:]  # Remove "sha256=" prefix
            
            # Create HMAC signature
            payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            computed_signature = hmac.new(
                settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures securely
            return hmac.compare_digest(expected_signature, computed_signature)
        
        except Exception as e:
            logger.error(f"Error verifying GitHub signature: {e}")
            return False

    async def get_webhook_stats(self, repository_id: Optional[str] = None) -> Dict[str, Any]:
        """Get webhook processing statistics."""
        # This would typically query a webhook_events table
        # For now, return mock statistics
        
        return {
            "total_webhooks_processed": 150,
            "webhooks_by_provider": {
                "github": 90,
                "gitlab": 60
            },
            "webhooks_by_event_type": {
                "push": 100,
                "pull_request": 30,
                "release": 15,
                "branch_create": 5
            },
            "successful_deployments_triggered": 85,
            "failed_webhook_processing": 3,
            "average_processing_time_ms": 250,
            "last_24h_activity": {
                "webhooks_received": 25,
                "deployments_triggered": 12
            }
        }

    async def validate_webhook_configuration(self, repository_id: str) -> Dict[str, Any]:
        """Validate webhook configuration for a repository."""
        try:
            # Get repository
            query = select(Repository).where(Repository.id == UUID(repository_id))
            result = await self.db.execute(query)
            repository = result.scalar_one_or_none()
            
            if not repository:
                raise NotFoundError(f"Repository {repository_id} not found")
            
            validation_result = {
                "repository_id": repository_id,
                "webhook_configured": repository.webhook_id is not None,
                "webhook_id": repository.webhook_id,
                "provider": repository.provider.value,
                "auto_deploy_enabled": repository.deployment_config.get("auto_deploy", False),
                "tracked_branch": repository.branch,
                "issues": [],
                "recommendations": []
            }
            
            # Check for potential issues
            if not repository.webhook_id:
                validation_result["issues"].append("No webhook configured")
                validation_result["recommendations"].append("Configure webhook to receive real-time updates")
            
            if not repository.deployment_config.get("auto_deploy", False):
                validation_result["recommendations"].append("Enable auto-deploy for automatic deployments")
            
            if not repository.deployment_config.get("build_command"):
                validation_result["recommendations"].append("Configure build command for proper deployment")
            
            return validation_result
        
        except Exception as e:
            logger.error(f"Error validating webhook configuration: {e}")
            return {
                "repository_id": repository_id,
                "error": str(e),
                "webhook_configured": False
            }