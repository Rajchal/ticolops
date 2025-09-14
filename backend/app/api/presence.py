"""API endpoints for presence management and status tracking."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.presence_manager import (
    presence_manager, register_user_online, register_user_offline,
    update_user_activity, get_project_online_users, get_user_status
)
from app.schemas.activity import UserPresenceStatus

router = APIRouter()


@router.post("/presence/online", status_code=status.HTTP_201_CREATED)
async def set_user_online(
    session_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set user as online and register presence session."""
    try:
        session_id = session_data.get("session_id", f"web_{current_user.id}")
        project_id = session_data.get("project_id")
        metadata = session_data.get("metadata", {})
        
        # Add user info to metadata
        metadata.update({
            "user_name": current_user.name,
            "user_email": current_user.email,
            "user_role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
            "connection_type": "api"
        })
        
        session_info = await register_user_online(
            user_id=str(current_user.id),
            session_id=session_id,
            project_id=project_id,
            metadata=metadata
        )
        
        return {
            "success": True,
            "message": "User set to online",
            "session": session_info
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/presence/offline")
async def set_user_offline(
    current_user: User = Depends(get_current_user)
):
    """Set user as offline and unregister presence session."""
    try:
        await register_user_offline(str(current_user.id))
        
        return {
            "success": True,
            "message": "User set to offline"
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/presence/heartbeat")
async def send_heartbeat(
    activity_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """Send heartbeat to maintain active status."""
    try:
        if activity_data is None:
            activity_data = {}
        
        await update_user_activity(
            user_id=str(current_user.id),
            location=activity_data.get("location"),
            activity_type=activity_data.get("activity_type"),
            metadata=activity_data.get("metadata")
        )
        
        return {
            "success": True,
            "message": "Heartbeat received",
            "timestamp": presence_manager.user_heartbeats.get(str(current_user.id))
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/presence/status")
async def update_presence_status(
    status_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user presence status and information."""
    try:
        # Validate status if provided
        if "status" in status_data:
            try:
                UserPresenceStatus(status_data["status"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Invalid status: {status_data['status']}"
                )
        
        updated_session = await presence_manager.update_user_presence(
            str(current_user.id), 
            status_data
        )
        
        if not updated_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User session not found. Please set user online first."
            )
        
        return {
            "success": True,
            "message": "Presence status updated",
            "session": updated_session
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/me")
async def get_my_presence(
    current_user: User = Depends(get_current_user)
):
    """Get current user's presence information."""
    try:
        presence_data = await get_user_status(str(current_user.id))
        
        if not presence_data:
            return {
                "user_id": str(current_user.id),
                "status": "offline",
                "message": "No active session found"
            }
        
        return {
            "user_id": str(current_user.id),
            "presence": presence_data
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/user/{user_id}")
async def get_user_presence(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific user's presence information."""
    try:
        # Users can only view their own presence unless they're admin
        if user_id != str(current_user.id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        presence_data = await get_user_status(user_id)
        
        if not presence_data:
            return {
                "user_id": user_id,
                "status": "offline",
                "message": "No active session found"
            }
        
        return {
            "user_id": user_id,
            "presence": presence_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/project/{project_id}")
async def get_project_presence(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get presence information for all users in a project."""
    try:
        # TODO: Add project access validation
        # project_service = ProjectService(db)
        # if not await project_service._user_has_project_access(project_id, str(current_user.id)):
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
        
        project_presence = await presence_manager.get_project_presence(project_id)
        online_users = await get_project_online_users(project_id)
        
        return {
            "project_id": project_id,
            "total_users": len(project_presence),
            "online_users": len(online_users),
            "presence_data": project_presence,
            "online_users_list": online_users
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/online")
async def get_online_users(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get all currently online users, optionally filtered by project."""
    try:
        online_users = await presence_manager.get_online_users(project_id)
        
        return {
            "project_id": project_id,
            "online_count": len(online_users),
            "online_users": online_users
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/activity-summary/{user_id}")
async def get_user_activity_summary(
    user_id: str,
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user)
):
    """Get user activity summary."""
    try:
        # Users can only view their own summary unless they're admin
        if user_id != str(current_user.id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        summary = await presence_manager.get_user_activity_summary(user_id, hours)
        
        return {
            "user_id": user_id,
            "hours_analyzed": hours,
            "summary": summary
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/stats")
async def get_presence_stats(
    current_user: User = Depends(get_current_user)
):
    """Get presence system statistics (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
        stats = presence_manager.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/presence/configure")
async def configure_presence_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Configure presence detection settings (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
        # Update settings
        if "idle_threshold_minutes" in settings:
            idle_threshold = settings["idle_threshold_minutes"]
            if not isinstance(idle_threshold, int) or idle_threshold < 1 or idle_threshold > 60:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="idle_threshold_minutes must be between 1 and 60"
                )
            presence_manager.idle_threshold_minutes = idle_threshold
        
        if "offline_threshold_minutes" in settings:
            offline_threshold = settings["offline_threshold_minutes"]
            if not isinstance(offline_threshold, int) or offline_threshold < 5 or offline_threshold > 120:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="offline_threshold_minutes must be between 5 and 120"
                )
            presence_manager.offline_threshold_minutes = offline_threshold
        
        return {
            "success": True,
            "message": "Presence settings updated",
            "settings": {
                "idle_threshold_minutes": presence_manager.idle_threshold_minutes,
                "offline_threshold_minutes": presence_manager.offline_threshold_minutes
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/presence/bulk-update")
async def bulk_update_presence(
    updates: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
):
    """Bulk update presence for multiple users (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
        results = []
        
        for update in updates:
            user_id = update.get("user_id")
            status_data = update.get("status_data", {})
            
            if not user_id:
                results.append({"user_id": None, "success": False, "error": "Missing user_id"})
                continue
            
            try:
                updated_session = await presence_manager.update_user_presence(user_id, status_data)
                results.append({
                    "user_id": user_id,
                    "success": True,
                    "session": updated_session
                })
            except Exception as e:
                results.append({
                    "user_id": user_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Processed {len(updates)} presence updates",
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/presence/cleanup")
async def cleanup_stale_presence(
    force: bool = Query(False),
    current_user: User = Depends(get_current_user)
):
    """Clean up stale presence data (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
        # Get current stats before cleanup
        before_stats = presence_manager.get_stats()
        
        # Force cleanup if requested
        if force:
            await presence_manager._cleanup_offline_users()
        
        # Get stats after cleanup
        after_stats = presence_manager.get_stats()
        
        cleaned_count = before_stats["total_active_sessions"] - after_stats["total_active_sessions"]
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} stale presence records",
            "before_stats": before_stats,
            "after_stats": after_stats,
            "cleaned_count": cleaned_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/presence/health")
async def presence_health_check():
    """Check the health of the presence management system."""
    try:
        stats = presence_manager.get_stats()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if not stats["is_running"]:
            health_status = "degraded"
            issues.append("Presence manager background tasks not running")
        
        if stats["total_active_sessions"] == 0:
            issues.append("No active user sessions")
        
        return {
            "status": health_status,
            "issues": issues,
            "stats": stats,
            "features": {
                "heartbeat_monitoring": stats["is_running"],
                "idle_detection": stats["is_running"],
                "status_broadcasting": stats["is_running"],
                "session_management": True
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "features": {
                "heartbeat_monitoring": False,
                "idle_detection": False,
                "status_broadcasting": False,
                "session_management": False
            }
        }