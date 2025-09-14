"""Repository management service for Git provider integrations."""

import asyncio
import logging
import aiohttp
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.repository import Repository, GitProvider
from app.models.project import Project
from app.models.user import User
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, ExternalServiceError

logger = logging.getLogger(__name__)


class GitProviderClient:
    """Base class for Git provider API clients."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Git provider API."""
        headers = kwargs.get('headers', {})
        headers.update(self._get_auth_headers())
        kwargs['headers'] = headers
        
        async with self.session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise ExternalServiceError(
                    f"Git provider API error: {response.status} - {error_text}"
                )
            return await response.json()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the provider."""
        raise NotImplementedError
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        raise NotImplementedError
    
    async def get_repositories(self) -> List[Dict[str, Any]]:
        """Get user's repositories."""
        raise NotImplementedError
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get specific repository information."""
        raise NotImplementedError
    
    async def create_webhook(self, owner: str, repo: str, webhook_url: str) -> Dict[str, Any]:
        """Create webhook for repository."""
        raise NotImplementedError
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: str) -> bool:
        """Delete webhook from repository."""
        raise NotImplementedError
    
    async def get_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get repository branches."""
        raise NotImplementedError
    
    async def get_commits(self, owner: str, repo: str, branch: str = "main", limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits from repository."""
        raise NotImplementedError


class GitHubClient(GitProviderClient):
    """GitHub API client."""
    
    BASE_URL = "https://api.github.com"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get GitHub user information."""
        return await self._make_request("GET", f"{self.BASE_URL}/user")
    
    async def get_repositories(self) -> List[Dict[str, Any]]:
        """Get user's GitHub repositories."""
        repos = await self._make_request("GET", f"{self.BASE_URL}/user/repos")
        return [
            {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "url": repo["html_url"],
                "clone_url": repo["clone_url"],
                "default_branch": repo["default_branch"],
                "private": repo["private"],
                "description": repo.get("description", ""),
                "language": repo.get("language"),
                "updated_at": repo["updated_at"]
            }
            for repo in repos
        ]
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get GitHub repository information."""
        repo_data = await self._make_request("GET", f"{self.BASE_URL}/repos/{owner}/{repo}")
        return {
            "id": repo_data["id"],
            "name": repo_data["name"],
            "full_name": repo_data["full_name"],
            "url": repo_data["html_url"],
            "clone_url": repo_data["clone_url"],
            "default_branch": repo_data["default_branch"],
            "private": repo_data["private"],
            "description": repo_data.get("description", ""),
            "language": repo_data.get("language"),
            "updated_at": repo_data["updated_at"]
        }
    
    async def create_webhook(self, owner: str, repo: str, webhook_url: str) -> Dict[str, Any]:
        """Create GitHub webhook."""
        webhook_data = {
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
        }
        
        return await self._make_request(
            "POST", 
            f"{self.BASE_URL}/repos/{owner}/{repo}/hooks",
            json=webhook_data
        )
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: str) -> bool:
        """Delete GitHub webhook."""
        try:
            await self._make_request(
                "DELETE", 
                f"{self.BASE_URL}/repos/{owner}/{repo}/hooks/{webhook_id}"
            )
            return True
        except ExternalServiceError:
            return False
    
    async def get_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get GitHub repository branches."""
        branches = await self._make_request("GET", f"{self.BASE_URL}/repos/{owner}/{repo}/branches")
        return [
            {
                "name": branch["name"],
                "commit_sha": branch["commit"]["sha"],
                "protected": branch.get("protected", False)
            }
            for branch in branches
        ]
    
    async def get_commits(self, owner: str, repo: str, branch: str = "main", limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent GitHub commits."""
        params = {"sha": branch, "per_page": limit}
        commits = await self._make_request(
            "GET", 
            f"{self.BASE_URL}/repos/{owner}/{repo}/commits",
            params=params
        )
        
        return [
            {
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": {
                    "name": commit["commit"]["author"]["name"],
                    "email": commit["commit"]["author"]["email"]
                },
                "date": commit["commit"]["author"]["date"],
                "url": commit["html_url"]
            }
            for commit in commits
        ]


class GitLabClient(GitProviderClient):
    """GitLab API client."""
    
    BASE_URL = "https://gitlab.com/api/v4"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get GitLab user information."""
        return await self._make_request("GET", f"{self.BASE_URL}/user")
    
    async def get_repositories(self) -> List[Dict[str, Any]]:
        """Get user's GitLab projects."""
        projects = await self._make_request("GET", f"{self.BASE_URL}/projects?owned=true")
        return [
            {
                "id": project["id"],
                "name": project["name"],
                "full_name": project["path_with_namespace"],
                "url": project["web_url"],
                "clone_url": project["http_url_to_repo"],
                "default_branch": project["default_branch"],
                "private": project["visibility"] == "private",
                "description": project.get("description", ""),
                "updated_at": project["last_activity_at"]
            }
            for project in projects
        ]
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get GitLab project information."""
        project_path = f"{owner}/{repo}".replace("/", "%2F")
        project_data = await self._make_request("GET", f"{self.BASE_URL}/projects/{project_path}")
        
        return {
            "id": project_data["id"],
            "name": project_data["name"],
            "full_name": project_data["path_with_namespace"],
            "url": project_data["web_url"],
            "clone_url": project_data["http_url_to_repo"],
            "default_branch": project_data["default_branch"],
            "private": project_data["visibility"] == "private",
            "description": project_data.get("description", ""),
            "updated_at": project_data["last_activity_at"]
        }
    
    async def create_webhook(self, owner: str, repo: str, webhook_url: str) -> Dict[str, Any]:
        """Create GitLab webhook."""
        project_path = f"{owner}/{repo}".replace("/", "%2F")
        webhook_data = {
            "url": webhook_url,
            "push_events": True,
            "merge_requests_events": True,
            "enable_ssl_verification": True
        }
        
        return await self._make_request(
            "POST",
            f"{self.BASE_URL}/projects/{project_path}/hooks",
            json=webhook_data
        )
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: str) -> bool:
        """Delete GitLab webhook."""
        try:
            project_path = f"{owner}/{repo}".replace("/", "%2F")
            await self._make_request(
                "DELETE",
                f"{self.BASE_URL}/projects/{project_path}/hooks/{webhook_id}"
            )
            return True
        except ExternalServiceError:
            return False
    
    async def get_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get GitLab repository branches."""
        project_path = f"{owner}/{repo}".replace("/", "%2F")
        branches = await self._make_request("GET", f"{self.BASE_URL}/projects/{project_path}/repository/branches")
        
        return [
            {
                "name": branch["name"],
                "commit_sha": branch["commit"]["id"],
                "protected": branch.get("protected", False)
            }
            for branch in branches
        ]
    
    async def get_commits(self, owner: str, repo: str, branch: str = "main", limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent GitLab commits."""
        project_path = f"{owner}/{repo}".replace("/", "%2F")
        params = {"ref_name": branch, "per_page": limit}
        commits = await self._make_request(
            "GET",
            f"{self.BASE_URL}/projects/{project_path}/repository/commits",
            params=params
        )
        
        return [
            {
                "sha": commit["id"],
                "message": commit["message"],
                "author": {
                    "name": commit["author_name"],
                    "email": commit["author_email"]
                },
                "date": commit["authored_date"],
                "url": commit["web_url"]
            }
            for commit in commits
        ]

c
lass RepositoryService:
    """Service for managing repository connections and Git provider integrations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _get_git_client(self, provider: GitProvider, access_token: str) -> GitProviderClient:
        """Get appropriate Git provider client."""
        if provider == GitProvider.GITHUB:
            return GitHubClient(access_token)
        elif provider == GitProvider.GITLAB:
            return GitLabClient(access_token)
        else:
            raise ValidationError(f"Unsupported Git provider: {provider}")
    
    async def connect_repository(
        self, 
        project_id: str, 
        user_id: str,
        provider: GitProvider,
        repository_url: str,
        access_token: str,
        branch: str = "main",
        deployment_config: Optional[Dict[str, Any]] = None
    ) -> Repository:
        """
        Connect a Git repository to a project.
        
        Args:
            project_id: Project ID
            user_id: User ID connecting the repository
            provider: Git provider (GitHub, GitLab, etc.)
            repository_url: Repository URL
            access_token: User's access token for the provider
            branch: Branch to track (default: main)
            deployment_config: Optional deployment configuration
            
        Returns:
            Created repository record
        """
        # Validate project exists and user has access
        project = await self._get_project_with_access(project_id, user_id)
        
        # Parse repository information from URL
        repo_info = self._parse_repository_url(repository_url, provider)
        
        # Validate repository access with Git provider
        async with self._get_git_client(provider, access_token) as git_client:
            try:
                remote_repo = await git_client.get_repository_info(
                    repo_info["owner"], 
                    repo_info["name"]
                )
            except ExternalServiceError as e:
                raise ValidationError(f"Cannot access repository: {str(e)}")
            
            # Create webhook for the repository
            webhook_url = f"{settings.BASE_URL}/api/webhooks/{provider.value}"
            try:
                webhook = await git_client.create_webhook(
                    repo_info["owner"],
                    repo_info["name"],
                    webhook_url
                )
                webhook_id = str(webhook.get("id"))
            except ExternalServiceError as e:
                logger.warning(f"Failed to create webhook: {e}")
                webhook_id = None
        
        # Create repository record
        repository = Repository(
            project_id=UUID(project_id),
            name=remote_repo["name"],
            url=repository_url,
            provider=provider,
            branch=branch,
            webhook_id=webhook_id,
            deployment_config=deployment_config or {
                "auto_deploy": True,
                "build_command": "",
                "output_directory": "",
                "environment_variables": {}
            }
        )
        
        self.db.add(repository)
        await self.db.commit()
        await self.db.refresh(repository)
        
        logger.info(f"Repository connected: {repository_url} to project {project_id}")
        return repository
    
    async def disconnect_repository(self, repository_id: str, user_id: str) -> bool:
        """
        Disconnect a repository from a project.
        
        Args:
            repository_id: Repository ID to disconnect
            user_id: User ID requesting disconnection
            
        Returns:
            True if successfully disconnected
        """
        # Get repository with project access check
        repository = await self._get_repository_with_access(repository_id, user_id)
        
        # Remove webhook if it exists
        if repository.webhook_id:
            # We'd need to store the access token to remove webhooks
            # For now, we'll just mark the repository as inactive
            logger.warning(f"Cannot remove webhook {repository.webhook_id} - access token not stored")
        
        # Mark repository as inactive instead of deleting to preserve history
        repository.is_active = False
        await self.db.commit()
        
        logger.info(f"Repository disconnected: {repository.url}")
        return True
    
    async def get_project_repositories(self, project_id: str, user_id: str) -> List[Repository]:
        """
        Get all repositories connected to a project.
        
        Args:
            project_id: Project ID
            user_id: User ID requesting repositories
            
        Returns:
            List of connected repositories
        """
        # Validate project access
        await self._get_project_with_access(project_id, user_id)
        
        query = select(Repository).where(
            and_(
                Repository.project_id == UUID(project_id),
                Repository.is_active == True
            )
        ).order_by(Repository.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_repository_info(self, repository_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get detailed repository information.
        
        Args:
            repository_id: Repository ID
            user_id: User ID requesting information
            
        Returns:
            Repository information with Git provider data
        """
        repository = await self._get_repository_with_access(repository_id, user_id)
        
        # Parse repository URL to get owner/name
        repo_info = self._parse_repository_url(repository.url, repository.provider)
        
        # Get basic repository data
        repo_data = {
            "id": str(repository.id),
            "name": repository.name,
            "url": repository.url,
            "provider": repository.provider.value,
            "branch": repository.branch,
            "is_active": repository.is_active,
            "deployment_config": repository.deployment_config,
            "created_at": repository.created_at.isoformat(),
            "updated_at": repository.updated_at.isoformat(),
            "owner": repo_info["owner"],
            "repo_name": repo_info["name"]
        }
        
        return repo_data
    
    async def update_repository_config(
        self, 
        repository_id: str, 
        user_id: str,
        config_updates: Dict[str, Any]
    ) -> Repository:
        """
        Update repository deployment configuration.
        
        Args:
            repository_id: Repository ID
            user_id: User ID updating configuration
            config_updates: Configuration updates
            
        Returns:
            Updated repository record
        """
        repository = await self._get_repository_with_access(repository_id, user_id)
        
        # Update deployment configuration
        current_config = repository.deployment_config or {}
        current_config.update(config_updates)
        repository.deployment_config = current_config
        
        # Update branch if provided
        if "branch" in config_updates:
            repository.branch = config_updates["branch"]
        
        await self.db.commit()
        await self.db.refresh(repository)
        
        return repository
    
    async def validate_repository_access(
        self, 
        provider: GitProvider,
        repository_url: str,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Validate access to a repository using provided credentials.
        
        Args:
            provider: Git provider
            repository_url: Repository URL
            access_token: Access token
            
        Returns:
            Repository validation result
        """
        try:
            repo_info = self._parse_repository_url(repository_url, provider)
            
            async with self._get_git_client(provider, access_token) as git_client:
                # Test user authentication
                user_info = await git_client.get_user_info()
                
                # Test repository access
                remote_repo = await git_client.get_repository_info(
                    repo_info["owner"],
                    repo_info["name"]
                )
                
                # Get branches
                branches = await git_client.get_branches(
                    repo_info["owner"],
                    repo_info["name"]
                )
                
                return {
                    "valid": True,
                    "user": {
                        "username": user_info.get("login") or user_info.get("username"),
                        "name": user_info.get("name"),
                        "email": user_info.get("email")
                    },
                    "repository": {
                        "name": remote_repo["name"],
                        "full_name": remote_repo["full_name"],
                        "description": remote_repo["description"],
                        "default_branch": remote_repo["default_branch"],
                        "private": remote_repo["private"],
                        "language": remote_repo.get("language")
                    },
                    "branches": [branch["name"] for branch in branches],
                    "permissions": {
                        "read": True,
                        "write": True,  # Assume write access if we can read
                        "admin": True   # Assume admin if we can create webhooks
                    }
                }
        
        except ExternalServiceError as e:
            return {
                "valid": False,
                "error": str(e),
                "error_type": "api_error"
            }
        except ValidationError as e:
            return {
                "valid": False,
                "error": str(e),
                "error_type": "validation_error"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown_error"
            }
    
    async def get_repository_commits(
        self, 
        repository_id: str, 
        user_id: str,
        access_token: str,
        branch: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent commits from a repository.
        
        Args:
            repository_id: Repository ID
            user_id: User ID requesting commits
            access_token: Access token for Git provider
            branch: Branch to get commits from (default: repository branch)
            limit: Number of commits to retrieve
            
        Returns:
            List of recent commits
        """
        repository = await self._get_repository_with_access(repository_id, user_id)
        repo_info = self._parse_repository_url(repository.url, repository.provider)
        
        target_branch = branch or repository.branch
        
        async with self._get_git_client(repository.provider, access_token) as git_client:
            commits = await git_client.get_commits(
                repo_info["owner"],
                repo_info["name"],
                target_branch,
                limit
            )
            
            return commits
    
    async def get_user_repositories(
        self, 
        provider: GitProvider,
        access_token: str
    ) -> List[Dict[str, Any]]:
        """
        Get user's repositories from Git provider.
        
        Args:
            provider: Git provider
            access_token: User's access token
            
        Returns:
            List of user's repositories
        """
        async with self._get_git_client(provider, access_token) as git_client:
            repositories = await git_client.get_repositories()
            return repositories
    
    def _parse_repository_url(self, url: str, provider: GitProvider) -> Dict[str, str]:
        """Parse repository URL to extract owner and repository name."""
        import re
        
        # Remove .git suffix if present
        url = url.rstrip('.git')
        
        if provider == GitProvider.GITHUB:
            # GitHub URL patterns
            patterns = [
                r'https://github\.com/([^/]+)/([^/]+)',
                r'git@github\.com:([^/]+)/([^/]+)',
                r'github\.com/([^/]+)/([^/]+)'
            ]
        elif provider == GitProvider.GITLAB:
            # GitLab URL patterns
            patterns = [
                r'https://gitlab\.com/([^/]+)/([^/]+)',
                r'git@gitlab\.com:([^/]+)/([^/]+)',
                r'gitlab\.com/([^/]+)/([^/]+)'
            ]
        else:
            raise ValidationError(f"Unsupported provider: {provider}")
        
        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                return {
                    "owner": match.group(1),
                    "name": match.group(2)
                }
        
        raise ValidationError(f"Invalid repository URL format: {url}")
    
    async def _get_project_with_access(self, project_id: str, user_id: str) -> Project:
        """Get project and validate user access."""
        query = select(Project).where(Project.id == UUID(project_id))
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project with ID {project_id} not found")
        
        # TODO: Add proper project access validation
        # For now, assume user has access
        
        return project
    
    async def _get_repository_with_access(self, repository_id: str, user_id: str) -> Repository:
        """Get repository and validate user access."""
        query = select(Repository).options(
            selectinload(Repository.project)
        ).where(Repository.id == UUID(repository_id))
        
        result = await self.db.execute(query)
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise NotFoundError(f"Repository with ID {repository_id} not found")
        
        # TODO: Add proper project access validation through repository.project
        # For now, assume user has access
        
        return repository