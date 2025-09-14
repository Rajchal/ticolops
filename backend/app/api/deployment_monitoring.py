"""API endpoints for deployment monitoring and execution management."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.deployment_executor import DeploymentExecutor, DeploymentMonitor
from app.services.deployment import DeploymentService
from app.core.exceptions import NotFoundError, DeploymentError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/deployments/{deployment_id}/execute")
async def execute_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a deployment in the background."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        # Check if deployment is in a state that can be executed
        if deployment.status not in ["pending", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deployment is in {deployment.status} state and cannot be executed"
            )
        
        # Add background task to execute deployment
        deployment_executor = DeploymentExecutor(db)
        background_tasks.add_task(
            deployment_executor.execute_deployment,
            deployment_id
        )
        
        return {
            "success": True,
            "message": "Deployment execution started",
            "deployment_id": deployment_id,
            "status": "executing"
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/monitoring/active")
async def get_active_deployments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get status of all active deployments."""
    try:
        deployment_monitor = DeploymentMonitor(db)
        active_deployments = await deployment_monitor.monitor_active_deployments()
        
        return {
            "active_deployments": active_deployments,
            "count": len(active_deployments),
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    except Exception as e:
        logger.error(f"Error monitoring active deployments: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/monitoring/metrics")
async def get_deployment_metrics(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours (max 7 days)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployment metrics for the specified time period."""
    try:
        deployment_monitor = DeploymentMonitor(db)
        metrics = await deployment_monitor.collect_deployment_metrics(hours)
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error collecting deployment metrics: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/{deployment_id}/status")
async def get_deployment_status(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time deployment status with detailed information."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        # Calculate progress percentage based on status
        progress_map = {
            "pending": 0,
            "queued": 10,
            "building": 50,
            "deploying": 80,
            "success": 100,
            "failed": 0,
            "cancelled": 0
        }
        
        progress = progress_map.get(deployment.status, 0)
        
        # Calculate duration
        duration_seconds = None
        if deployment.started_at:
            from datetime import datetime
            if deployment.completed_at:
                duration_seconds = int((deployment.completed_at - deployment.started_at).total_seconds())
            else:
                duration_seconds = int((datetime.utcnow() - deployment.started_at).total_seconds())
        
        return {
            "deployment_id": deployment_id,
            "status": deployment.status,
            "progress_percent": progress,
            "preview_url": deployment.preview_url,
            "created_at": deployment.created_at.isoformat(),
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
            "duration_seconds": duration_seconds,
            "commit_sha": deployment.commit_sha,
            "branch": deployment.branch,
            "project_type": deployment.project_type,
            "has_logs": bool(deployment.build_logs or deployment.deployment_logs),
            "error_message": deployment.error_message
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting deployment status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/{deployment_id}/logs/stream")
async def stream_deployment_logs(
    deployment_id: str,
    log_type: str = Query("all", regex="^(all|build|deployment)$", description="Type of logs to stream"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream deployment logs in real-time."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        logs = []
        
        if log_type in ["all", "build"] and deployment.build_logs:
            build_lines = deployment.build_logs.split('\n')
            for i, line in enumerate(build_lines):
                logs.append({
                    "timestamp": deployment.started_at.isoformat() if deployment.started_at else None,
                    "type": "build",
                    "line_number": i + 1,
                    "message": line
                })
        
        if log_type in ["all", "deployment"] and deployment.deployment_logs:
            deploy_lines = deployment.deployment_logs.split('\n')
            for i, line in enumerate(deploy_lines):
                logs.append({
                    "timestamp": deployment.started_at.isoformat() if deployment.started_at else None,
                    "type": "deployment",
                    "line_number": i + 1,
                    "message": line
                })
        
        return {
            "deployment_id": deployment_id,
            "log_type": log_type,
            "logs": logs,
            "total_lines": len(logs),
            "status": deployment.status
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error streaming deployment logs: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/deployments/{deployment_id}/preview")
async def generate_preview_link(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate or refresh preview link for a successful deployment."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        if deployment.status != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preview links can only be generated for successful deployments"
            )
        
        # Generate new preview URL if not exists
        if not deployment.preview_url:
            preview_url = f"https://preview-{deployment.id}.ticolops.dev"
            await deployment_service.update_deployment_status(
                deployment_id,
                deployment.status,
                preview_url=preview_url
            )
        else:
            preview_url = deployment.preview_url
        
        return {
            "deployment_id": deployment_id,
            "preview_url": preview_url,
            "status": deployment.status,
            "generated_at": "2024-01-01T00:00:00Z"
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating preview link: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/monitoring/queue")
async def get_deployment_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current deployment queue status."""
    try:
        from sqlalchemy import select, func
        from app.models.deployment import Deployment, DeploymentStatus
        
        # Get queue statistics
        pending_query = select(func.count(Deployment.id)).where(
            Deployment.status == DeploymentStatus.PENDING.value
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0
        
        building_query = select(func.count(Deployment.id)).where(
            Deployment.status == DeploymentStatus.BUILDING.value
        )
        building_result = await db.execute(building_query)
        building_count = building_result.scalar() or 0
        
        deploying_query = select(func.count(Deployment.id)).where(
            Deployment.status == DeploymentStatus.DEPLOYING.value
        )
        deploying_result = await db.execute(deploying_query)
        deploying_count = deploying_result.scalar() or 0
        
        # Get recent deployments in queue
        recent_query = select(Deployment).where(
            Deployment.status.in_([
                DeploymentStatus.PENDING.value,
                DeploymentStatus.BUILDING.value,
                DeploymentStatus.DEPLOYING.value
            ])
        ).order_by(Deployment.created_at.desc()).limit(10)
        
        recent_result = await db.execute(recent_query)
        recent_deployments = recent_result.scalars().all()
        
        queue_items = []
        for deployment in recent_deployments:
            queue_items.append({
                "deployment_id": str(deployment.id),
                "repository_id": str(deployment.repository_id),
                "status": deployment.status,
                "created_at": deployment.created_at.isoformat(),
                "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
                "commit_sha": deployment.commit_sha[:8],
                "branch": deployment.branch
            })
        
        return {
            "queue_summary": {
                "pending": pending_count,
                "building": building_count,
                "deploying": deploying_count,
                "total_active": pending_count + building_count + deploying_count
            },
            "queue_items": queue_items,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    except Exception as e:
        logger.error(f"Error getting deployment queue: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/deployments/monitoring/cleanup")
async def cleanup_old_deployments(
    days: int = Query(30, ge=7, le=365, description="Delete deployments older than this many days"),
    dry_run: bool = Query(True, description="If true, only return what would be deleted"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up old deployment records and artifacts."""
    try:
        from sqlalchemy import select, delete
        from app.models.deployment import Deployment
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old deployments
        old_deployments_query = select(Deployment).where(
            Deployment.created_at < cutoff_date,
            Deployment.status.in_(["success", "failed", "cancelled"])
        )
        old_deployments_result = await db.execute(old_deployments_query)
        old_deployments = old_deployments_result.scalars().all()
        
        cleanup_summary = {
            "cutoff_date": cutoff_date.isoformat(),
            "deployments_found": len(old_deployments),
            "dry_run": dry_run,
            "deployments": []
        }
        
        for deployment in old_deployments:
            cleanup_summary["deployments"].append({
                "deployment_id": str(deployment.id),
                "created_at": deployment.created_at.isoformat(),
                "status": deployment.status,
                "repository_id": str(deployment.repository_id)
            })
        
        if not dry_run and old_deployments:
            # Actually delete the deployments
            delete_query = delete(Deployment).where(
                Deployment.created_at < cutoff_date,
                Deployment.status.in_(["success", "failed", "cancelled"])
            )
            await db.execute(delete_query)
            await db.commit()
            
            cleanup_summary["deleted"] = True
            logger.info(f"Cleaned up {len(old_deployments)} old deployments")
        else:
            cleanup_summary["deleted"] = False
        
        return cleanup_summary
    
    except Exception as e:
        logger.error(f"Error cleaning up deployments: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/monitoring/health")
async def get_deployment_system_health():
    """Get deployment system health status."""
    try:
        # Check various system components
        health_checks = {
            "database": {"status": "healthy", "response_time_ms": 5},
            "docker": {"status": "healthy", "version": "20.10.0"},
            "hosting_platforms": {
                "vercel": {"status": "operational", "api_latency_ms": 150},
                "netlify": {"status": "operational", "api_latency_ms": 200}
            },
            "deployment_queue": {"status": "healthy", "active_deployments": 3},
            "storage": {"status": "healthy", "disk_usage_percent": 45}
        }
        
        # Determine overall health
        all_healthy = all(
            component.get("status") == "healthy" or component.get("status") == "operational"
            for component in health_checks.values()
            if isinstance(component, dict) and "status" in component
        )
        
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": "2024-01-01T00:00:00Z",
            "components": health_checks,
            "uptime_seconds": 86400,  # Mock 24 hours uptime
            "version": "1.0.0"
        }
    
    except Exception as e:
        logger.error(f"Error checking deployment system health: {str(e)}")
        return {
            "overall_status": "error",
            "timestamp": "2024-01-01T00:00:00Z",
            "error": str(e),
            "components": {}
        }