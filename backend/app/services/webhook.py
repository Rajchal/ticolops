"""Webhook handling service for Git provider events."""

import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.repository import Repository, GitProvider
from app.models.project import Project
from app.core.config import settings
from app.core.exceptions import ValidationError, NotFoundError
from app.services.activity import ActivityService
from app.services.presence_manager import PresenceManager
from app.services.deployment import DeploymentService

logger = logging.getLogger(__name__)


class WebhookEvent:
    """Represents a webhook event from a Git provider."""
    
    def __init__(
        self,
        provider: GitProvider,
        event_type: str,
        repository_id: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ):
        self.provider = provider
        self.event_type = event_type
        self.repository_id = repository_id
        self.payload = payload
        self.signature = signature
        self.timestamp = datetime.utcnow()
    
    @property
    def commit_sha(self) -> Optional[str]:
        """Extract commit SHA from payload."""
        if self.provider == GitProvider.GITHUB:
            return self.payload.get("after")
        elif self.provider == GitProvider.GITLAB:
            return self.payload.get("checkout_sha")
        return None
    
    @property
    def branch(self) -> Optional[str]:
        """Extract branch name from payload."""
        if self.provider == GitProvider.GITHUB:
            ref = self.payload.get("ref", "")
            return ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else None
        elif self.provider == GitProvider.GITLAB:
            ref = self.payload.get("ref", "")
            return ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else None
        return None
    
    @property
    def commits(self) -> List[Dict[str, Any]]:
        """Extract commits from payload."""
        if self.provider == GitProvider.GITHUB:
            return self.payload.get("commits", [])
        elif self.provider == GitProvider.GITLAB:
            return self.payload.get("commits", [])
        return []
    
    @property
    def pusher(self) -> Optional[Dict[str, str]]:
        """Extract pusher information from payload."""
        if self.provider == GitProvider.GITHUB:
            pusher = self.payload.get("pusher", {})
            return {
                "name": pusher.get("name"),
                "email": pusher.get("email"),
                "username": pusher.get("name")
            }
        elif self.provider == GitProvider.GITLAB:
            return {
                "name": self.payload.get("user_name"),
                "email": self.payload.get("user_email"),
                "username": self.payload.get("user_username")
            }
        return None
    
    @property
    def repository_name(self) -> Optional[str]:
        """Extract repository name from payload."""
        if self.provider == GitProvider.GITHUB:
            repo = self.payload.get("repository", {})
            return repo.get("full_name")
        elif self.provider == GitProvider.GITLAB:
            project = self.payload.get("project", {})
            return project.get("path_with_namespace")
        return None


class WebhookSignatureValidator:
    """Validates webhook signatures from Git providers."""
    
    @staticmethod
    def validate_github_signature(payload: bytes, signature: str, secret: str) -> bool:
        """
        Validate GitHub webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: GitHub signature header (X-Hub-Signature-256)
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        received_signature = signature[7:]  # Remove "sha256=" prefix
        return hmac.compare_digest(expected_signature, received_signature)
    
    @staticmethod
    def validate_gitlab_signature(payload: bytes, signature: str, secret: str) -> bool:
        """
        Validate GitLab webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: GitLab signature header (X-Gitlab-Token)
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        return hmac.compare_digest(secret, signature)


