"""Tests for repository API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.models.repository import Repository, GitProvider
from app.models.user import User
from app.schemas.repository import RepositoryValidationResult, GitUser, GitRepository
from app.core.exceptions import NotFoundError, ValidationError, ExternalServiceError


class TestRepositoryAPI:
    """Test cases for repository API endpoints."""

    @pytest.mark.asyncio
    async def test_connect_repository_success(self, client, mock_current_user):
        """Test successful repository connection."""
        project_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_repository = Repository(
                id=uuid4(),
                project_id=uuid4(project_id),
                name="test-repo",
                url="https://github.com/user/test-repo",
                provider=GitProvider.GITHUB,
                branch="main",
                webhook_id="12345",
                is_active=True,
                deployment_config={
                    "auto_deploy": True,
                    "build_command": "",
                    "output_directory": "",
                    "environment_variables": {}
                }
            )
            mock_service.return_value.connect_repository = AsyncMock(return_value=mock_repository)
            
            connection_data = {
                "provider": "github",
                "repository_url": "https://github.com/user/test-repo",
                "access_token": "fake_token",
                "branch": "main",
                "deployment_config": {
                    "auto_deploy": True,
                    "build_command": "npm run build",
                    "output_directory": "dist",
                    "environment_variables": {}
                }
            }
            
            response = await client.post(f"/projects/{project_id}/repositories", json=connection_data)
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "test-repo"
            assert data["provider"] == "github"
            assert data["webhook_id"] == "12345"
            
            # Verify service was called
            mock_service.return_value.connect_repository.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_repository_validation_error(self, client, mock_current_user):
        """Test repository connection with validation error."""
        project_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_service.return_value.connect_repository = AsyncMock(
                side_effect=ValidationError("Invalid repository URL")
            )
            
            connection_data = {
                "provider": "github",
                "repository_url": "invalid-url",
                "access_token": "fake_token"
            }
            
            response = await client.post(f"/projects/{project_id}/repositories", json=connection_data)
            
            # Verify validation error
            assert response.status_code == 400
            assert "Invalid repository URL" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_connect_repository_external_service_error(self, client, mock_current_user):
        """Test repository connection with external service error."""
        project_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_service.return_value.connect_repository = AsyncMock(
                side_effect=ExternalServiceError("GitHub API error")
            )
            
            connection_data = {
                "provider": "github",
                "repository_url": "https://github.com/user/test-repo",
                "access_token": "invalid_token"
            }
            
            response = await client.post(f"/projects/{project_id}/repositories", json=connection_data)
            
            # Verify external service error
            assert response.status_code == 502
            assert "GitHub API error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_disconnect_repository_success(self, client, mock_current_user):
        """Test successful repository disconnection."""
        repository_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_service.return_value.disconnect_repository = AsyncMock(return_value=True)
            
            response = await client.delete(f"/repositories/{repository_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "disconnected successfully" in data["message"]
            
            # Verify service was called
            mock_service.return_value.disconnect_repository.assert_called_once_with(
                repository_id, str(mock_current_user.id)
            )

    @pytest.mark.asyncio
    async def test_disconnect_repository_not_found(self, client, mock_current_user):
        """Test repository disconnection with repository not found."""
        repository_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_service.return_value.disconnect_repository = AsyncMock(
                side_effect=NotFoundError("Repository not found")
            )
            
            response = await client.delete(f"/repositories/{repository_id}")
            
            # Verify not found error
            assert response.status_code == 404
            assert "Repository not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_project_repositories_success(self, client, mock_current_user):
        """Test getting project repositories."""
        project_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_repositories = [
                Repository(
                    id=uuid4(),
                    project_id=uuid4(project_id),
                    name="repo1",
                    url="https://github.com/user/repo1",
                    provider=GitProvider.GITHUB,
                    branch="main",
                    is_active=True,
                    deployment_config={}
                ),
                Repository(
                    id=uuid4(),
                    project_id=uuid4(project_id),
                    name="repo2",
                    url="https://gitlab.com/user/repo2",
                    provider=GitProvider.GITLAB,
                    branch="develop",
                    is_active=True,
                    deployment_config={}
                )
            ]
            mock_service.return_value.get_project_repositories = AsyncMock(return_value=mock_repositories)
            
            response = await client.get(f"/projects/{project_id}/repositories")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "repo1"
            assert data[0]["provider"] == "github"
            assert data[1]["name"] == "repo2"
            assert data[1]["provider"] == "gitlab"

    @pytest.mark.asyncio
    async def test_get_repository_info_success(self, client, mock_current_user):
        """Test getting repository information."""
        repository_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_repo_info = {
                "id": repository_id,
                "name": "test-repo",
                "url": "https://github.com/user/test-repo",
                "provider": "github",
                "branch": "main",
                "is_active": True,
                "deployment_config": {
                    "auto_deploy": True,
                    "build_command": "npm run build",
                    "output_directory": "dist",
                    "environment_variables": {}
                },
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "owner": "user",
                "repo_name": "test-repo"
            }
            mock_service.return_value.get_repository_info = AsyncMock(return_value=mock_repo_info)
            
            response = await client.get(f"/repositories/{repository_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-repo"
            assert data["provider"] == "github"
            assert data["owner"] == "user"
            assert data["repo_name"] == "test-repo"

    @pytest.mark.asyncio
    async def test_update_repository_config_success(self, client, mock_current_user):
        """Test updating repository configuration."""
        repository_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_repository = Repository(
                id=uuid4(repository_id),
                project_id=uuid4(),
                name="test-repo",
                url="https://github.com/user/test-repo",
                provider=GitProvider.GITHUB,
                branch="develop",  # Updated branch
                is_active=True,
                deployment_config={
                    "auto_deploy": False,  # Updated config
                    "build_command": "npm run build:prod",
                    "output_directory": "build",
                    "environment_variables": {"NODE_ENV": "production"}
                }
            )
            mock_service.return_value.update_repository_config = AsyncMock(return_value=mock_repository)
            
            config_update = {
                "branch": "develop",
                "auto_deploy": False,
                "build_command": "npm run build:prod",
                "output_directory": "build",
                "environment_variables": {"NODE_ENV": "production"}
            }
            
            response = await client.put(f"/repositories/{repository_id}/config", json=config_update)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["branch"] == "develop"
            assert data["deployment_config"]["auto_deploy"] is False
            assert data["deployment_config"]["build_command"] == "npm run build:prod"

    @pytest.mark.asyncio
    async def test_validate_repository_access_success(self, client, mock_current_user):
        """Test successful repository access validation."""
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_validation_result = {
                "valid": True,
                "user": {
                    "username": "testuser",
                    "name": "Test User",
                    "email": "test@example.com"
                },
                "repository": {
                    "name": "test-repo",
                    "full_name": "user/test-repo",
                    "description": "Test repository",
                    "default_branch": "main",
                    "private": False,
                    "language": "Python"
                },
                "branches": ["main", "develop", "feature/test"],
                "permissions": {
                    "read": True,
                    "write": True,
                    "admin": True
                }
            }
            mock_service.return_value.validate_repository_access = AsyncMock(return_value=mock_validation_result)
            
            validation_data = {
                "provider": "github",
                "repository_url": "https://github.com/user/test-repo",
                "access_token": "fake_token"
            }
            
            response = await client.post("/repositories/validate", json=validation_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user"]["username"] == "testuser"
            assert data["repository"]["name"] == "test-repo"
            assert len(data["branches"]) == 3
            assert data["permissions"]["admin"] is True

    @pytest.mark.asyncio
    async def test_validate_repository_access_failure(self, client, mock_current_user):
        """Test repository access validation failure."""
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_validation_result = {
                "valid": False,
                "error": "Invalid access token",
                "error_type": "authentication_error"
            }
            mock_service.return_value.validate_repository_access = AsyncMock(return_value=mock_validation_result)
            
            validation_data = {
                "provider": "github",
                "repository_url": "https://github.com/user/test-repo",
                "access_token": "invalid_token"
            }
            
            response = await client.post("/repositories/validate", json=validation_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "Invalid access token" in data["error"]
            assert data["error_type"] == "authentication_error"

    @pytest.mark.asyncio
    async def test_get_repository_commits_success(self, client, mock_current_user):
        """Test getting repository commits."""
        repository_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_commits = [
                {
                    "sha": "abc123",
                    "message": "Initial commit",
                    "author": {"name": "Test User", "email": "test@example.com"},
                    "date": "2024-01-15T10:00:00Z",
                    "url": "https://github.com/user/repo/commit/abc123"
                },
                {
                    "sha": "def456",
                    "message": "Add feature",
                    "author": {"name": "Test User", "email": "test@example.com"},
                    "date": "2024-01-15T11:00:00Z",
                    "url": "https://github.com/user/repo/commit/def456"
                }
            ]
            mock_service.return_value.get_repository_commits = AsyncMock(return_value=mock_commits)
            
            response = await client.get(
                f"/repositories/{repository_id}/commits",
                params={"access_token": "fake_token", "limit": 10}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["sha"] == "abc123"
            assert data[0]["message"] == "Initial commit"
            assert data[1]["sha"] == "def456"
            assert data[1]["message"] == "Add feature"

    @pytest.mark.asyncio
    async def test_get_repository_commits_with_branch(self, client, mock_current_user):
        """Test getting repository commits from specific branch."""
        repository_id = str(uuid4())
        
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_service.return_value.get_repository_commits = AsyncMock(return_value=[])
            
            response = await client.get(
                f"/repositories/{repository_id}/commits",
                params={"access_token": "fake_token", "branch": "develop", "limit": 5}
            )
            
            # Verify response
            assert response.status_code == 200
            
            # Verify service was called with correct parameters
            mock_service.return_value.get_repository_commits.assert_called_once_with(
                repository_id=repository_id,
                user_id=str(mock_current_user.id),
                access_token="fake_token",
                branch="develop",
                limit=5
            )

    @pytest.mark.asyncio
    async def test_get_user_repositories_success(self, client, mock_current_user):
        """Test getting user repositories from Git provider."""
        with patch('app.api.repository.RepositoryService') as mock_service:
            mock_repositories = [
                {
                    "id": 123,
                    "name": "repo1",
                    "full_name": "user/repo1",
                    "url": "https://github.com/user/repo1",
                    "clone_url": "https://github.com/user/repo1.git",
                    "default_branch": "main",
                    "private": False,
                    "description": "Repository 1",
                    "language": "Python",
                    "updated_at": "2024-01-15T10:00:00Z"
                },
                {
                    "id": 456,
                    "name": "repo2",
                    "full_name": "user/repo2",
                    "url": "https://github.com/user/repo2",
                    "clone_url": "https://github.com/user/repo2.git",
                    "default_branch": "main",
                    "private": True,
                    "description": "Repository 2",
                    "language": "JavaScript",
                    "updated_at": "2024-01-15T11:00:00Z"
                }
            ]
            mock_service.return_value.get_user_repositories = AsyncMock(return_value=mock_repositories)
            
            response = await client.get(
                "/git-providers/github/repositories",
                params={"access_token": "fake_token"}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "repo1"
            assert data[0]["private"] is False
            assert data[1]["name"] == "repo2"
            assert data[1]["private"] is True

    @pytest.mark.asyncio
    async def test_get_repository_stats_success(self, client, mock_current_user):
        """Test getting repository statistics."""
        response = await client.get("/repositories/stats")
        
        # Verify response (using mock data from endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "total_repositories" in data
        assert "repositories_by_provider" in data
        assert "active_repositories" in data
        assert "repositories_with_webhooks" in data
        assert "recent_connections" in data

    @pytest.mark.asyncio
    async def test_sync_repository_success(self, client, mock_current_user):
        """Test manual repository sync."""
        repository_id = str(uuid4())
        
        response = await client.post(
            f"/repositories/{repository_id}/sync",
            params={"access_token": "fake_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sync initiated" in data["message"]
        assert data["repository_id"] == repository_id

    @pytest.mark.asyncio
    async def test_repository_system_health_success(self, client):
        """Test repository system health check."""
        response = await client.get("/repositories/health")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "features" in data
        assert "providers" in data
        assert data["features"]["github_integration"] is True
        assert data["features"]["gitlab_integration"] is True
        assert data["providers"]["github"]["status"] == "operational"
        assert data["providers"]["gitlab"]["status"] == "operational"

    @pytest.mark.asyncio
    async def test_invalid_request_data(self, client, mock_current_user):
        """Test API endpoints with invalid request data."""
        project_id = str(uuid4())
        
        # Missing required fields
        invalid_connection_data = {
            "provider": "github"
            # Missing repository_url and access_token
        }
        
        response = await client.post(f"/projects/{project_id}/repositories", json=invalid_connection_data)
        
        # Verify validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_git_provider(self, client, mock_current_user):
        """Test API endpoints with invalid Git provider."""
        response = await client.get(
            "/git-providers/invalid_provider/repositories",
            params={"access_token": "fake_token"}
        )
        
        # Verify validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_access_token(self, client, mock_current_user):
        """Test endpoints that require access token without providing it."""
        repository_id = str(uuid4())
        
        response = await client.get(f"/repositories/{repository_id}/commits")
        
        # Verify validation error for missing access token
        assert response.status_code == 422