"""Tests for webhook service functionality."""

import pytest
import json
import hashlib
import hmac
from datetime import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.webhook import WebhookService, WebhookEvent, WebhookSignatureValidator
from app.models.repository import Repository, GitProvider
from app.models.project import Project
from app.core.exceptions import ValidationError, NotFoundError


class TestWebhookSignatureValidator:
    """Test webhook signature validation."""
    
    def test_validate_github_signature_valid(self):
        """Test valid GitHub signature validation."""
        payload = b'{"test": "data"}'
        secret = "my-secret"
        
        # Create expected signature
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        github_signature = f"sha256={signature}"
        
        result = WebhookSignatureValidator.validate_github_signature(
            payload, github_signature, secret
        )
        assert result is True
    
    def test_validate_github_signature_invalid(self):
        """Test invalid GitHub signature validation."""
        payload = b'{"test": "data"}'
        secret = "my-secret"
        invalid_signature = "sha256=invalid"
        
        result = WebhookSignatureValidator.validate_github_signature(
            payload, invalid_signature, secret
        )
        assert result is False
    
    def test_validate_github_signature_wrong_format(self):
        """Test GitHub signature with wrong format."""
        payload = b'{"test": "data"}'
        secret = "my-secret"
        wrong_format = "invalid-format"
        
        result = WebhookSignatureValidator.validate_github_signature(
            payload, wrong_format, secret
        )
        assert result is False
    
    def test_validate_gitlab_signature_valid(self):
        """Test valid GitLab signature validation."""
        payload = b'{"test": "data"}'
        secret = "my-secret"
        
        result = WebhookSignatureValidator.validate_gitlab_signature(
            payload, secret, secret
        )
        assert result is True
    
    def test_validate_gitlab_signature_invalid(self):
        """Test invalid GitLab signature validation."""
        payload = b'{"test": "data"}'
        secret = "my-secret"
        invalid_token = "invalid-token"
        
        result = WebhookSignatureValidator.validate_gitlab_signature(
            payload, invalid_token, secret
        )
        assert result is False


class TestWebhookEvent:
    """Test webhook event data extraction."""
    
    def test_github_push_event_properties(self):
        """Test GitHub push event property extraction."""
        payload = {
            "ref": "refs/heads/main",
            "after": "abc123",
            "commits": [
                {"id": "abc123", "message": "Test commit"}
            ],
            "pusher": {
                "name": "testuser",
                "email": "test@example.com"
            },
            "repository": {
                "full_name": "owner/repo"
            }
        }
        
        event = WebhookEvent(
            provider=GitProvider.GITHUB,
            event_type="push",
            repository_id="repo-123",
            payload=payload
        )
        
        assert event.commit_sha == "abc123"
        assert event.branch == "main"
        assert len(event.commits) == 1
        assert event.pusher["name"] == "testuser"
        assert event.pusher["email"] == "test@example.com"
        assert event.repository_name == "owner/repo"
    
    def test_gitlab_push_event_properties(self):
        """Test GitLab push event property extraction."""
        payload = {
            "ref": "refs/heads/develop",
            "checkout_sha": "def456",
            "commits": [
                {"id": "def456", "message": "GitLab commit"}
            ],
            "user_name": "gitlab-user",
            "user_email": "gitlab@example.com",
            "user_username": "gitlabuser",
            "project": {
                "path_with_namespace": "group/project"
            }
        }
        
        event = WebhookEvent(
            provider=GitProvider.GITLAB,
            event_type="push",
            repository_id="repo-456",
            payload=payload
        )
        
        assert event.commit_sha == "def456"
        assert event.branch == "develop"
        assert len(event.commits) == 1
        assert event.pusher["name"] == "gitlab-user"
        assert event.pusher["email"] == "gitlab@example.com"
        assert event.pusher["username"] == "gitlabuser"
        assert event.repository_name == "group/project"
    
    def test_event_with_no_commits(self):
        """Test event with no commits."""
        payload = {
            "ref": "refs/heads/main",
            "commits": []
        }
        
        event = WebhookEvent(
            provider=GitProvider.GITHUB,
            event_type="push",
            repository_id="repo-123",
            payload=payload
        )
        
        assert len(event.commits) == 0
        assert event.branch == "main"


