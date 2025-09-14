"""Tests for repository management service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.repository import RepositoryService, GitHubClient, GitLabClient
from app.models.repository import Repository, GitProvider
from app.models.project import Project
from app.models.user import User
from app.schemas.repository import RepositoryConnectionRequest
from app.core.exceptions import NotFoundError, ValidationError, ExternalServiceError


@pytest.fixture
def repository_service(mock_db_session):
    """Repository service instance with mocked database."""
    return RepositoryService(mock_db_session)


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    return Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        owner_id=uuid4()
    )


@pytest.fixture
def sample_repository():
    """Sample repository for testing."""
    return Repository(
        id=uuid4(),
        project_id=uuid4(),
        name="test-repo",
        url="https://github.com/user/test-repo",
        provider=GitProvider.GITHUB,
        branch="main",
        webhook_id="12345",
        is_active=True,
        deployment_config={
            "auto_deploy": True,
            "build_command": "npm run build",
            "output_directory": "dist",
            "environment_variables": {}
        }
    )


class TestGitHubClient:
    """Test cases for GitHubClient."""

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful GitHub user info retrieval."""
        mock_response = {
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value.status = 200
            mock_request.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            async with GitHubClient("fake_token") as client:
                user_info = await client.get_user_info()
                
                assert user_info["login"] == "testuser"
                assert user_info["name"] == "Test User"
                assert user_info["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_repositories_success(self):
        """Test successful GitHub repositories retrieval."""
        mock_response = [
            {
                "id": 123,
                "name": "test-repo",
                "full_name": "user/test-repo",
                "html_url": "https://github.com/user/test-repo",
                "clone_url": "https://github.com/user/test-repo.git",
                "default_branch": "main",
                "private": False,
                "description": "Test repository",
                "language": "Python",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        ]
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value.status = 200
            mock_request.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            async with GitHubClient("fake_token") as client:
                repos = await client.get_repositories()
                
                assert len(repos) == 1
                assert repos[0]["name"] == "test-repo"
                assert repos[0]["full_name"] == "user/test-repo"
                assert repos[0]["private"] is False

    @pytest.mark.asyncio
    async def test_create_webhook_success(self):
        """Test successful GitHub webhook creation."""
        mock_response = {
            "id": 12345,
            "url": "https://api.github.com/repos/user/repo/hooks/12345",
            "active": True
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value.status = 201
            mock_request.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            async with GitHubClient("fake_token") as client:
                webhook = await client.create_webhook("user", "repo", "https://example.com/webhook")
                
                assert webhook["id"] == 12345
                assert webhook["active"] is True

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test GitHub API error handling."""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value.status = 404
            mock_request.return_value.__aenter__.return_value.text = AsyncMock(return_value="Not Found")
            
            async with GitHubClient("fake_token") as client:
                with pytest.raises(ExternalServiceError, match="Git provider API error: 404"):
                    await client.get_user_info()


class TestGitLabClient:
    """Test cases for GitLabClient."""

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful GitLab user info retrieval."""
        mock_response = {
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value.status = 200
            mock_request.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            async with GitLabClient("fake_token") as client:
                user_info = await client.get_user_info()
                
                assert user_info["username"] == "testuser"
                assert user_info["name"] == "Test User"
                assert user_info["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_repositories_success(self):
        """Test successful GitLab projects retrieval."""
        mock_response = [
            {
                "id": 123,
                "name": "test-project",
                "path_with_namespace": "user/test-project",
                "web_url": "https://gitlab.com/user/test-project",
                "http_url_to_repo": "https://gitlab.com/user/test-project.git",
                "default_branch": "main",
                "visibility": "private",
                "description": "Test project",
                "last_activity_at": "2024-01-15T10:00:00Z"
            }
        ]
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value.status = 200
            mock_request.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            async with GitLabClient("fake_token") as client:
                repos = await client.get_repositories()
                
                assert len(repos) == 1
                assert repos[0]["name"] == "test-project"
                assert repos[0]["full_name"] == "user/test-project"
                assert repos[0]["private"] is True


class TestRepositoryService:
    """Test cases for RepositoryService."""

    @pytest.mark.asyncio
    async def test_connect_repository_success(self, repository_service, mock_db_session, sample_project):
        """Test successful repository connection."""
        # Mock project lookup
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_project
        
        # Mock Git client
        with patch.object(repository_service, '_get_git_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get_repository_info.return_value = {
                "name": "test-repo",
                "full_name": "user/test-repo",
                "description": "Test repository",
                "default_branch": "main",
                "private": False
            }
            mock_client.create_webhook.return_value = {"id": 12345}
            mock_get_client.return_value = mock_client
            
            repository = await repository_service.connect_repository(
                project_id=str(sample_project.id),
                user_id=str(uuid4()),
                provider=GitProvider.GITHUB,
                repository_url="https://github.com/user/test-repo",
                access_token="fake_token"
            )
            
            # Verify repository was created
            assert isinstance(repository, Repository)
            assert repository.name == "test-repo"
            assert repository.provider == GitProvider.GITHUB
            assert repository.webhook_id == "12345"
            
            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_repository_project_not_found(self, repository_service, mock_db_session):
        """Test repository connection with non-existent project."""
        # Mock project not found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(NotFoundError, match="Project with ID .* not found"):
            await repository_service.connect_repository(
                project_id=str(uuid4()),
                user_id=str(uuid4()),
                provider=GitProvider.GITHUB,
                repository_url="https://github.com/user/test-repo",
                access_token="fake_token"
            )

    @pytest.mark.asyncio
    async def test_disconnect_repository_success(self, repository_service, mock_db_session, sample_repository):
        """Test successful repository disconnection."""
        # Mock repository lookup
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_repository
        
        success = await repository_service.disconnect_repository(
            str(sample_repository.id), 
            str(uuid4())
        )
        
        # Verify disconnection
        assert success is True
        assert sample_repository.is_active is False
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_repositories_success(self, repository_service, mock_db_session, sample_project):
        """Test getting project repositories."""
        # Mock project lookup
        mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_project,  # Project lookup
        ]
        
        # Mock repositories query
        mock_repositories = [
            Repository(
                id=uuid4(),
                project_id=sample_project.id,
                name="repo1",
                url="https://github.com/user/repo1",
                provider=GitProvider.GITHUB,
                branch="main",
                is_active=True,
                deployment_config={}
            ),
            Repository(
                id=uuid4(),
                project_id=sample_project.id,
                name="repo2",
                url="https://github.com/user/repo2",
                provider=GitProvider.GITHUB,
                branch="main",
                is_active=True,
                deployment_config={}
            )
        ]
        
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = mock_repositories
        
        repositories = await repository_service.get_project_repositories(
            str(sample_project.id), 
            str(uuid4())
        )
        
        # Verify results
        assert len(repositories) == 2
        assert repositories[0].name == "repo1"
        assert repositories[1].name == "repo2"

    @pytest.mark.asyncio
    async def test_validate_repository_access_success(self, repository_service):
        """Test successful repository access validation."""
        # Mock Git client
        with patch.object(repository_service, '_get_git_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get_user_info.return_value = {
                "login": "testuser",
                "name": "Test User",
                "email": "test@example.com"
            }
            mock_client.get_repository_info.return_value = {
                "name": "test-repo",
                "full_name": "user/test-repo",
                "description": "Test repository",
                "default_branch": "main",
                "private": False,
                "language": "Python"
            }
            mock_client.get_branches.return_value = [
                {"name": "main", "commit_sha": "abc123", "protected": False},
                {"name": "develop", "commit_sha": "def456", "protected": False}
            ]
            mock_get_client.return_value = mock_client
            
            result = await repository_service.validate_repository_access(
                GitProvider.GITHUB,
                "https://github.com/user/test-repo",
                "fake_token"
            )
            
            # Verify validation result
            assert result["valid"] is True
            assert result["user"]["username"] == "testuser"
            assert result["repository"]["name"] == "test-repo"
            assert len(result["branches"]) == 2
            assert "main" in result["branches"]
            assert "develop" in result["branches"]

    @pytest.mark.asyncio
    async def test_validate_repository_access_failure(self, repository_service):
        """Test repository access validation failure."""
        # Mock Git client to raise exception
        with patch.object(repository_service, '_get_git_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get_user_info.side_effect = ExternalServiceError("API error")
            mock_get_client.return_value = mock_client
            
            result = await repository_service.validate_repository_access(
                GitProvider.GITHUB,
                "https://github.com/user/test-repo",
                "invalid_token"
            )
            
            # Verify validation failure
            assert result["valid"] is False
            assert "API error" in result["error"]
            assert result["error_type"] == "api_error"

    @pytest.mark.asyncio
    async def test_get_repository_commits_success(self, repository_service, mock_db_session, sample_repository):
        """Test getting repository commits."""
        # Mock repository lookup
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_repository
        
        # Mock Git client
        with patch.object(repository_service, '_get_git_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get_commits.return_value = [
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
            mock_get_client.return_value = mock_client
            
            commits = await repository_service.get_repository_commits(
                str(sample_repository.id),
                str(uuid4()),
                "fake_token"
            )
            
            # Verify commits
            assert len(commits) == 2
            assert commits[0]["sha"] == "abc123"
            assert commits[0]["message"] == "Initial commit"
            assert commits[1]["sha"] == "def456"
            assert commits[1]["message"] == "Add feature"

    def test_parse_repository_url_github(self, repository_service):
        """Test parsing GitHub repository URLs."""
        test_cases = [
            ("https://github.com/user/repo", {"owner": "user", "name": "repo"}),
            ("https://github.com/user/repo.git", {"owner": "user", "name": "repo"}),
            ("git@github.com:user/repo.git", {"owner": "user", "name": "repo"}),
            ("github.com/user/repo", {"owner": "user", "name": "repo"})
        ]
        
        for url, expected in test_cases:
            result = repository_service._parse_repository_url(url, GitProvider.GITHUB)
            assert result == expected

    def test_parse_repository_url_gitlab(self, repository_service):
        """Test parsing GitLab repository URLs."""
        test_cases = [
            ("https://gitlab.com/user/project", {"owner": "user", "name": "project"}),
            ("https://gitlab.com/user/project.git", {"owner": "user", "name": "project"}),
            ("git@gitlab.com:user/project.git", {"owner": "user", "name": "project"})
        ]
        
        for url, expected in test_cases:
            result = repository_service._parse_repository_url(url, GitProvider.GITLAB)
            assert result == expected

    def test_parse_repository_url_invalid(self, repository_service):
        """Test parsing invalid repository URLs."""
        with pytest.raises(ValidationError, match="Invalid repository URL format"):
            repository_service._parse_repository_url("invalid-url", GitProvider.GITHUB)

    @pytest.mark.asyncio
    async def test_update_repository_config_success(self, repository_service, mock_db_session, sample_repository):
        """Test updating repository configuration."""
        # Mock repository lookup
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_repository
        
        config_updates = {
            "auto_deploy": False,
            "build_command": "npm run build:prod",
            "branch": "develop"
        }
        
        updated_repository = await repository_service.update_repository_config(
            str(sample_repository.id),
            str(uuid4()),
            config_updates
        )
        
        # Verify updates
        assert updated_repository.deployment_config["auto_deploy"] is False
        assert updated_repository.deployment_config["build_command"] == "npm run build:prod"
        assert updated_repository.branch == "develop"
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_repository_service_integration_flow(sample_project):
    """Integration test for complete repository service workflow."""
    mock_db_session = AsyncMock()
    repository_service = RepositoryService(mock_db_session)
    
    # Mock project lookup
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_project
    
    # Mock Git client
    with patch.object(repository_service, '_get_git_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get_repository_info.return_value = {
            "name": "integration-test-repo",
            "full_name": "user/integration-test-repo",
            "description": "Integration test repository",
            "default_branch": "main",
            "private": False
        }
        mock_client.create_webhook.return_value = {"id": 99999}
        mock_get_client.return_value = mock_client
        
        # 1. Connect repository
        repository = await repository_service.connect_repository(
            project_id=str(sample_project.id),
            user_id=str(uuid4()),
            provider=GitProvider.GITHUB,
            repository_url="https://github.com/user/integration-test-repo",
            access_token="fake_token"
        )
        
        assert repository.name == "integration-test-repo"
        assert repository.provider == GitProvider.GITHUB
        
        # 2. Update configuration
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = repository
        
        updated_repository = await repository_service.update_repository_config(
            str(repository.id),
            str(uuid4()),
            {"auto_deploy": False, "build_command": "npm test"}
        )
        
        assert updated_repository.deployment_config["auto_deploy"] is False
        assert updated_repository.deployment_config["build_command"] == "npm test"
        
        # 3. Disconnect repository
        success = await repository_service.disconnect_repository(
            str(repository.id),
            str(uuid4())
        )
        
        assert success is True
        assert repository.is_active is False