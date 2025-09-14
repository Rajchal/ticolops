"""API endpoints for notification triggers and event handling."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.notification_triggers import get_notification_trigger_service

logger = logging.getLogger(__name__)
router = APIRouter()


class DeploymentEventData(BaseModel):
    """Data for deployment event triggers."""
    deployment_id: str
    event_type: str = Field(..., description="Event type: started, success, failed, cancelled")
    repository_id: str
    branch: str
    commit_hash: str
    environment: str = "production"
    error_details: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[int] = None


class ActivityEventData(BaseModel):
    """Data for activity event triggers."""
    activity_id: str
    event_type: str = Field(..., description="Event type: started, conflict_detected, collaboration_opportunity, mention_detected")
    user_id: str
    project_id: str
    location: str
    activity_type: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CollaborationTriggerData(BaseModel):
    """Data for collaboration triggers."""
    trigger_type: str = Field(..., description="Trigger type: help_requested, work_completed, review_requested, critical_path_update")
    project_id: str
    user_id: str
    component: Optional[str] = None
    description: Optional[str] = None
    urgency: Optional[str] = "medium"
    reviewers: Optional[List[str]] = None
    deadline: Optional[str] = None
    priority: Optional[str] = "medium"


class MentionDetectionData(BaseModel):
    """Data for mention detection."""
    content: str
    source_user_id: str
    project_id: str
    context_type: str = "comment"
    context_id: Optional[str] = None
    context_url: Optional[str] = None


@router.post("/triggers/deployment")
async def trigger_deployment_event(
    event_data: DeploymentEventData,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger deployment-related notifications.
    
    Args:
        event_data: Deployment event data
        background_tasks: Background task manager
        current_user: Current user
        db: Database session
    """
    try:
        trigger_service = get_notification_trigger_service(db)
        
        # Create mock deployment object (in real implementation, fetch from DB)
        deployment = type('Deployment', (), {
            'id': event_data.deployment_id,
            'repository_id': event_data.repository_id,
            'branch': event_data.branch,
            'commit_hash': event_data.commit_hash,
            'environment': event_data.environment,
            'status': event_data.event_type,
            'logs': [],
            'started_at': None,
            'completed_at': None,
            'url': None
        })()
        
        # Prepare additional data
        additional_data = {}
        if event_data.error_details:
            additional_data["error"] = event_data.error_details
        if event_data.duration_seconds:
            additional_data["duration"] = event_data.duration_seconds
        
        # Handle the deployment event in background
        background_tasks.add_task(
            trigger_service.handle_deployment_event,
            deployment,
            event_data.event_type,
            additional_data
        )
        
        return {
            "success": True,
            "message": f"Deployment event '{event_data.event_type}' triggered successfully",
            "deployment_id": event_data.deployment_id,
            "event_type": event_data.event_type
        }
    
    except Exception as e:
        logger.error(f"Error triggering deployment event: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/triggers/activity")
