"""Integration tests for webhook API endpoints."""

import pytest
import json
import hashlib
import hmac
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.repository import Repository, GitProvider
from app.core.database import get_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def override_get_db(mock_db):
    """Override database dependency."""
    def _override_get_db():
        return mock_db
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


class TestGitHubWebhookEndpoint:
    """Test GitHub webhook endpoint."""
    
    def test_github_webhook_push_event(self, client, override_get_db):
        """Test GitHub push webhook processing."""
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
            "X-GitHub-Delivery": "delivery-123",
            "Content-Type": "application/json"
        }
        
        # Mock webhook service processing
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.process_webhook.return_value = {
                "status": "processed",
                "action": "deployment_triggered",
                "commits": 1,
                "branch": "main"
            }
            
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["event"] == "push"
        assert data["delivery_id"] == "delivery-123"
        assert data["result"]["status"] == "processed"
    
    def test_github_webhook_invalid_json(self, client, override_get_db):
        """Test GitHub webhook with invalid JSON."""
        headers = {
            "X-GitHub-Event": "push",
            "Content-Type": "application/json"
        }
        
        response = client.post(
            "/webhooks/github",
            data="invalid json",
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Invalid JSON payload" in response.json()["detail"]
    
    def test_github_webhook_signature_validation_error(self, client, override_get_db):
        """Test GitHub webhook with signature validation error."""
        payload = {"test": "data"}
        headers = {
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": "sha256=invalid",
            "Content-Type": "application/json"
        }
        
        # Mock webhook service to raise validation error
        with patch('app.api.webhooks.WebhookService') as mock_service:
            from app.core.exceptions import ValidationError
            mock_service.return_value.process_webhook.side_effect = ValidationError("Invalid signature")
            
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]
    
    def test_github_webhook_internal_error(self, client, override_get_db):
        """Test GitHub webhook with internal server error."""
        payload = {"test": "data"}
        headers = {
            "X-GitHub-Event": "push",
            "Content-Type": "application/json"
        }
        
        # Mock webhook service to raise generic exception
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.process_webhook.side_effect = Exception("Database error")
            
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


