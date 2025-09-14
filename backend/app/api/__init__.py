"""API routes and endpoints."""

from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .activity import router as activity_router
from .websocket import router as websocket_router
from .presence import router as presence_router
from .collaboration import router as collaboration_router
from .repository import router as repository_router
from .webhooks import router as webhooks_router
from .deployment import router as deployment_router
from .deployment_monitoring import router as deployment_monitoring_router
from .deployment_recovery import router as deployment_recovery_router
from .notifications import router as notifications_router
from .notification_triggers import router as notification_triggers_router
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
api_router.include_router(webhooks_router, prefix="", tags=["webhooks"])
api_router.include_router(deployment_router, prefix="", tags=["deployment"])
api_router.include_router(deployment_monitoring_router, prefix="", tags=["deployment-monitoring"])
api_router.include_router(deployment_recovery_router, prefix="", tags=["deployment-recovery"])
api_router.include_router(notifications_router, prefix="", tags=["notifications"])
api_router.include_router(notification_triggers_router, prefix="", tags=["notification-triggers"])
# api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
# api_router.include_router(project_files_router, prefix="", tags=["project-files"])
# api_router.include_router(workspace_router, prefix="", tags=["workspace"])