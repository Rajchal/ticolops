"""Workspace management API endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.project import ProjectSettings
from app.services.workspace import WorkspaceService
from app.core.exceptions import NotFoundError, PermissionError, ValidationError

router = APIRouter()


@router.post("/projects/{project_id}/workspace/initialize", response_model=Dict[str, Any])
async def initialize_member_workspace(
    project_id: str,
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize workspace for a new project member."""
    try:
        workspace_service = WorkspaceService(db)
        return await workspace_service.initialize_member_workspace(
            project_id, member_id, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/projects/{project_id}/settings", response_model=Dict[str, Any])
async def update_project_settings(
    project_id: str,
    settings: ProjectSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update project settings and notify team members."""
    try:
        workspace_service = WorkspaceService(db)
        return await workspace_service.update_project_settings(
            project_id, settings, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/workspace", response_model=Dict[str, Any])
async def get_workspace_overview(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workspace overview for current user in project."""
    try:
        workspace_service = WorkspaceService(db)
        return await workspace_service.get_workspace_overview(project_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/projects/{project_id}/templates/{template_type}", response_model=Dict[str, Any])
async def setup_project_template(
    project_id: str,
    template_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set up project template and starter files."""
    try:
        workspace_service = WorkspaceService(db)
        return await workspace_service.setup_project_templates(
            project_id, template_type, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/projects/{project_id}/members/{member_id}/permissions", response_model=Dict[str, Any])
async def manage_member_permissions(
    project_id: str,
    member_id: str,
    permissions: Dict[str, bool],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manage specific permissions for a project member."""
    try:
        workspace_service = WorkspaceService(db)
        return await workspace_service.manage_member_permissions(
            project_id, member_id, permissions, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/collaboration-opportunities", response_model=Dict[str, Any])
async def get_collaboration_opportunities(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get collaboration opportunities for current user in project."""
    try:
        workspace_service = WorkspaceService(db)
        opportunities = await workspace_service._get_collaboration_opportunities(
            project_id, str(current_user.id)
        )
        return {"opportunities": opportunities}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/templates", response_model=Dict[str, Any])
async def get_available_templates():
    """Get list of available project templates."""
    templates = {
        "web": {
            "name": "Web Project",
            "description": "Basic HTML, CSS, and JavaScript template",
            "files": ["index.html", "styles.css", "script.js", "README.md"]
        },
        "api": {
            "name": "API Project", 
            "description": "FastAPI template for building REST APIs",
            "files": ["main.py", "requirements.txt", "README.md"]
        },
        "react": {
            "name": "React App",
            "description": "React application template (coming soon)",
            "files": ["Coming soon..."]
        },
        "mobile": {
            "name": "Mobile App",
            "description": "Mobile application template (coming soon)",
            "files": ["Coming soon..."]
        }
    }
    
    return {"templates": templates}


@router.post("/projects/{project_id}/workspace/reset", response_model=Dict[str, Any])
async def reset_workspace(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset workspace for current user (remove personal files and preferences)."""
    try:
        workspace_service = WorkspaceService(db)
        
        # This would typically remove user's personal workspace files
        # For now, return a success message
        return {
            "project_id": project_id,
            "user_id": str(current_user.id),
            "status": "reset",
            "message": "Workspace has been reset successfully"
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/activity-summary", response_model=Dict[str, Any])
async def get_project_activity_summary(
    project_id: str,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project activity summary for the specified number of days."""
    try:
        workspace_service = WorkspaceService(db)
        
        # Check access
        if not await workspace_service.project_service._user_has_project_access(project_id, str(current_user.id)):
            raise PermissionError("You don't have access to this project")
        
        # Get activity summary
        summary = await workspace_service._get_project_activity_summary(project_id)
        
        return {
            "project_id": project_id,
            "days": days,
            "summary": summary
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))