class TestGitLabWebhookEndpoint:
    """Test GitLab webhook endpoint."""
    
    def test_gitlab_webhook_push_event(self, client, override_get_db):
        """Test GitLab push webhook processing."""
        payload = {
            "ref": "refs/heads/main",
            "checkout_sha": "def456",
            "commits": [
                {
                    "id": "def456",
                    "message": "GitLab commit",
                    "author": {"name": "GitLab User", "email": "gitlab@example.com"}
                }
            ],
            "user_name": "gitlab-user",
            "user_email": "gitlab@example.com",
            "project": {
                "web_url": "https://gitlab.com/group/project",
                "path_with_namespace": "group/project"
            }
        }
        
        headers = {
            "X-Gitlab-Event": "Push Hook",
            "X-Gitlab-Token": "secret-token",
            "Content-Type": "application/json"
        }
        
        # Mock webhook service processing
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.process_webhook.return_value = {
                "status": "processed",
                "action": "deployment_triggered",
                "commits": 1,
                "branch": "main"
            }
            
            response = client.post(
                "/webhooks/gitlab",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["event"] == "Push Hook"
        assert data["result"]["status"] == "processed"
    
    def test_gitlab_webhook_merge_request_event(self, client, override_get_db):
        """Test GitLab merge request webhook processing."""
        payload = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "iid": 42,
                "title": "Test MR",
                "source_branch": "feature",
                "target_branch": "main"
            },
            "user": {
                "username": "contributor",
                "name": "Contributor Name"
            },
            "project": {
                "web_url": "https://gitlab.com/group/project"
            }
        }
        
        headers = {
            "X-Gitlab-Event": "Merge Request Hook",
            "X-Gitlab-Token": "secret-token",
            "Content-Type": "application/json"
        }
        
        # Mock webhook service processing
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.process_webhook.return_value = {
                "status": "processed",
                "action": "mr_logged",
                "mr_action": "open",
                "mr_number": 42
            }
            
            response = client.post(
                "/webhooks/gitlab",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["event"] == "Merge Request Hook"


class TestWebhookManagementEndpoints:
    """Test webhook management endpoints."""
    
    def test_get_webhook_events(self, client, override_get_db):
        """Test getting webhook events for a repository."""
        repository_id = "repo-123"
        
        # Mock webhook service
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.get_webhook_events.return_value = [
                {
                    "id": "event-1",
                    "event_type": "push",
                    "status": "processed",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
            
            response = client.get(f"/webhooks/events/{repository_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["repository_id"] == repository_id
        assert len(data["events"]) == 1
        assert data["count"] == 1
    
    def test_get_webhook_events_with_limit(self, client, override_get_db):
        """Test getting webhook events with custom limit."""
        repository_id = "repo-123"
        limit = 10
        
        # Mock webhook service
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.get_webhook_events.return_value = []
            
            response = client.get(f"/webhooks/events/{repository_id}?limit={limit}")
        
        assert response.status_code == 200
        # Verify the service was called with correct limit
        mock_service.return_value.get_webhook_events.assert_called_once_with(repository_id, limit)
    
    def test_get_webhook_events_repository_not_found(self, client, override_get_db):
        """Test getting webhook events for non-existent repository."""
        repository_id = "nonexistent"
        
        # Mock webhook service to raise NotFoundError
        with patch('app.api.webhooks.WebhookService') as mock_service:
            from app.core.exceptions import NotFoundError
            mock_service.return_value.get_webhook_events.side_effect = NotFoundError("Repository not found")
            
            response = client.get(f"/webhooks/events/{repository_id}")
        
        assert response.status_code == 404
        assert "Repository not found" in response.json()["detail"]
    
    def test_register_webhook(self, client, override_get_db):
        """Test webhook registration."""
        repository_id = "repo-123"
        webhook_data = {
            "webhook_url": "https://example.com/webhook",
            "events": ["push", "pull_request"]
        }
        
        # Mock webhook service
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.register_webhook.return_value = {
                "status": "registered",
                "webhook_id": "webhook-456",
                "webhook_url": webhook_data["webhook_url"],
                "events": webhook_data["events"]
            }
            
            response = client.post(
                f"/webhooks/register/{repository_id}",
                json=webhook_data
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["webhook_url"] == webhook_data["webhook_url"]
    
    def test_register_webhook_missing_url(self, client, override_get_db):
        """Test webhook registration without webhook URL."""
        repository_id = "repo-123"
        webhook_data = {"events": ["push"]}
        
        response = client.post(
            f"/webhooks/register/{repository_id}",
            json=webhook_data
        )
        
        assert response.status_code == 400
        assert "webhook_url is required" in response.json()["detail"]
    
    def test_register_webhook_repository_not_found(self, client, override_get_db):
        """Test webhook registration for non-existent repository."""
        repository_id = "nonexistent"
        webhook_data = {"webhook_url": "https://example.com/webhook"}
        
        # Mock webhook service to raise NotFoundError
        with patch('app.api.webhooks.WebhookService') as mock_service:
            from app.core.exceptions import NotFoundError
            mock_service.return_value.register_webhook.side_effect = NotFoundError("Repository not found")
            
            response = client.post(
                f"/webhooks/register/{repository_id}",
                json=webhook_data
            )
        
        assert response.status_code == 404
        assert "Repository not found" in response.json()["detail"]
    
    def test_unregister_webhook(self, client, override_get_db):
        """Test webhook unregistration."""
        repository_id = "repo-123"
        webhook_id = "webhook-456"
        
        # Mock webhook service
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.unregister_webhook.return_value = True
            
            response = client.delete(f"/webhooks/unregister/{repository_id}/{webhook_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["repository_id"] == repository_id
        assert data["webhook_id"] == webhook_id
    
    def test_unregister_webhook_failed(self, client, override_get_db):
        """Test failed webhook unregistration."""
        repository_id = "repo-123"
        webhook_id = "webhook-456"
        
        # Mock webhook service to return False
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.unregister_webhook.return_value = False
            
            response = client.delete(f"/webhooks/unregister/{repository_id}/{webhook_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
    
    def test_webhook_test_endpoint(self, client):
        """Test webhook test endpoint."""
        response = client.get("/webhooks/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Webhook endpoint is accessible" in data["message"]


class TestWebhookSignatureIntegration:
    """Test webhook signature validation in API endpoints."""
    
    def test_github_webhook_with_valid_signature(self, client, override_get_db):
        """Test GitHub webhook with valid signature."""
        payload = {"test": "data"}
        secret = "test-secret"
        payload_bytes = json.dumps(payload).encode()
        
        # Create valid signature
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": f"sha256={signature}",
            "Content-Type": "application/json"
        }
        
        # Mock webhook service processing
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.process_webhook.return_value = {
                "status": "processed"
            }
            
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 200
        
        # Verify the service was called with correct parameters
        mock_service.return_value.process_webhook.assert_called_once()
        call_args = mock_service.return_value.process_webhook.call_args
        assert call_args[1]["provider"] == GitProvider.GITHUB
        assert call_args[1]["payload"] == payload
        assert call_args[1]["headers"]["X-Hub-Signature-256"] == f"sha256={signature}"
    
    def test_gitlab_webhook_with_token(self, client, override_get_db):
        """Test GitLab webhook with token."""
        payload = {"test": "data"}
        token = "secret-token"
        
        headers = {
            "X-Gitlab-Event": "Push Hook",
            "X-Gitlab-Token": token,
            "Content-Type": "application/json"
        }
        
        # Mock webhook service processing
        with patch('app.api.webhooks.WebhookService') as mock_service:
            mock_service.return_value.process_webhook.return_value = {
                "status": "processed"
            }
            
            response = client.post(
                "/webhooks/gitlab",
                json=payload,
                headers=headers
            )
        
        assert response.status_code == 200
        
        # Verify the service was called with correct parameters
        mock_service.return_value.process_webhook.assert_called_once()
        call_args = mock_service.return_value.process_webhook.call_args
        assert call_args[1]["provider"] == GitProvider.GITLAB
        assert call_args[1]["payload"] == payload
        assert call_args[1]["headers"]["X-Gitlab-Token"] == token