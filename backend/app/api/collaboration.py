"""API endpoints for conflict detection and collaboration features."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.conflict_detector import (
    conflict_detector, detect_project_conflicts, find_collaboration_opportunities
)
from app.schemas.activity import CollaborationOpportunity, ConflictDetection

router = APIRouter()


@router.get("/projects/{project_id}/conflicts", response_model=List[ConflictDetection])
async def get_project_conflicts(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current conflicts in a project."""
    try:
        # TODO: Add project access validation
        # project_service = ProjectService(db)
        # if not await project_service._user_has_project_access(project_id, str(current_user.id)):
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")
        
        conflicts = await detect_project_conflicts(project_id)
        
        return conflicts
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/collaboration-opportunities", response_model=List[CollaborationOpportunity])
async def get_collaboration_opportunities(
    project_id: str,
    user_id: Optional[str] = Query(None, description="Filter opportunities for specific user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get collaboration opportunities in a project."""
    try:
        # TODO: Add project access validation
        
        # If user_id not specified, use current user
        target_user_id = user_id or str(current_user.id)
        
        # Users can only get their own opportunities unless they're admin
        if target_user_id != str(current_user.id) and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        opportunities = await find_collaboration_opportunities(project_id, target_user_id)
        
        return opportunities
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/conflicts/{conflict_id}/analyze")
async def analyze_conflict(
    conflict_id: str,
    conflict_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Analyze conflict severity and impact."""
    try:
        # Convert dict to ConflictDetection object for analysis
        conflict = ConflictDetection(**conflict_data)
        
        analysis = await conflict_detector.analyze_conflict_severity(conflict)
        
        return {
            "conflict_id": conflict_id,
            "analysis": analysis,
            "analyzed_by": str(current_user.id),
            "analyzed_at": "2024-01-15T10:00:00Z"
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/conflicts/{conflict_id}/resolve")
async def get_conflict_resolution_suggestions(
    conflict_id: str,
    conflict_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Get resolution suggestions for a conflict."""
    try:
        # Convert dict to ConflictDetection object
        conflict = ConflictDetection(**conflict_data)
        
        suggestions = await conflict_detector.suggest_conflict_resolution(conflict)
        
        return {
            "conflict_id": conflict_id,
            "resolution_suggestions": suggestions,
            "suggested_by": str(current_user.id),
            "suggested_at": "2024-01-15T10:00:00Z"
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/conflict-history")
async def get_conflict_history(
    project_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conflict history for a project."""
    try:
        # TODO: Add project access validation
        
        history = await conflict_detector.get_conflict_history(project_id, days)
        
        return {
            "project_id": project_id,
            "analysis_period_days": days,
            "history": history,
            "generated_at": "2024-01-15T10:00:00Z"
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/projects/{project_id}/collaboration-session")
async def create_collaboration_session(
    project_id: str,
    session_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a collaboration session based on opportunities."""
    try:
        # TODO: Add project access validation
        
        session_id = f"collab_{project_id}_{current_user.id}"
        
        # Extract session details
        participants = session_data.get("participants", [str(current_user.id)])
        session_type = session_data.get("type", "general")
        focus_area = session_data.get("focus_area", "project_wide")
        duration_minutes = session_data.get("duration_minutes", 60)
        
        # Create collaboration session
        session = {
            "session_id": session_id,
            "project_id": project_id,
            "created_by": str(current_user.id),
            "participants": participants,
            "type": session_type,
            "focus_area": focus_area,
            "duration_minutes": duration_minutes,
            "status": "active",
            "created_at": "2024-01-15T10:00:00Z",
            "metadata": session_data.get("metadata", {})
        }
        
        # TODO: Store session in database
        # TODO: Notify participants via WebSocket
        
        # Schedule session cleanup
        background_tasks.add_task(
            _cleanup_collaboration_session, 
            session_id, 
            duration_minutes
        )
        
        return {
            "success": True,
            "message": "Collaboration session created",
            "session": session
        }
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/collaboration-insights")
async def get_collaboration_insights(
    project_id: str,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get collaboration insights and analytics for a project."""
    try:
        # TODO: Add project access validation
        
        # Get recent conflicts and opportunities
        conflicts = await detect_project_conflicts(project_id)
        opportunities = await find_collaboration_opportunities(project_id)
        
        # Calculate insights
        insights = {
            "project_id": project_id,
            "analysis_period_days": days,
            "current_status": {
                "active_conflicts": len(conflicts),
                "collaboration_opportunities": len(opportunities),
                "conflict_severity_distribution": _analyze_conflict_severity(conflicts),
                "opportunity_type_distribution": _analyze_opportunity_types(opportunities)
            },
            "recommendations": _generate_collaboration_recommendations(conflicts, opportunities),
            "trends": {
                "conflict_trend": "stable",  # Would be calculated from historical data
                "collaboration_trend": "increasing",
                "team_engagement": "high"
            },
            "metrics": {
                "average_resolution_time": "45 minutes",
                "collaboration_success_rate": "85%",
                "conflict_prevention_rate": "70%"
            }
        }
        
        return insights
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/smart-suggestions")
async def get_smart_collaboration_suggestions(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-powered collaboration suggestions based on current context."""
    try:
        project_id = request_data.get("project_id")
        current_activity = request_data.get("current_activity", {})
        preferences = request_data.get("preferences", {})
        
        if not project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id required")
        
        # Get current context
        conflicts = await detect_project_conflicts(project_id)
        opportunities = await find_collaboration_opportunities(project_id, str(current_user.id))
        
        # Generate smart suggestions
        suggestions = {
            "immediate_actions": [],
            "collaboration_matches": [],
            "conflict_alerts": [],
            "learning_opportunities": [],
            "productivity_tips": []
        }
        
        # Analyze conflicts for immediate actions
        for conflict in conflicts:
            if str(current_user.id) in conflict.users:
                suggestions["immediate_actions"].append({
                    "type": "conflict_resolution",
                    "priority": "high",
                    "description": f"Resolve conflict in {conflict.location}",
                    "action": "coordinate_with_team",
                    "estimated_time": "15 minutes"
                })
        
        # Analyze opportunities for collaboration matches
        for opportunity in opportunities:
            if str(current_user.id) in opportunity.users:
                other_users = [uid for uid in opportunity.users if uid != str(current_user.id)]
                suggestions["collaboration_matches"].append({
                    "type": opportunity.type,
                    "priority": opportunity.priority.value,
                    "description": opportunity.description,
                    "potential_partners": other_users,
                    "estimated_benefit": "high"
                })
        
        # Add learning opportunities
        if current_activity.get("activity_type") == "debugging":
            suggestions["learning_opportunities"].append({
                "type": "knowledge_sharing",
                "description": "Consider asking for help from experienced team members",
                "action": "request_assistance",
                "potential_helpers": []  # Would be populated based on expertise analysis
            })
        
        # Add productivity tips
        if len(conflicts) > 2:
            suggestions["productivity_tips"].append({
                "tip": "High conflict activity detected",
                "recommendation": "Consider scheduling a team sync meeting",
                "impact": "medium"
            })
        
        return {
            "user_id": str(current_user.id),
            "project_id": project_id,
            "suggestions": suggestions,
            "context": {
                "active_conflicts": len(conflicts),
                "available_opportunities": len(opportunities),
                "current_activity": current_activity
            },
            "generated_at": "2024-01-15T10:00:00Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/collaboration/stats")
async def get_collaboration_system_stats(
    current_user: User = Depends(get_current_user)
):
    """Get collaboration system statistics (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
        stats = conflict_detector.get_stats()
        
        return {
            "success": True,
            "stats": stats,
            "system_health": "operational" if stats["is_running"] else "degraded"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/collaboration/configure")
async def configure_collaboration_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Configure collaboration detection settings (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
        # Update settings
        if "conflict_detection_window_minutes" in settings:
            window = settings["conflict_detection_window_minutes"]
            if not isinstance(window, int) or window < 5 or window > 120:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="conflict_detection_window_minutes must be between 5 and 120"
                )
            conflict_detector.conflict_detection_window_minutes = window
        
        if "collaboration_window_minutes" in settings:
            window = settings["collaboration_window_minutes"]
            if not isinstance(window, int) or window < 30 or window > 480:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="collaboration_window_minutes must be between 30 and 480"
                )
            conflict_detector.collaboration_window_minutes = window
        
        if "file_proximity_threshold" in settings:
            threshold = settings["file_proximity_threshold"]
            if not isinstance(threshold, int) or threshold < 1 or threshold > 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="file_proximity_threshold must be between 1 and 10"
                )
            conflict_detector.file_proximity_threshold = threshold
        
        return {
            "success": True,
            "message": "Collaboration settings updated",
            "settings": {
                "conflict_detection_window_minutes": conflict_detector.conflict_detection_window_minutes,
                "collaboration_window_minutes": conflict_detector.collaboration_window_minutes,
                "file_proximity_threshold": conflict_detector.file_proximity_threshold
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/collaboration/health")
async def collaboration_health_check():
    """Check the health of the collaboration system."""
    try:
        stats = conflict_detector.get_stats()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if not stats["is_running"]:
            health_status = "degraded"
            issues.append("Conflict detector not running")
        
        if stats["total_recent_conflicts"] > 10:
            issues.append(f"High conflict count: {stats['total_recent_conflicts']}")
        
        return {
            "status": health_status,
            "issues": issues,
            "stats": stats,
            "features": {
                "conflict_detection": stats["is_running"],
                "collaboration_opportunities": stats["is_running"],
                "smart_suggestions": True,
                "resolution_recommendations": True
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "features": {
                "conflict_detection": False,
                "collaboration_opportunities": False,
                "smart_suggestions": False,
                "resolution_recommendations": False
            }
        }


# Helper functions

async def _cleanup_collaboration_session(session_id: str, duration_minutes: int):
    """Background task to cleanup collaboration session after duration."""
    import asyncio
    await asyncio.sleep(duration_minutes * 60)
    
    # TODO: Mark session as completed in database
    # TODO: Send session summary to participants
    
    logger.info(f"Collaboration session {session_id} completed after {duration_minutes} minutes")


def _analyze_conflict_severity(conflicts: List[ConflictDetection]) -> Dict[str, int]:
    """Analyze conflict severity distribution."""
    severity_counts = {}
    for conflict in conflicts:
        severity = conflict.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return severity_counts


def _analyze_opportunity_types(opportunities: List[CollaborationOpportunity]) -> Dict[str, int]:
    """Analyze collaboration opportunity type distribution."""
    type_counts = {}
    for opportunity in opportunities:
        opp_type = opportunity.type
        type_counts[opp_type] = type_counts.get(opp_type, 0) + 1
    return type_counts


def _generate_collaboration_recommendations(
    conflicts: List[ConflictDetection], 
    opportunities: List[CollaborationOpportunity]
) -> List[Dict[str, Any]]:
    """Generate collaboration recommendations based on current state."""
    recommendations = []
    
    if len(conflicts) > 3:
        recommendations.append({
            "type": "conflict_management",
            "priority": "high",
            "title": "High Conflict Activity",
            "description": "Consider scheduling a team coordination meeting",
            "action": "schedule_meeting"
        })
    
    if len(opportunities) > 5:
        recommendations.append({
            "type": "collaboration_boost",
            "priority": "medium",
            "title": "Multiple Collaboration Opportunities",
            "description": "Great time for pair programming or knowledge sharing",
            "action": "initiate_collaboration"
        })
    
    same_file_conflicts = [c for c in conflicts if c.type == "concurrent_editing"]
    if len(same_file_conflicts) > 1:
        recommendations.append({
            "type": "workflow_improvement",
            "priority": "medium",
            "title": "Frequent Concurrent Editing",
            "description": "Consider implementing file locking or better coordination protocols",
            "action": "improve_workflow"
        })
    
    return recommendations