@pytest.mark.asyncio
class TestWebhookService:
    """Test webhook service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def webhook_service(self, mock_db):
        """Create webhook service instance."""
        return WebhookService(mock_db)
    
    @pytest.fixture
    def sample_repository(self):
        """Create sample repository for testing."""
        return Repository(
            id="repo-123",
            project_id="project-456",
            name="test-repo",
            url="https://github.com/owner/test-repo",
            provider=GitProvider.GITHUB,
            branch="main",
            webhook_id="webhook-789",
            deployment_config={"auto_deploy": True},
            is_active=True
        )
    
    async def test_process_github_push_webhook(self, webhook_service, sample_repository):
        """Test processing GitHub push webhook."""
        payload = {
            "ref": "refs/heads/main",
            "after": "abc123",
            "commits": [
                {
                    "id": "abc123",
                    "message": "Test commit",
                    "author": {"name": "Test User", "email": "test@example.com"}
                }
            ],
            "pusher": {
                "name": "testuser",
                "email": "test@example.com"
            },
            "repository": {
                "html_url": "https://github.com/owner/test-repo",
                "full_name": "owner/test-repo"
            }
        }
        
        headers = {
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": None,
            "X-GitHub-Delivery": "delivery-123"
        }
        
        # Mock repository lookup
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=sample_repository):
            with patch.object(webhook_service, '_validate_signature', return_value=True):
                result = await webhook_service.process_webhook(
                    provider=GitProvider.GITHUB,
                    payload=payload,
                    headers=headers,
                    raw_payload=json.dumps(payload).encode()
                )
        
        assert result["status"] == "processed"
        assert result["action"] == "deployment_triggered"
        assert result["commits"] == 1
        assert result["branch"] == "main"
    
    async def test_process_webhook_repository_not_found(self, webhook_service):
        """Test processing webhook when repository is not found."""
        payload = {
            "repository": {
                "html_url": "https://github.com/unknown/repo"
            }
        }
        
        headers = {"X-GitHub-Event": "push"}
        
        # Mock repository lookup to return None
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=None):
            result = await webhook_service.process_webhook(
                provider=GitProvider.GITHUB,
                payload=payload,
                headers=headers,
                raw_payload=json.dumps(payload).encode()
            )
        
        assert result["status"] == "ignored"
        assert result["reason"] == "repository_not_found"
    
    async def test_process_webhook_invalid_signature(self, webhook_service, sample_repository):
        """Test processing webhook with invalid signature."""
        payload = {"repository": {"html_url": "https://github.com/owner/test-repo"}}
        headers = {"X-GitHub-Event": "push", "X-Hub-Signature-256": "invalid"}
        
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=sample_repository):
            with patch.object(webhook_service, '_validate_signature', return_value=False):
                with patch('app.core.config.settings.WEBHOOK_SECRET', 'test-secret'):
                    result = await webhook_service.process_webhook(
                        provider=GitProvider.GITHUB,
                        payload=payload,
                        headers=headers,
                        raw_payload=json.dumps(payload).encode()
                    )
        
        assert result["status"] == "error"
        assert result["reason"] == "invalid_signature"
    
    async def test_process_push_event_wrong_branch(self, webhook_service, sample_repository):
        """Test processing push event for non-tracked branch."""
        # Repository tracks 'main' branch
        sample_repository.branch = "main"
        
        payload = {
            "ref": "refs/heads/develop",  # Different branch
            "commits": [{"id": "abc123", "message": "Test"}],
            "repository": {"html_url": "https://github.com/owner/test-repo"}
        }
        
        headers = {"X-GitHub-Event": "push"}
        
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=sample_repository):
            with patch.object(webhook_service, '_validate_signature', return_value=True):
                result = await webhook_service.process_webhook(
                    provider=GitProvider.GITHUB,
                    payload=payload,
                    headers=headers,
                    raw_payload=json.dumps(payload).encode()
                )
        
        assert result["status"] == "ignored"
        assert result["reason"] == "branch_not_tracked"
    
    async def test_process_push_event_no_auto_deploy(self, webhook_service, sample_repository):
        """Test processing push event with auto-deploy disabled."""
        # Disable auto-deploy
        sample_repository.deployment_config = {"auto_deploy": False}
        
        payload = {
            "ref": "refs/heads/main",
            "commits": [{"id": "abc123", "message": "Test"}],
            "pusher": {"name": "user", "email": "user@example.com"},
            "repository": {"html_url": "https://github.com/owner/test-repo"}
        }
        
        headers = {"X-GitHub-Event": "push"}
        
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=sample_repository):
            with patch.object(webhook_service, '_validate_signature', return_value=True):
                result = await webhook_service.process_webhook(
                    provider=GitProvider.GITHUB,
                    payload=payload,
                    headers=headers,
                    raw_payload=json.dumps(payload).encode()
                )
        
        assert result["status"] == "processed"
        assert result["action"] == "logged"
    
    async def test_process_pull_request_event(self, webhook_service, sample_repository):
        """Test processing pull request event."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Test PR",
                "user": {"login": "contributor"}
            },
            "repository": {"html_url": "https://github.com/owner/test-repo"}
        }
        
        headers = {"X-GitHub-Event": "pull_request"}
        
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=sample_repository):
            with patch.object(webhook_service, '_validate_signature', return_value=True):
                result = await webhook_service.process_webhook(
                    provider=GitProvider.GITHUB,
                    payload=payload,
                    headers=headers,
                    raw_payload=json.dumps(payload).encode()
                )
        
        assert result["status"] == "processed"
        assert result["action"] == "pr_logged"
        assert result["pr_action"] == "opened"
        assert result["pr_number"] == 42
    
    async def test_process_unsupported_event(self, webhook_service, sample_repository):
        """Test processing unsupported event type."""
        payload = {"repository": {"html_url": "https://github.com/owner/test-repo"}}
        headers = {"X-GitHub-Event": "unsupported_event"}
        
        with patch.object(webhook_service, '_find_repository_by_payload', return_value=sample_repository):
            with patch.object(webhook_service, '_validate_signature', return_value=True):
                result = await webhook_service.process_webhook(
                    provider=GitProvider.GITHUB,
                    payload=payload,
                    headers=headers,
                    raw_payload=json.dumps(payload).encode()
                )
        
        assert result["status"] == "ignored"
        assert result["reason"] == "unsupported_event_type"
    
    async def test_register_webhook(self, webhook_service):
        """Test webhook registration."""
        repository_id = "repo-123"
        webhook_url = "https://example.com/webhook"
        events = ["push", "pull_request"]
        
        # Mock repository lookup
        mock_repo = AsyncMock()
        webhook_service.db.execute = AsyncMock()
        webhook_service.db.execute.return_value.scalar_one_or_none.return_value = mock_repo
        
        result = await webhook_service.register_webhook(
            repository_id=repository_id,
            webhook_url=webhook_url,
            events=events
        )
        
        assert result["status"] == "registered"
        assert result["webhook_url"] == webhook_url
        assert result["events"] == events
        assert result["repository_id"] == repository_id
    
    async def test_register_webhook_repository_not_found(self, webhook_service):
        """Test webhook registration with non-existent repository."""
        # Mock repository lookup to return None
        webhook_service.db.execute = AsyncMock()
        webhook_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(NotFoundError):
            await webhook_service.register_webhook(
                repository_id="nonexistent",
                webhook_url="https://example.com/webhook"
            )
    
    async def test_unregister_webhook(self, webhook_service):
        """Test webhook unregistration."""
        repository_id = "repo-123"
        webhook_id = "webhook-456"
        
        # Mock repository lookup
        mock_repo = AsyncMock()
        mock_repo.webhook_id = webhook_id
        webhook_service.db.execute = AsyncMock()
        webhook_service.db.execute.return_value.scalar_one_or_none.return_value = mock_repo
        webhook_service.db.commit = AsyncMock()
        
        result = await webhook_service.unregister_webhook(repository_id, webhook_id)
        
        assert result is True
        assert mock_repo.webhook_id is None
        webhook_service.db.commit.assert_called_once()
    
    async def test_get_webhook_events(self, webhook_service):
        """Test getting webhook events."""
        repository_id = "repo-123"
        limit = 10
        
        events = await webhook_service.get_webhook_events(repository_id, limit)
        
        # Currently returns empty list as events storage is not implemented
        assert events == []
    
    def test_extract_event_type_github(self, webhook_service):
        """Test extracting event type from GitHub headers."""
        headers = {"X-GitHub-Event": "push"}
        event_type = webhook_service._extract_event_type(GitProvider.GITHUB, headers, {})
        assert event_type == "push"
    
    def test_extract_event_type_gitlab(self, webhook_service):
        """Test extracting event type from GitLab headers."""
        headers = {"X-Gitlab-Event": "Push Hook"}
        event_type = webhook_service._extract_event_type(GitProvider.GITLAB, headers, {})
        assert event_type == "Push Hook"
    
    def test_extract_signature_github(self, webhook_service):
        """Test extracting signature from GitHub headers."""
        headers = {"X-Hub-Signature-256": "sha256=abc123"}
        signature = webhook_service._extract_signature(GitProvider.GITHUB, headers)
        assert signature == "sha256=abc123"
    
    def test_extract_signature_gitlab(self, webhook_service):
        """Test extracting signature from GitLab headers."""
        headers = {"X-Gitlab-Token": "secret-token"}
        signature = webhook_service._extract_signature(GitProvider.GITLAB, headers)
        assert signature == "secret-token"