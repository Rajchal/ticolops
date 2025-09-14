"""API endpoints for activity tracking and presence management."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.activity import ActivityService, PresenceService
from app.schemas.activity import (
    Activity, ActivityCreate, ActivityUpdate, ActivityFilter, ActivityStats,
    UserPresence, UserPresenceCreate, UserPresenceUpdate, PresenceFilter,
    CollaborationOpportunity, ConflictDetection, ActivityBatch
)
from app.core.exceptions import NotFoundError, ValidationError

router = APIRouter()


@router.post("/activities", response_model=Activity, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_data: ActivityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new activity."""
    try:
        activity_service = ActivityService(db)
        return await activity_service.create_activity(str(current_user.id), activity_data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/activities", response_model=List[Activity])
async def get_activities(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    activity_types: Optional[str] = Query(None),  # Comma-separated list
    location: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activities based on filters."""
    try:
        # Parse activity types if provided
        parsed_activity_types = None
        if activity_types:
            from app.schemas.activity import ActivityType
            type_list = activity_types.split(",")
            parsed_activity_types = [ActivityType(t.strip()) for t in type_list if t.strip()]

        # Parse dates if provided
        from datetime import datetime
        parsed_start_date = None
        parsed_end_date = None
        if start_date:
            parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            parsed_end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        # Parse priority if provided
        parsed_priority = None
        if priority:
            from app.schemas.activity import ActivityPriority
            parsed_priority = ActivityPriority(priority)

        # Create filter
        filters = ActivityFilter(
            user_id=user_id,
            project_id=project_id,
            activity_types=parsed_activity_types,
            location=location,
            priority=parsed_priority,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset
        )

        activity_service = ActivityService(db)
        return await activity_service.get_activities(filters)
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/activities/{activity_id}", response_model=Activity)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing activity."""
    try:
        activity_service = ActivityService(db)
        return await activity_service.update_activity(activity_id, str(current_user.id), activity_data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/activities/{activity_id}/end", response_model=Activity)
async def end_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """End an ongoing activity."""
    try:
        activity_service = ActivityService(db)
        return await activity_service.end_activity(activity_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/activities/batch", response_model=List[Activity], status_code=status.HTTP_201_CREATED)
async def create_batch_activities(
    batch_data: ActivityBatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple activities in a batch."""
    try:
        activity_service = ActivityService(db)
        return await activity_service.create_batch_activities(str(current_user.id), batch_data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/activities/stats", response_model=ActivityStats)
async def get_activity_stats(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity statistics."""
    try:
        # Users can only view their own stats unless they're admin
        if user_id and user_id != str(current_user.id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        activity_service = ActivityService(db)
        return await activity_service.get_activity_stats(user_id, project_id, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Presence Management Endpoints

@router.post("/presence", response_model=UserPresence, status_code=status.HTTP_201_CREATED)
async def update_presence(
    presence_data: UserPresenceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user presence."""
    try:
        presence_service = PresenceService(db)
        return await presence_service.update_presence(str(current_user.id), presence_data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/project/{project_id}", response_model=List[UserPresence])
async def get_project_presence(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user presence for a project."""
    try:
        # TODO: Add project access validation
        presence_service = PresenceService(db)
        return await presence_service.get_project_presence(project_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/online", response_model=List[UserPresence])
async def get_online_users(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get currently online users."""
    try:
        presence_service = PresenceService(db)
        return await presence_service.get_online_users(project_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/collaboration/opportunities/{project_id}", response_model=List[CollaborationOpportunity])
async def get_collaboration_opportunities(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get collaboration opportunities for current user in a project."""
    try:
        # TODO: Add project access validation
        presence_service = PresenceService(db)
        return await presence_service.detect_collaboration_opportunities(str(current_user.id), project_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/collaboration/conflicts/{project_id}", response_model=List[ConflictDetection])
async def get_project_conflicts(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get potential conflicts in a project."""
    try:
        # TODO: Add project access validation
        presence_service = PresenceService(db)
        return await presence_service.detect_conflicts(project_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/presence/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_stale_presence(
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up stale presence records (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        presence_service = PresenceService(db)
        cleaned_count = await presence_service.cleanup_stale_presence(hours)
        
        return {
            "message": f"Cleaned up {cleaned_count} stale presence records",
            "cleaned_count": cleaned_count,
            "hours_threshold": hours
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health/activity-system", status_code=status.HTTP_200_OK)
async def activity_system_health_check(
    db: AsyncSession = Depends(get_db)
):
    """Check the health of the activity tracking system."""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, select
        from app.models.activity import Activity, UserPresence

        # Check recent activity
        recent_time = datetime.utcnow() - timedelta(hours=24)
        
        # Count recent activities
        activity_count_query = select(func.count(Activity.id)).where(Activity.created_at >= recent_time)
        activity_result = await db.execute(activity_count_query)
        recent_activities = activity_result.scalar()

        # Count online users
        online_cutoff = datetime.utcnow() - timedelta(minutes=5)
        online_count_query = select(func.count(UserPresence.id)).where(
            UserPresence.last_activity >= online_cutoff
        )
        online_result = await db.execute(online_count_query)
        online_users = online_result.scalar()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "recent_activities_24h": recent_activities,
                "currently_online_users": online_users,
                "database_connection": "ok"
            },
            "features": {
                "activity_tracking": "operational",
                "presence_management": "operational",
                "collaboration_detection": "operational",
                "conflict_detection": "operational"
            }
        }
    
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }