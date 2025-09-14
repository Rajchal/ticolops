"""API endpoints for repository management and Git provider integration."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.repository import RepositoryService
from app.schemas.repository import (
    Repository, RepositoryConnectionRequest, RepositoryValidationRequest,
    RepositoryConfigUpdate, RepositoryInfo, RepositoryValidationResult,
    GitCommit, UserRepository, RepositoryStats, GitProvider
)
from app.core.exceptions import NotFoundError, ValidationError, ExternalServiceError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/projects/{project_id}/repositories", response_model=Repository, status_code=status.HTTP_201_CREATED)
async def connect_repository(
    project_id: str,
    connection_request: RepositoryConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect a Git repository to a project."""
    try:
        repository_service = RepositoryService(db)
        
        repository = await repository_service.connect_repository(
            project_id=project_id,
            user_id=str(current_user.id),
            provider=connection_request.provider,
            repository_url=connection_request.repository_url,
            access_token=connection_request.access_token,
            branch=connection_request.branch,
            deployment_config=connection_request.deployment_config
        )
        
        return repository
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ExternalServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/repositories/{repository_id}")
async def disconnect_repository(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect a repository from its project."""
    try:
        repository_service = RepositoryService(db)
        
        success = await repository_service.disconnect_repository(repository_id, str(current_user.id))
        
        return {
            "success": success,
            "message": "Repository disconnected successfully" if success else "Failed to disconnect repository"
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/repositories", response_model=List[Repository])
async def get_project_repositories(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all repositories connected to a project."""
    try:
        repository_service = RepositoryService(db)
        
        repositories = await repository_service.get_project_repositories(project_id, str(current_user.id))
        
        return repositories
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/repositories/{repository_id}", response_model=RepositoryInfo)
async def get_repository_info(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a repository."""
    try:
        repository_service = RepositoryService(db)
        
        repository_info = await repository_service.get_repository_info(repository_id, str(current_user.id))
        
        return repository_info
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/repositories/{repository_id}/config", response_model=Repository)
async def update_repository_config(
    repository_id: str,
    config_update: RepositoryConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update repository deployment configuration."""
    try:
        repository_service = RepositoryService(db)
        
        # Convert Pydantic model to dict, excluding None values
        config_updates = config_update.dict(exclude_none=True)
        
        repository = await repository_service.update_repository_config(
            repository_id, str(current_user.id), config_updates
        )
        
        return repository
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/repositories/validate", response_model=RepositoryValidationResult)
async def validate_repository_access(
    validation_request: RepositoryValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate access to a repository using provided credentials."""
    try:
        repository_service = RepositoryService(db)
        
        validation_result = await repository_service.validate_repository_access(
            provider=validation_request.provider,
            repository_url=validation_request.repository_url,
            access_token=validation_request.access_token
        )
        
        return validation_result
    
    except Exception as e:
        # Return validation failure instead of raising exception
        return RepositoryValidationResult(
            valid=False,
            error=f"Validation failed: {str(e)}",
            error_type="validation_error"
        )


@router.get("/repositories/{repository_id}/commits", response_model=List[GitCommit])
async def get_repository_commits(
    repository_id: str,
    access_token: str = Query(..., description="Git provider access token"),
    branch: Optional[str] = Query(None, description="Branch to get commits from"),
    limit: int = Query(10, ge=1, le=50, description="Number of commits to retrieve"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent commits from a repository."""
    try:
        repository_service = RepositoryService(db)
        
        commits = await repository_service.get_repository_commits(
            repository_id=repository_id,
            user_id=str(current_user.id),
            access_token=access_token,
            branch=branch,
            limit=limit
        )
        
        return commits
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ExternalServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/git-providers/{provider}/repositories", response_model=List[UserRepository])
async def get_user_repositories(
    provider: GitProvider,
    access_token: str = Query(..., description="Git provider access token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's repositories from a Git provider."""
    try:
        repository_service = RepositoryService(db)
        
        repositories = await repository_service.get_user_repositories(
            provider=provider,
            access_token=access_token
        )
        
        return repositories
    
    except ExternalServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/repositories/stats", response_model=RepositoryStats)
async def get_repository_stats(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get repository statistics."""
    try:
        # This would typically query the database for statistics
        # For now, return mock data
        
        stats = RepositoryStats(
            total_repositories=5,
            repositories_by_provider={"github": 3, "gitlab": 2},
            active_repositories=4,
            repositories_with_webhooks=3,
            recent_connections=[
                {
                    "repository_name": "my-project",
                    "provider": "github",
                    "connected_at": "2024-01-15T10:00:00Z"
                }
            ]
        )
        
        return stats
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/repositories/{repository_id}/sync")
async def sync_repository(
    repository_id: str,
    access_token: str = Query(..., description="Git provider access token"),
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually sync repository data with Git provider."""
    try:
        # Add background task to sync repository
        background_tasks.add_task(
            _sync_repository_background,
            repository_id,
            str(current_user.id),
            access_token,
            db
        )
        
        return {
            "success": True,
            "message": "Repository sync initiated",
            "repository_id": repository_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/repositories/health")
async def repository_system_health():
    """Check the health of the repository management system."""
    try:
        # Check system health
        health_status = "healthy"
        issues = []
        
        # TODO: Add actual health checks
        # - Database connectivity
        # - Git provider API availability
        # - Webhook endpoint accessibility
        
        return {
            "status": health_status,
            "issues": issues,
            "features": {
                "github_integration": True,
                "gitlab_integration": True,
                "webhook_management": True,
                "repository_sync": True
            },
            "providers": {
                "github": {"status": "operational", "api_version": "v3"},
                "gitlab": {"status": "operational", "api_version": "v4"}
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "features": {
                "github_integration": False,
                "gitlab_integration": False,
                "webhook_management": False,
                "repository_sync": False
            }
        }


# Background tasks

async def _sync_repository_background(
    repository_id: str,
    user_id: str,
    access_token: str,
    db: AsyncSession
):
    """Background task to sync repository data."""
    try:
        repository_service = RepositoryService(db)
        
        # Get repository info
        repository_info = await repository_service.get_repository_info(repository_id, user_id)
        
        # Get recent commits
        commits = await repository_service.get_repository_commits(
            repository_id=repository_id,
            user_id=user_id,
            access_token=access_token,
            limit=20
        )
        
        # TODO: Store sync data in database
        # TODO: Update repository metadata
        # TODO: Trigger deployment if auto-deploy is enabled
        
        logger.info(f"Repository {repository_id} synced successfully")
        
    except Exception as e:
        logger.error(f"Failed to sync repository {repository_id}: {e}")


# Helper functions

def _parse_git_provider_from_url(url: str) -> Optional[GitProvider]:
    """Parse Git provider from repository URL."""
    url_lower = url.lower()
    
    if 'github.com' in url_lower:
        return GitProvider.GITHUB
    elif 'gitlab.com' in url_lower:
        return GitProvider.GITLAB
    elif 'bitbucket.org' in url_lower:
        return GitProvider.BITBUCKET
    
    return None


@router.post("/repositories/{repository_id}/webhook")
async def manage_repository_webhook(
    repository_id: str,
    webhook_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manage webhook for a repository (create or delete).
    
    Args:
        repository_id: Repository ID
        webhook_data: Webhook management data including action and access_token
        
    Returns:
        Webhook management result
    """
    try:
        repository_service = RepositoryService(db)
        
        action = webhook_data.get("action", "create")
        access_token = webhook_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="access_token is required")
        
        if action not in ["create", "delete"]:
            raise HTTPException(status_code=400, detail="action must be 'create' or 'delete'")
        
        result = await repository_service.manage_webhook(
            repository_id=repository_id,
            user_id=str(current_user.id),
            access_token=access_token,
            action=action
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error managing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/repositories/{repository_id}/webhook/status")
async def get_repository_webhook_status(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get webhook status for a repository.
    
    Args:
        repository_id: Repository ID
        
    Returns:
        Webhook status information
    """
    try:
        repository_service = RepositoryService(db)
        
        status = await repository_service.get_webhook_status(
            repository_id=repository_id,
            user_id=str(current_user.id)
        )
        
        return status
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error retrieving webhook status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")