async def trigger_activity_event(
    event_data: ActivityEventData,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger activity-related notifications.
    
    Args:
        event_data: Activity event data
        background_tasks: Background task manager
        current_user: Current user
        db: Database session
    """
    try:
        trigger_service = get_notification_trigger_service(db)
        
        # Create mock activity object (in real implementation, fetch from DB)
        activity = type('Activity', (), {
            'id': event_data.activity_id,
            'user_id': event_data.user_id,
            'project_id': event_data.project_id,
            'location': event_data.location,
            'type': event_data.activity_type,
            'metadata': event_data.metadata or {}
        })()
        
        # Prepare additional data
        additional_data = {}
        if event_data.content:
            additional_data["content"] = event_data.content
        if event_data.metadata:
            additional_data.update(event_data.metadata)
        
        # Handle the activity event in background
        background_tasks.add_task(
            trigger_service.handle_activity_event,
            activity,
            event_data.event_type,
            additional_data
        )
        
        return {
            "success": True,
            "message": f"Activity event '{event_data.event_type}' triggered successfully",
            "activity_id": event_data.activity_id,
            "event_type": event_data.event_type
        }
    
    except Exception as e:
        logger.error(f"Error triggering activity event: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/triggers/collaboration")
async def trigger_collaboration_event(
    trigger_data: CollaborationTriggerData,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger collaboration-related notifications.
    
    Args:
        trigger_data: Collaboration trigger data
        background_tasks: Background task manager
        current_user: Current user
        db: Database session
    """
    try:
        trigger_service = get_notification_trigger_service(db)
        
        # Prepare trigger data
        data = {
            "component": trigger_data.component,
            "description": trigger_data.description,
            "urgency": trigger_data.urgency,
            "reviewers": trigger_data.reviewers or [],
            "deadline": trigger_data.deadline,
            "priority": trigger_data.priority
        }
        
        # Handle the collaboration trigger in background
        background_tasks.add_task(
            trigger_service.handle_collaboration_trigger,
            trigger_data.trigger_type,
            trigger_data.project_id,
            trigger_data.user_id,
            data
        )
        
        return {
            "success": True,
            "message": f"Collaboration trigger '{trigger_data.trigger_type}' activated successfully",
            "trigger_type": trigger_data.trigger_type,
            "project_id": trigger_data.project_id
        }
    
    except Exception as e:
        logger.error(f"Error triggering collaboration event: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/triggers/mentions")
async def detect_mentions(
    mention_data: MentionDetectionData,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect and handle mentions in content.
    
    Args:
        mention_data: Mention detection data
        background_tasks: Background task manager
        current_user: Current user
        db: Database session
    """
    try:
        trigger_service = get_notification_trigger_service(db)
        
        # Get source user and project (in real implementation, fetch from DB)
        source_user = type('User', (), {
            'id': mention_data.source_user_id,
            'name': 'Source User',
            'username': 'sourceuser'
        })()
        
        project = type('Project', (), {
            'id': mention_data.project_id,
            'name': 'Sample Project'
        })()
        
        # Prepare context
        context = {
            "type": mention_data.context_type,
            "id": mention_data.context_id,
            "url": mention_data.context_url or f"/projects/{mention_data.project_id}"
        }
        
        # Detect mentions in background
        background_tasks.add_task(
            trigger_service.detect_and_handle_mentions,
            mention_data.content,
            source_user,
            project,
            context
        )
        
        return {
            "success": True,
            "message": "Mention detection triggered successfully",
            "content_length": len(mention_data.content),
            "project_id": mention_data.project_id
        }
    
    except Exception as e:
        logger.error(f"Error detecting mentions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/triggers/batch")
async def trigger_batch_events(
    events: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger multiple notification events in batch.
    
    Args:
        events: List of event data
        background_tasks: Background task manager
        current_user: Current user
        db: Database session
    """
    try:
        trigger_service = get_notification_trigger_service(db)
        processed_events = []
        
        for event in events:
            event_type = event.get("type")
            
            if event_type == "deployment":
                # Process deployment event
                deployment_data = DeploymentEventData(**event.get("data", {}))
                deployment = type('Deployment', (), {
                    'id': deployment_data.deployment_id,
                    'repository_id': deployment_data.repository_id,
                    'branch': deployment_data.branch,
                    'commit_hash': deployment_data.commit_hash,
                    'environment': deployment_data.environment
                })()
                
                background_tasks.add_task(
                    trigger_service.handle_deployment_event,
                    deployment,
                    deployment_data.event_type,
                    deployment_data.error_details or {}
                )
                
                processed_events.append({
                    "type": "deployment",
                    "id": deployment_data.deployment_id,
                    "status": "queued"
                })
            
            elif event_type == "activity":
                # Process activity event
                activity_data = ActivityEventData(**event.get("data", {}))
                activity = type('Activity', (), {
                    'id': activity_data.activity_id,
                    'user_id': activity_data.user_id,
                    'project_id': activity_data.project_id,
                    'location': activity_data.location,
                    'type': activity_data.activity_type
                })()
                
                background_tasks.add_task(
                    trigger_service.handle_activity_event,
                    activity,
                    activity_data.event_type,
                    activity_data.metadata or {}
                )
                
                processed_events.append({
                    "type": "activity",
                    "id": activity_data.activity_id,
                    "status": "queued"
                })
            
            elif event_type == "collaboration":
                # Process collaboration event
                collab_data = CollaborationTriggerData(**event.get("data", {}))
                
                background_tasks.add_task(
                    trigger_service.handle_collaboration_trigger,
                    collab_data.trigger_type,
                    collab_data.project_id,
                    collab_data.user_id,
                    {
                        "component": collab_data.component,
                        "description": collab_data.description,
                        "urgency": collab_data.urgency
                    }
                )
                
                processed_events.append({
                    "type": "collaboration",
                    "trigger_type": collab_data.trigger_type,
                    "status": "queued"
                })
        
        return {
            "success": True,
            "message": f"Processed {len(processed_events)} events successfully",
            "processed_events": processed_events,
            "total_events": len(events)
        }
    
    except Exception as e:
        logger.error(f"Error processing batch events: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/triggers/stats")
async def get_trigger_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get notification trigger statistics.
    
    Returns:
        Trigger statistics and metrics
    """
    try:
        # In a real implementation, this would query actual statistics
        # For now, returning mock data
        stats = {
            "deployment_triggers": {
                "total": 150,
                "success": 120,
                "failed": 25,
                "cancelled": 5
            },
            "activity_triggers": {
                "total": 500,
                "conflicts_detected": 15,
                "collaborations_suggested": 45,
                "mentions_processed": 80
            },
            "collaboration_triggers": {
                "help_requests": 25,
                "review_requests": 60,
                "work_completions": 95,
                "critical_path_updates": 12
            },
            "notification_delivery": {
                "total_sent": 1200,
                "delivered": 1150,
                "failed": 50,
                "delivery_rate": 95.8
            }
        }
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    except Exception as e:
        logger.error(f"Error getting trigger stats: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/triggers/test")
async def test_notification_trigger(
    trigger_type: str,
    test_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test notification triggers with sample data.
    
    Args:
        trigger_type: Type of trigger to test
        test_data: Test data for the trigger
        background_tasks: Background task manager
        current_user: Current user
        db: Database session
    """
    try:
        trigger_service = get_notification_trigger_service(db)
        
        if trigger_type == "deployment_success":
            # Test deployment success notification
            deployment = type('Deployment', (), {
                'id': 'test-deployment-123',
                'repository_id': 'test-repo-456',
                'branch': 'main',
                'commit_hash': 'abc123def456',
                'environment': 'production',
                'url': 'https://test-app.vercel.app',
                'started_at': None,
                'completed_at': None
            })()
            
            background_tasks.add_task(
                trigger_service.handle_deployment_event,
                deployment,
                "deployment_success",
                test_data
            )
        
        elif trigger_type == "mention":
            # Test mention detection
            source_user = type('User', (), {
                'id': str(current_user.id),
                'name': current_user.name,
                'username': getattr(current_user, 'username', 'testuser')
            })()
            
            project = type('Project', (), {
                'id': test_data.get('project_id', 'test-project-123'),
                'name': 'Test Project'
            })()
            
            context = {
                "type": "test",
                "id": "test-context-123",
                "url": "/test"
            }
            
            background_tasks.add_task(
                trigger_service.detect_and_handle_mentions,
                test_data.get('content', '@testuser This is a test mention'),
                source_user,
                project,
                context
            )
        
        elif trigger_type == "conflict":
            # Test conflict detection
            activity = type('Activity', (), {
                'id': 'test-activity-123',
                'user_id': str(current_user.id),
                'project_id': test_data.get('project_id', 'test-project-123'),
                'location': test_data.get('location', 'src/components/TestComponent.tsx'),
                'type': 'coding'
            })()
            
            background_tasks.add_task(
                trigger_service.handle_activity_event,
                activity,
                "conflict_detected",
                {
                    "conflicting_users": [str(current_user.id), "other-user-456"],
                    "severity": "medium"
                }
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown trigger type: {trigger_type}"
            )
        
        return {
            "success": True,
            "message": f"Test trigger '{trigger_type}' executed successfully",
            "trigger_type": trigger_type,
            "test_data": test_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing notification trigger: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")