"""API endpoints for deployment error handling and recovery."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.deployment_recovery import DeploymentRecoveryService
from app.services.deployment import DeploymentService
from app.core.exceptions import NotFoundError, DeploymentError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/deployments/{deployment_id}/analyze-failure")
async def analyze_deployment_failure(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze a failed deployment and provide recovery suggestions."""
    try:
        recovery_service = DeploymentRecoveryService(db)
        analysis = await recovery_service.handle_deployment_failure(deployment_id)
        
        return {
            "success": True,
            "deployment_id": deployment_id,
            "analysis": analysis,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeploymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing deployment failure: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/deployments/{deployment_id}/auto-retry")
async def auto_retry_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Automatically retry a failed deployment if conditions are met."""
    try:
        recovery_service = DeploymentRecoveryService(db)
        new_deployment = await recovery_service.auto_retry_deployment(deployment_id)
        
        if new_deployment:
            # Execute the new deployment in background
            from app.services.deployment_executor import DeploymentExecutor
            deployment_executor = DeploymentExecutor(db)
            background_tasks.add_task(
                deployment_executor.execute_deployment,
                str(new_deployment.id)
            )
            
            return {
                "success": True,
                "retry_initiated": True,
                "original_deployment_id": deployment_id,
                "new_deployment_id": str(new_deployment.id),
                "message": "Auto-retry initiated successfully"
            }
        else:
            return {
                "success": True,
                "retry_initiated": False,
                "deployment_id": deployment_id,
                "message": "Auto-retry not recommended for this deployment"
            }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeploymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error auto-retrying deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    rollback_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rollback to a previous successful deployment."""
    try:
        recovery_service = DeploymentRecoveryService(db)
        
        target_deployment_id = rollback_data.get("target_deployment_id")
        rollback_deployment = await recovery_service.rollback_deployment(
            deployment_id, target_deployment_id
        )
        
        # Execute the rollback deployment in background
        from app.services.deployment_executor import DeploymentExecutor
        deployment_executor = DeploymentExecutor(db)
        background_tasks.add_task(
            deployment_executor.execute_deployment,
            str(rollback_deployment.id)
        )
        
        return {
            "success": True,
            "original_deployment_id": deployment_id,
            "rollback_deployment_id": str(rollback_deployment.id),
            "target_deployment_id": target_deployment_id,
            "message": "Rollback initiated successfully"
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeploymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back deployment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/repositories/{repository_id}/deployment-health")
async def get_deployment_health(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployment health score and metrics for a repository."""
    try:
        recovery_service = DeploymentRecoveryService(db)
        health_data = await recovery_service.get_deployment_health_score(repository_id)
        
        return {
            "repository_id": repository_id,
            "health_data": health_data,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    except Exception as e:
        logger.error(f"Error getting deployment health: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/{deployment_id}/recovery-options")
async def get_recovery_options(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available recovery options for a failed deployment."""
    try:
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.get_deployment(deployment_id)
        
        if deployment.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recovery options are only available for failed deployments"
            )
        
        recovery_service = DeploymentRecoveryService(db)
        analysis = await recovery_service.handle_deployment_failure(deployment_id)
        
        return {
            "deployment_id": deployment_id,
            "recovery_options": analysis["recovery_options"],
            "auto_retry_recommended": analysis["auto_retry_recommended"],
            "rollback_available": analysis["rollback_available"],
            "error_category": analysis["error_analysis"]["category"],
            "error_severity": analysis["error_analysis"]["severity"]
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting recovery options: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployments/{deployment_id}/troubleshooting")
async def get_troubleshooting_guide(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed troubleshooting guide for a failed deployment."""
    try:
        recovery_service = DeploymentRecoveryService(db)
        analysis = await recovery_service.handle_deployment_failure(deployment_id)
        
        error_analysis = analysis["error_analysis"]
        
        return {
            "deployment_id": deployment_id,
            "error_category": error_analysis["category"],
            "error_severity": error_analysis["severity"],
            "patterns_matched": error_analysis["patterns_matched"],
            "troubleshooting_suggestions": error_analysis["suggestions"],
            "quick_fixes": error_analysis["quick_fixes"],
            "related_documentation": error_analysis["related_docs"],
            "recovery_plan": analysis["recovery_plan"],
            "similar_failures": analysis["similar_failures"],
            "confidence_score": error_analysis["analysis_confidence"]
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeploymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting troubleshooting guide: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/repositories/{repository_id}/failure-patterns")
async def get_failure_patterns(
    repository_id: str,
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get failure patterns and trends for a repository."""
    try:
        from sqlalchemy import select, and_, desc
        from app.models.deployment import Deployment, DeploymentStatus
        from datetime import datetime, timedelta
        
        # Get failed deployments in the specified period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(Deployment).where(
            and_(
                Deployment.repository_id == repository_id,
                Deployment.status == DeploymentStatus.FAILED.value,
                Deployment.created_at >= cutoff_date
            )
        ).order_by(desc(Deployment.created_at))
        
        result = await db.execute(query)
        failed_deployments = result.scalars().all()
        
        # Analyze patterns
        recovery_service = DeploymentRecoveryService(db)
        patterns = []
        category_counts = {}
        
        for deployment in failed_deployments:
            if deployment.error_message or deployment.build_logs or deployment.deployment_logs:
                error_logs = (deployment.error_message or "") + (deployment.build_logs or "") + (deployment.deployment_logs or "")
                error_analysis = recovery_service.error_analyzer.analyze_error(error_logs, deployment)
                
                category = error_analysis["category"]
                category_counts[category] = category_counts.get(category, 0) + 1
                
                patterns.append({
                    "deployment_id": str(deployment.id),
                    "created_at": deployment.created_at.isoformat(),
                    "commit_sha": deployment.commit_sha[:8],
                    "error_category": category,
                    "error_severity": error_analysis["severity"],
                    "patterns_matched": error_analysis["patterns_matched"][:3]  # Top 3 patterns
                })
        
        # Calculate trend data
        trend_data = []
        total_failures = len(failed_deployments)
        
        for category, count in category_counts.items():
            trend_data.append({
                "category": category,
                "count": count,
                "percentage": round((count / total_failures) * 100, 2) if total_failures > 0 else 0
            })
        
        trend_data.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "repository_id": repository_id,
            "analysis_period_days": days,
            "total_failures": total_failures,
            "failure_trends": trend_data,
            "recent_failures": patterns[:10],  # Last 10 failures
            "recommendations": _generate_pattern_recommendations(trend_data)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing failure patterns: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/deployments/bulk-recovery")
async def bulk_recovery_analysis(
    recovery_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze multiple failed deployments for bulk recovery actions."""
    try:
        deployment_ids = recovery_request.get("deployment_ids", [])
        
        if not deployment_ids or len(deployment_ids) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide 1-10 deployment IDs"
            )
        
        recovery_service = DeploymentRecoveryService(db)
        bulk_analysis = []
        
        for deployment_id in deployment_ids:
            try:
                analysis = await recovery_service.handle_deployment_failure(deployment_id)
                bulk_analysis.append({
                    "deployment_id": deployment_id,
                    "status": "analyzed",
                    "error_category": analysis["error_analysis"]["category"],
                    "auto_retry_recommended": analysis["auto_retry_recommended"],
                    "rollback_available": analysis["rollback_available"]
                })
            except Exception as e:
                bulk_analysis.append({
                    "deployment_id": deployment_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # Generate bulk recommendations
        categories = [item["error_category"] for item in bulk_analysis if item.get("error_category")]
        common_category = max(set(categories), key=categories.count) if categories else None
        
        bulk_recommendations = []
        if common_category:
            bulk_recommendations.append(f"Most deployments failed due to {common_category}. Consider addressing this systematically.")
        
        auto_retry_count = sum(1 for item in bulk_analysis if item.get("auto_retry_recommended"))
        if auto_retry_count > 0:
            bulk_recommendations.append(f"{auto_retry_count} deployments can be auto-retried.")
        
        return {
            "analyzed_deployments": bulk_analysis,
            "common_error_category": common_category,
            "bulk_recommendations": bulk_recommendations,
            "summary": {
                "total_analyzed": len(bulk_analysis),
                "auto_retry_candidates": auto_retry_count,
                "rollback_candidates": sum(1 for item in bulk_analysis if item.get("rollback_available"))
            }
        }
    
    except Exception as e:
        logger.error(f"Error in bulk recovery analysis: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/deployment-recovery/health-dashboard")
async def get_health_dashboard(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overall deployment health dashboard data."""
    try:
        from sqlalchemy import select, func, and_
        from app.models.deployment import Deployment, DeploymentStatus
        from app.models.repository import Repository
        from datetime import datetime, timedelta
        
        # Get repositories (filtered by project if specified)
        repo_query = select(Repository)
        if project_id:
            repo_query = repo_query.where(Repository.project_id == project_id)
        
        repo_result = await db.execute(repo_query)
        repositories = repo_result.scalars().all()
        
        dashboard_data = {
            "overview": {
                "total_repositories": len(repositories),
                "healthy_repositories": 0,
                "at_risk_repositories": 0,
                "critical_repositories": 0
            },
            "repository_health": [],
            "global_trends": {
                "success_rate_trend": [],
                "common_failure_categories": [],
                "recovery_success_rate": 85.5  # Mock data
            }
        }
        
        recovery_service = DeploymentRecoveryService(db)
        
        # Analyze each repository
        for repo in repositories:
            health_data = await recovery_service.get_deployment_health_score(str(repo.id))
            
            # Categorize repository health
            health_score = health_data["health_score"]
            if health_score >= 80:
                dashboard_data["overview"]["healthy_repositories"] += 1
                health_status = "healthy"
            elif health_score >= 60:
                dashboard_data["overview"]["at_risk_repositories"] += 1
                health_status = "at_risk"
            else:
                dashboard_data["overview"]["critical_repositories"] += 1
                health_status = "critical"
            
            dashboard_data["repository_health"].append({
                "repository_id": str(repo.id),
                "repository_name": repo.name,
                "health_score": health_score,
                "health_status": health_status,
                "success_rate": health_data["success_rate"],
                "total_deployments": health_data["total_deployments"],
                "top_failure_category": health_data["failure_trends"][0]["category"] if health_data["failure_trends"] else None
            })
        
        # Sort by health score (worst first for attention)
        dashboard_data["repository_health"].sort(key=lambda x: x["health_score"])
        
        return dashboard_data
    
    except Exception as e:
        logger.error(f"Error getting health dashboard: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


def _generate_pattern_recommendations(trend_data: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on failure patterns."""
    recommendations = []
    
    if not trend_data:
        return ["No failure patterns detected. Deployment health appears good."]
    
    top_failure = trend_data[0]
    
    if top_failure["percentage"] > 50:
        recommendations.append(f"Over 50% of failures are due to {top_failure['category']}. This should be your top priority to fix.")
    
    if len(trend_data) > 1 and trend_data[1]["percentage"] > 25:
        recommendations.append(f"Secondary failure cause is {trend_data[1]['category']} ({trend_data[1]['percentage']}%). Address this after fixing the primary issue.")
    
    # Category-specific recommendations
    if top_failure["category"] == "build_failure":
        recommendations.append("Consider implementing pre-commit hooks to catch build issues early.")
    elif top_failure["category"] == "dependency_error":
        recommendations.append("Consider using dependency lock files and regular dependency updates.")
    elif top_failure["category"] == "configuration_error":
        recommendations.append("Review deployment configuration and consider using configuration validation.")
    
    return recommendations