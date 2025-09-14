"""Webhook API endpoints for Git provider integrations."""

import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.repository import GitProvider
from app.services.webhook import WebhookService
from app.core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery")
):
    """
    Handle GitHub webhook events.
    
    GitHub sends webhooks for various repository events like pushes,
    pull requests, etc. This endpoint processes those events and
    triggers appropriate actions in the platform.
    """
    try:
        # Get raw payload for signature verification
        raw_payload = await request.body()
        
        # Parse JSON payload
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Prepare headers for processing
        headers = {
            "X-GitHub-Event": x_github_event,
            "X-Hub-Signature-256": x_hub_signature_256,
            "X-GitHub-Delivery": x_github_delivery
        }
        
        # Process webhook
        webhook_service = WebhookService(db)
        result = await webhook_service.process_webhook(
            provider=GitProvider.GITHUB,
            payload=payload,
            headers=headers,
            raw_payload=raw_payload
        )
        
        # Log the webhook processing
        logger.info(f"GitHub webhook processed: {x_github_event} - {result['status']}")
        
        return {
            "status": "success",
            "event": x_github_event,
            "delivery_id": x_github_delivery,
            "result": result
        }
        
    except ValidationError as e:
        logger.warning(f"GitHub webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"GitHub webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_gitlab_event: str = Header(None, alias="X-Gitlab-Event"),
    x_gitlab_token: str = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_instance: str = Header(None, alias="X-Gitlab-Instance")
):
    """
    Handle GitLab webhook events.
    
    GitLab sends webhooks for various project events like pushes,
    merge requests, etc. This endpoint processes those events and
    triggers appropriate actions in the platform.
    """
    try:
        # Get raw payload for signature verification
        raw_payload = await request.body()
        
        # Parse JSON payload
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Prepare headers for processing
        headers = {
            "X-Gitlab-Event": x_gitlab_event,
            "X-Gitlab-Token": x_gitlab_token,
            "X-Gitlab-Instance": x_gitlab_instance
        }
        
        # Process webhook
        webhook_service = WebhookService(db)
        result = await webhook_service.process_webhook(
            provider=GitProvider.GITLAB,
            payload=payload,
            headers=headers,
            raw_payload=raw_payload
        )
        
        # Log the webhook processing
        logger.info(f"GitLab webhook processed: {x_gitlab_event} - {result['status']}")
        
        return {
            "status": "success",
            "event": x_gitlab_event,
            "instance": x_gitlab_instance,
            "result": result
        }
        
    except ValidationError as e:
        logger.warning(f"GitLab webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"GitLab webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/events/{repository_id}")
async def get_webhook_events(
    repository_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent webhook events for a repository.
    
    Args:
        repository_id: Repository ID
        limit: Maximum number of events to return (default: 50)
        
    Returns:
        List of recent webhook events
    """
    try:
        webhook_service = WebhookService(db)
        events = await webhook_service.get_webhook_events(repository_id, limit)
        
        return {
            "repository_id": repository_id,
            "events": events,
            "count": len(events)
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error retrieving webhook events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/register/{repository_id}")
async def register_webhook(
    repository_id: str,
    webhook_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Register webhook with Git provider for a repository.
    
    Args:
        repository_id: Repository ID
        webhook_data: Webhook configuration data
        
    Returns:
        Webhook registration result
    """
    try:
        webhook_service = WebhookService(db)
        
        webhook_url = webhook_data.get("webhook_url")
        events = webhook_data.get("events", ["push", "pull_request"])
        
        if not webhook_url:
            raise HTTPException(status_code=400, detail="webhook_url is required")
        
        result = await webhook_service.register_webhook(
            repository_id=repository_id,
            webhook_url=webhook_url,
            events=events
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error registering webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/unregister/{repository_id}/{webhook_id}")
async def unregister_webhook(
    repository_id: str,
    webhook_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Unregister webhook from Git provider.
    
    Args:
        repository_id: Repository ID
        webhook_id: Webhook ID to unregister
        
    Returns:
        Unregistration result
    """
    try:
        webhook_service = WebhookService(db)
        success = await webhook_service.unregister_webhook(repository_id, webhook_id)
        
        return {
            "status": "success" if success else "failed",
            "repository_id": repository_id,
            "webhook_id": webhook_id
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error unregistering webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test")
async def test_webhook():
    """
    Test endpoint to verify webhook configuration.
    
    This endpoint can be used to test webhook connectivity
    and ensure the webhook URL is accessible.
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is accessible",
        "timestamp": "2024-01-01T00:00:00Z"
    }