class WebhookService:
    """Service for handling Git provider webhooks."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_service = ActivityService(db)
        self.presence_manager = PresenceManager()
        self.deployment_service = DeploymentService(db)
    
    async def process_webhook(
        self,
        provider: GitProvider,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        raw_payload: bytes
    ) -> Dict[str, Any]:
        """
        Process incoming webhook from Git provider.
        
        Args:
            provider: Git provider (GitHub, GitLab)
            payload: Parsed webhook payload
            headers: HTTP headers from webhook request
            raw_payload: Raw webhook payload for signature verification
            
        Returns:
            Processing result
        """
        try:
            # Extract event type
            event_type = self._extract_event_type(provider, headers, payload)
            
            # Find repository by webhook payload
            repository = await self._find_repository_by_payload(provider, payload)
            if not repository:
                logger.warning(f"Repository not found for webhook payload: {payload}")
                return {"status": "ignored", "reason": "repository_not_found"}
            
            # Validate webhook signature if configured
            if settings.WEBHOOK_SECRET:
                if not self._validate_signature(provider, headers, raw_payload):
                    logger.warning(f"Invalid webhook signature for repository {repository.id}")
                    return {"status": "error", "reason": "invalid_signature"}
            
            # Create webhook event
            webhook_event = WebhookEvent(
                provider=provider,
                event_type=event_type,
                repository_id=str(repository.id),
                payload=payload,
                signature=self._extract_signature(provider, headers)
            )
            
            # Process the event
            result = await self._process_event(webhook_event, repository)
            
            logger.info(f"Processed webhook event: {event_type} for repository {repository.id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    async def register_webhook(
        self,
        repository_id: str,
        webhook_url: str,
        events: List[str] = None
    ) -> Dict[str, Any]:
        """
        Register webhook with Git provider.
        
        Args:
            repository_id: Repository ID
            webhook_url: Webhook URL to register
            events: List of events to subscribe to
            
        Returns:
            Webhook registration result
        """
        if events is None:
            events = ["push", "pull_request", "merge_request"]
        
        # Get repository
        query = select(Repository).where(Repository.id == UUID(repository_id))
        result = await self.db.execute(query)
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise NotFoundError(f"Repository {repository_id} not found")
        
        # TODO: Implement webhook registration with Git provider
        # This would require storing access tokens securely
        
        return {
            "status": "registered",
            "webhook_url": webhook_url,
            "events": events,
            "repository_id": repository_id
        }
    
    async def unregister_webhook(self, repository_id: str, webhook_id: str) -> bool:
        """
        Unregister webhook from Git provider.
        
        Args:
            repository_id: Repository ID
            webhook_id: Webhook ID to unregister
            
        Returns:
            True if successfully unregistered
        """
        # Get repository
        query = select(Repository).where(Repository.id == UUID(repository_id))
        result = await self.db.execute(query)
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise NotFoundError(f"Repository {repository_id} not found")
        
        # TODO: Implement webhook unregistration with Git provider
        # This would require storing access tokens securely
        
        # Clear webhook ID from repository
        repository.webhook_id = None
        await self.db.commit()
        
        return True
    
    async def get_webhook_events(
        self,
        repository_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent webhook events for a repository.
        
        Args:
            repository_id: Repository ID
            limit: Maximum number of events to return
            
        Returns:
            List of recent webhook events
        """
        # TODO: Implement webhook event storage and retrieval
        # For now, return empty list
        return []
    
    def _extract_event_type(
        self,
        provider: GitProvider,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> str:
        """Extract event type from webhook headers/payload."""
        if provider == GitProvider.GITHUB:
            return headers.get("X-GitHub-Event", "unknown")
        elif provider == GitProvider.GITLAB:
            return headers.get("X-Gitlab-Event", "unknown")
        return "unknown"
    
    def _extract_signature(self, provider: GitProvider, headers: Dict[str, str]) -> Optional[str]:
        """Extract signature from webhook headers."""
        if provider == GitProvider.GITHUB:
            return headers.get("X-Hub-Signature-256")
        elif provider == GitProvider.GITLAB:
            return headers.get("X-Gitlab-Token")
        return None
    
    def _validate_signature(
        self,
        provider: GitProvider,
        headers: Dict[str, str],
        raw_payload: bytes
    ) -> bool:
        """Validate webhook signature."""
        signature = self._extract_signature(provider, headers)
        if not signature:
            return False
        
        secret = settings.WEBHOOK_SECRET
        if not secret:
            return True  # No secret configured, skip validation
        
        if provider == GitProvider.GITHUB:
            return WebhookSignatureValidator.validate_github_signature(
                raw_payload, signature, secret
            )
        elif provider == GitProvider.GITLAB:
            return WebhookSignatureValidator.validate_gitlab_signature(
                raw_payload, signature, secret
            )
        
        return False
    
    async def _find_repository_by_payload(
        self,
        provider: GitProvider,
        payload: Dict[str, Any]
    ) -> Optional[Repository]:
        """Find repository by webhook payload information."""
        # Extract repository identifier from payload
        if provider == GitProvider.GITHUB:
            repo_data = payload.get("repository", {})
            repo_url = repo_data.get("html_url") or repo_data.get("clone_url")
        elif provider == GitProvider.GITLAB:
            project_data = payload.get("project", {})
            repo_url = project_data.get("web_url") or project_data.get("http_url")
        else:
            return None
        
        if not repo_url:
            return None
        
        # Find repository by URL
        query = select(Repository).where(
            and_(
                Repository.url == repo_url,
                Repository.provider == provider,
                Repository.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _process_event(
        self,
        event: WebhookEvent,
        repository: Repository
    ) -> Dict[str, Any]:
        """Process a specific webhook event."""
        if event.event_type == "push":
            return await self._process_push_event(event, repository)
        elif event.event_type in ["pull_request", "merge_request"]:
            return await self._process_pr_event(event, repository)
        else:
            logger.info(f"Ignoring unsupported event type: {event.event_type}")
            return {"status": "ignored", "reason": "unsupported_event_type"}
    
    async def _process_push_event(
        self,
        event: WebhookEvent,
        repository: Repository
    ) -> Dict[str, Any]:
        """Process push event from Git provider."""
        # Extract push information
        branch = event.branch
        commits = event.commits
        pusher = event.pusher
        
        if not branch or not commits:
            return {"status": "ignored", "reason": "no_commits_or_branch"}
        
        # Only process pushes to the tracked branch
        if branch != repository.branch:
            return {"status": "ignored", "reason": "branch_not_tracked"}
        
        # Log activity for the pusher
        if pusher and pusher.get("email"):
            # Find user by email (simplified - in real implementation, 
            # you'd need proper user mapping)
            activity_data = {
                "type": "push",
                "location": f"{repository.name}:{branch}",
                "metadata": {
                    "commits": len(commits),
                    "commit_messages": [commit.get("message", "")[:100] for commit in commits[:3]],
                    "repository_id": str(repository.id),
                    "branch": branch
                }
            }
            
            # TODO: Map Git user to platform user and log activity
            logger.info(f"Push activity: {pusher['email']} pushed {len(commits)} commits to {branch}")
        
        # Trigger deployment if auto-deploy is enabled
        deployment_config = repository.deployment_config or {}
        if deployment_config.get("auto_deploy", True):
            try:
                deployment = await self.deployment_service.trigger_deployment_from_webhook(
                    repository_id=str(repository.id),
                    commit_sha=event.commit_sha,
                    branch=branch,
                    pusher_info=pusher
                )
                
                if deployment:
                    logger.info(f"Triggered deployment {deployment.id} for repository {repository.id}")
                    return {
                        "status": "processed",
                        "action": "deployment_triggered",
                        "deployment_id": str(deployment.id),
                        "commits": len(commits),
                        "branch": branch
                    }
                else:
                    return {
                        "status": "processed",
                        "action": "deployment_skipped",
                        "reason": "auto_deploy_disabled_or_branch_not_tracked",
                        "commits": len(commits),
                        "branch": branch
                    }
            except Exception as e:
                logger.error(f"Failed to trigger deployment: {e}")
                return {
                    "status": "processed",
                    "action": "deployment_failed",
                    "error": str(e),
                    "commits": len(commits),
                    "branch": branch
                }
        
        return {
            "status": "processed",
            "action": "logged",
            "commits": len(commits),
            "branch": branch
        }
    
    async def _process_pr_event(
        self,
        event: WebhookEvent,
        repository: Repository
    ) -> Dict[str, Any]:
        """Process pull/merge request event from Git provider."""
        # Extract PR information
        action = event.payload.get("action")
        pr_data = event.payload.get("pull_request") or event.payload.get("merge_request")
        
        if not pr_data:
            return {"status": "ignored", "reason": "no_pr_data"}
        
        pr_title = pr_data.get("title", "")
        pr_author = pr_data.get("user", {}).get("login") or pr_data.get("author", {}).get("username")
        
        # Log PR activity
        if pr_author:
            activity_data = {
                "type": "pull_request",
                "location": f"{repository.name}:PR#{pr_data.get('number')}",
                "metadata": {
                    "action": action,
                    "title": pr_title,
                    "repository_id": str(repository.id),
                    "pr_number": pr_data.get("number")
                }
            }
            
            # TODO: Map Git user to platform user and log activity
            logger.info(f"PR activity: {pr_author} {action} PR #{pr_data.get('number')}")
        
        return {
            "status": "processed",
            "action": "pr_logged",
            "pr_action": action,
            "pr_number": pr_data.get("number")
        }