"""API routes and endpoints."""

from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .activity import router as activity_router
from .websocket import router as websocket_router
from .presence import router as presence_router
from .collaboration import router as collaboration_router
from .repository import router as repository_router
# Temporarily commented out until project schemas are properly set up
# from .projects import router as projects_router
# from .project_files import router as project_files_router
# from .workspace import router as workspace_router

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(activity_router, prefix="", tags=["activity"])
api_router.include_router(websocket_router, prefix="", tags=["websocket"])
api_router.include_router(presence_router, prefix="", tags=["presence"])
api_router.include_router(collaboration_router, prefix="", tags=["collaboration"])
api_router.include_router(repository_router, prefix="", tags=["repository"])
# api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
# api_router.include_router(project_files_router, prefix="", tags=["project-files"])
# api_router.include_router(workspace_router, prefix="", tags=["workspace"])