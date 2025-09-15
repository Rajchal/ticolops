"""API routes and endpoints."""

from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .activity import router as activity_router
from .websocket import router as websocket_router
from .presence import router as presence_router
from .collaboration import router as collaboration_router
from .repository import router as repository_router
from .work_items import router as work_items_router
from .webhooks import router as webhooks_router
from .deployment import router as deployment_router
from .deployment_monitoring import router as deployment_monitoring_router
from .deployment_recovery import router as deployment_recovery_router
from .notifications import router as notifications_router
from .notification_triggers import router as notification_triggers_router
# Projects and workspace routers are required for the frontend to list and manage projects
from .projects import router as projects_router
from .project_files import router as project_files_router
from .workspace import router as workspace_router

api_router = APIRouter()

# Include routers (each router already declares its own prefix)
api_router.include_router(auth_router, tags=["authentication"])
api_router.include_router(users_router, tags=["users"])
api_router.include_router(activity_router, tags=["activity"])
api_router.include_router(websocket_router, tags=["websocket"])
api_router.include_router(presence_router, tags=["presence"])
api_router.include_router(collaboration_router, tags=["collaboration"])
api_router.include_router(repository_router, tags=["repository"])
api_router.include_router(work_items_router, tags=["work-items"])
api_router.include_router(webhooks_router, tags=["webhooks"])
api_router.include_router(deployment_router, tags=["deployment"])
api_router.include_router(deployment_monitoring_router, tags=["deployment-monitoring"])
api_router.include_router(deployment_recovery_router, tags=["deployment-recovery"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(notification_triggers_router, tags=["notification-triggers"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(project_files_router, prefix="", tags=["project-files"])
api_router.include_router(workspace_router, prefix="", tags=["workspace"])