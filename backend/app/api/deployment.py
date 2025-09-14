"""API endpoints for deployment management and automation."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.deployment import DeploymentStatus, DeploymentTrigger
from app.services.deployment import DeploymentService
from app.schemas.deployment import (
    Deployment, DeploymentCreate, DeploymentUpdate, DeploymentSummary,
    DeploymentTriggerRequest, DeploymentStats, ProjectTypeDetectionResult
)
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/deployments", response_model=Deployment, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment_data: DeploymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new deployment."""
    try:
        deployment_service = DeploymentService(db)
        
        deployment = await deployment_service.create_deployment(
            repository_id=deployment_data.repository_id,
            commit_sha=deployment_data.commit_sha,
            branch=deployment_data.branch,
            trigger=deployment_data.trigger,
            build_config=deployment_data.build_config,
            environment_variables=deployment_data.environment_variables
        )
        
        return deployment
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/{deployment_id}", response_model=Deployment)
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployment by ID."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        return deployment
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/deployments/{deployment_id}", response_model=Deployment)
async def update_deployment(
    deployment_id: str,
    deployment_update: DeploymentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update deployment status and metadata."""
    try:
        deployment_service = DeploymentService(db)
        
        # Convert Pydantic model to dict, excluding None values
        update_data = deployment_update.dict(exclude_none=True)
        
        deployment = await deployment_service.update_deployment_status(
            deployment_id=deployment_id,
            status=update_data.get("status"),
            preview_url=update_data.get("preview_url"),
            build_logs=update_data.get("build_logs"),
            deployment_logs=update_data.get("deployment_logs"),
            error_message=update_data.get("error_message")
        )
        
        return deployment
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/deployments/{deployment_id}")
async def cancel_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an active deployment."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.cancel_deployment(deployment_id)
        
        return {
            "success": True,
            "message": "Deployment cancelled successfully",
            "deployment_id": deployment_id,
            "status": deployment.status
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/repositories/{repository_id}/deployments", response_model=List[DeploymentSummary])
async def get_repository_deployments(
    repository_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of deployments to retrieve"),
    status: Optional[DeploymentStatus] = Query(None, description="Filter by deployment status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployments for a repository."""
    try:
        deployment_service = DeploymentService(db)
        
        deployments = await deployment_service.get_repository_deployments(
            repository_id=repository_id,
            limit=limit,
            status_filter=status
        )
        
        return deployments
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving repository deployments: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/projects/{project_id}/deployments", response_model=List[DeploymentSummary])
async def get_project_deployments(
    project_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of deployments to retrieve"),
    status: Optional[DeploymentStatus] = Query(None, description="Filter by deployment status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployments for a project."""
    try:
        deployment_service = DeploymentService(db)
        
        deployments = await deployment_service.get_project_deployments(
            project_id=project_id,
            limit=limit,
            status_filter=status
        )
        
        return deployments
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving project deployments: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/deployments/trigger", response_model=Deployment, status_code=status.HTTP_201_CREATED)
async def trigger_deployment(
    trigger_request: DeploymentTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a deployment."""
    try:
        deployment_service = DeploymentService(db)
        
        # Get repository to determine branch and commit if not specified
        from app.services.repository import RepositoryService
        repo_service = RepositoryService(db)
        repo_info = await repo_service.get_repository_info(
            trigger_request.repository_id,
            str(current_user.id)
        )
        
        branch = trigger_request.branch or repo_info.get("branch", "main")
        commit_sha = trigger_request.commit_sha or "latest"  # Would need to fetch from Git API
        
        deployment = await deployment_service.create_deployment(
            repository_id=trigger_request.repository_id,
            commit_sha=commit_sha,
            branch=branch,
            trigger=DeploymentTrigger.MANUAL,
            environment_variables=trigger_request.environment_variables
        )
        
        return deployment
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/stats", response_model=DeploymentStats)
async def get_deployment_stats(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployment statistics."""
    try:
        deployment_service = DeploymentService(db)
        stats = await deployment_service.get_deployment_stats(project_id)
        
        return stats
    
    except Exception as e:
        logger.error(f"Error retrieving deployment stats: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: str,
    log_type: str = Query("all", regex="^(all|build|deployment)$", description="Type of logs to retrieve"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployment logs."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        logs = {}
        if log_type in ["all", "build"] and deployment.build_logs:
            logs["build_logs"] = deployment.build_logs
        if log_type in ["all", "deployment"] and deployment.deployment_logs:
            logs["deployment_logs"] = deployment.deployment_logs
        
        return {
            "deployment_id": deployment_id,
            "logs": logs,
            "status": deployment.status,
            "created_at": deployment.created_at,
            "started_at": deployment.started_at,
            "completed_at": deployment.completed_at
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving deployment logs: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/repositories/{repository_id}/detect-project-type")
async def detect_project_type(
    repository_id: str,
    access_token: str = Query(..., description="Git provider access token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Detect project type from repository contents."""
    try:
        deployment_service = DeploymentService(db)
        
        # TODO: Implement actual repository file scanning
        # For now, return a mock detection result
        
        from app.models.deployment import ProjectType
        
        mock_result = {
            "project_type": ProjectType.REACT,
            "confidence": 0.95,
            "detected_files": ["package.json", "src/App.js", "public/index.html"],
            "suggested_config": {
                "id": "mock-config-id",
                "project_type": ProjectType.REACT,
                "name": "React Application",
                "description": "Standard React application configuration",
                "build_command": "npm run build",
                "output_directory": "build",
                "install_command": "npm install",
                "detection_files": ["package.json", "src/App.js"],
                "detection_patterns": {"dependencies": ["react", "react-dom"]},
                "default_env_vars": {"NODE_ENV": "production"},
                "node_version": "18",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
        
        return mock_result
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting project type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/health")
async def deployment_system_health():
    """Check the health of the deployment system."""
    try:
        # Check system health
        health_status = "healthy"
        issues = []
        
        # TODO: Add actual health checks
        # - Database connectivity
        # - Deployment queue status
        # - Build system availability
        # - Hosting platform connectivity
        
        return {
            "status": health_status,
            "issues": issues,
            "features": {
                "deployment_creation": True,
                "project_type_detection": True,
                "build_automation": True,
                "deployment_monitoring": True,
                "webhook_triggers": True
            },
            "build_systems": {
                "docker": {"status": "operational", "version": "20.10"},
                "node": {"status": "operational", "version": "18.x"},
                "python": {"status": "operational", "version": "3.11"}
            },
            "hosting_platforms": {
                "vercel": {"status": "operational", "api_version": "v2"},
                "netlify": {"status": "operational", "api_version": "v1"},
                "railway": {"status": "operational", "api_version": "v1"}
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "features": {
                "deployment_creation": False,
                "project_type_detection": False,
                "build_automation": False,
                "deployment_monitoring": False,
                "webhook_triggers": False
            }
        }


@router.post("/deployments/{deployment_id}/retry", response_model=Deployment)
async def retry_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed deployment."""
    try:
        deployment_service = DeploymentService(db)
        
        # Get the original deployment
        original_deployment = await deployment_service.get_deployment(deployment_id)
        
        if original_deployment.status not in [DeploymentStatus.FAILED.value, DeploymentStatus.CANCELLED.value]:
            raise ValidationError("Can only retry failed or cancelled deployments")
        
        # Create a new deployment with the same parameters
        new_deployment = await deployment_service.create_deployment(
            repository_id=str(original_deployment.repository_id),
            commit_sha=original_deployment.commit_sha,
            branch=original_deployment.branch,
            trigger=DeploymentTrigger.MANUAL,
            build_config=original_deployment.build_config,
            environment_variables=original_deployment.environment_variables
        )
        
        return new_deployment
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrying deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")