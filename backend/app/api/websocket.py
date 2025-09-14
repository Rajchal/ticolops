"""WebSocket API endpoints for real-time communication."""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.websocket import connection_manager
from app.core.deps import get_current_user_from_token
from app.services.activity import ActivityService, PresenceService
from app.services.project import ProjectService
from app.models.user import User
from app.schemas.activity import ActivityCreate, UserPresenceUpdate, ActivityType

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    project_id: Optional[str] = Query(None, description="Optional project ID for project-specific connection")
):
    """
    Main WebSocket endpoint for real-time communication.
    
    Query Parameters:
        token: JWT authentication token
        project_id: Optional project ID for project-specific features
    """
    connection_id = None
    current_user = None
    
    try:
        # Get database session
        async for db in get_db():
            # Authenticate user from token
            current_user = await get_current_user_from_token(token, db)
            if not current_user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
            
            # Validate project access if project_id provided
            if project_id:
                project_service = ProjectService(db)
                if not await project_service._user_has_project_access(project_id, str(current_user.id)):
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Project access denied")
                    return
            
            # Connect user
            connection_id = await connection_manager.connect(
                websocket=websocket,
                user_id=str(current_user.id),
                project_id=project_id,
                session_metadata={
                    "user_name": current_user.name,
                    "user_email": current_user.email,
                    "user_role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
                }
            )
            
            # Send welcome message
            welcome_message = {
                "type": "connection_established",
                "data": {
                    "connection_id": connection_id,
                    "user_id": str(current_user.id),
                    "project_id": project_id,
                    "server_time": asyncio.get_event_loop().time()
                }
            }
            await websocket.send_text(json.dumps(welcome_message))
            
            # Main message handling loop
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                        await handle_websocket_message(
                            connection_id=connection_id,
                            message=message,
                            user_id=str(current_user.id),
                            project_id=project_id,
                            db=db
                        )
                    except json.JSONDecodeError:
                        await send_error_message(websocket, "Invalid JSON format")
                    except Exception as e:
                        logger.error(f"Error handling WebSocket message: {e}")
                        await send_error_message(websocket, f"Message handling error: {str(e)}")
                        
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: user={current_user.id}, connection={connection_id}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            break  # Exit the async for loop
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Server error")
        except:
            pass
    
    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id)


async def handle_websocket_message(
    connection_id: str,
    message: Dict[str, Any],
    user_id: str,
    project_id: Optional[str],
    db: AsyncSession
):
    """
    Handle incoming WebSocket messages.
    
    Args:
        connection_id: WebSocket connection ID
        message: Parsed message from client
        user_id: User ID
        project_id: Optional project ID
        db: Database session
    """
    message_type = message.get("type")
    data = message.get("data", {})
    
    logger.debug(f"Handling WebSocket message: type={message_type}, user={user_id}")
    
    try:
        if message_type == "ping":
            await connection_manager.handle_ping(connection_id)
        
        elif message_type == "activity_update":
            await handle_activity_update(user_id, project_id, data, db)
        
        elif message_type == "presence_update":
            await handle_presence_update(user_id, project_id, data, db)
        
        elif message_type == "typing_start":
            await handle_typing_event(user_id, project_id, data, True)
        
        elif message_type == "typing_stop":
            await handle_typing_event(user_id, project_id, data, False)
        
        elif message_type == "cursor_update":
            await handle_cursor_update(user_id, project_id, data)
        
        elif message_type == "file_open":
            await handle_file_event(user_id, project_id, data, "opened")
        
        elif message_type == "file_close":
            await handle_file_event(user_id, project_id, data, "closed")
        
        elif message_type == "join_project":
            await handle_join_project(connection_id, user_id, data, db)
        
        elif message_type == "leave_project":
            await handle_leave_project(connection_id, user_id, data)
        
        elif message_type == "request_project_status":
            await handle_project_status_request(connection_id, user_id, project_id, db)
        
        elif message_type == "broadcast_message":
            await handle_broadcast_message(user_id, project_id, data, db)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await send_error_message_to_connection(connection_id, f"Unknown message type: {message_type}")
    
    except Exception as e:
        logger.error(f"Error handling message type {message_type}: {e}")
        await send_error_message_to_connection(connection_id, f"Error processing {message_type}: {str(e)}")


async def handle_activity_update(
    user_id: str, 
    project_id: Optional[str], 
    data: Dict[str, Any], 
    db: AsyncSession
):
    """Handle activity update from user."""
    try:
        activity_service = ActivityService(db)
        
        # Create activity record if requested
        if data.get("create_record", False):
            activity_data = ActivityCreate(
                type=ActivityType(data.get("activity_type", "user_active")),
                title=data.get("title", "User activity"),
                description=data.get("description"),
                location=data.get("location"),
                project_id=project_id,
                metadata=data.get("metadata", {})
            )
            
            await activity_service.create_activity(user_id, activity_data)
        
        # Broadcast activity update to project members
        if project_id:
            await connection_manager.update_user_activity(user_id, {
                "activity_type": data.get("activity_type"),
                "location": data.get("location"),
                "description": data.get("description"),
                "metadata": data.get("metadata", {})
            })
    
    except Exception as e:
        logger.error(f"Error handling activity update: {e}")


async def handle_presence_update(
    user_id: str, 
    project_id: Optional[str], 
    data: Dict[str, Any], 
    db: AsyncSession
):
    """Handle presence update from user."""
    try:
        presence_service = PresenceService(db)
        
        # Update presence in database
        presence_update = UserPresenceUpdate(
            status=data.get("status"),
            current_location=data.get("current_location"),
            current_activity=data.get("current_activity"),
            metadata=data.get("metadata", {})
        )
        
        # Note: This is a simplified update - in a full implementation,
        # you'd need to get the existing presence record first
        
        # Broadcast presence update to project members
        if project_id:
            message = {
                "type": "presence_update",
                "data": {
                    "user_id": user_id,
                    "status": data.get("status"),
                    "current_location": data.get("current_location"),
                    "current_activity": data.get("current_activity"),
                    "timestamp": asyncio.get_event_loop().time()
                }
            }
            
            await connection_manager.broadcast_to_project(project_id, message, exclude_user=user_id)
    
    except Exception as e:
        logger.error(f"Error handling presence update: {e}")


async def handle_typing_event(
    user_id: str, 
    project_id: Optional[str], 
    data: Dict[str, Any], 
    is_typing: bool
):
    """Handle typing start/stop events."""
    if not project_id:
        return
    
    message = {
        "type": "typing_indicator",
        "data": {
            "user_id": user_id,
            "file_path": data.get("file_path"),
            "is_typing": is_typing,
            "timestamp": asyncio.get_event_loop().time()
        }
    }
    
    await connection_manager.broadcast_to_project(project_id, message, exclude_user=user_id)


async def handle_cursor_update(
    user_id: str, 
    project_id: Optional[str], 
    data: Dict[str, Any]
):
    """Handle cursor position updates."""
    if not project_id:
        return
    
    message = {
        "type": "cursor_update",
        "data": {
            "user_id": user_id,
            "file_path": data.get("file_path"),
            "position": data.get("position", {}),
            "selection": data.get("selection"),
            "timestamp": asyncio.get_event_loop().time()
        }
    }
    
    await connection_manager.broadcast_to_project(project_id, message, exclude_user=user_id)


async def handle_file_event(
    user_id: str, 
    project_id: Optional[str], 
    data: Dict[str, Any], 
    event_type: str
):
    """Handle file open/close events."""
    if not project_id:
        return
    
    message = {
        "type": "file_event",
        "data": {
            "user_id": user_id,
            "file_path": data.get("file_path"),
            "event_type": event_type,
            "timestamp": asyncio.get_event_loop().time()
        }
    }
    
    await connection_manager.broadcast_to_project(project_id, message, exclude_user=user_id)


async def handle_join_project(
    connection_id: str, 
    user_id: str, 
    data: Dict[str, Any], 
    db: AsyncSession
):
    """Handle user joining a project."""
    new_project_id = data.get("project_id")
    if not new_project_id:
        await send_error_message_to_connection(connection_id, "Project ID required")
        return
    
    try:
        # Validate project access
        project_service = ProjectService(db)
        if not await project_service._user_has_project_access(new_project_id, user_id):
            await send_error_message_to_connection(connection_id, "Project access denied")
            return
        
        # Update connection metadata to include new project
        if connection_id in connection_manager.connection_metadata:
            connection_manager.connection_metadata[connection_id]["project_id"] = new_project_id
            
            # Add to project subscriptions
            if new_project_id not in connection_manager.project_subscriptions:
                connection_manager.project_subscriptions[new_project_id] = set()
            connection_manager.project_subscriptions[new_project_id].add(connection_id)
        
        # Send confirmation
        message = {
            "type": "project_joined",
            "data": {
                "project_id": new_project_id,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        websocket = connection_manager.connection_metadata[connection_id]["websocket"]
        await websocket.send_text(json.dumps(message))
        
        # Notify other project members
        await connection_manager.broadcast_to_project(
            new_project_id, 
            {
                "type": "user_joined_project",
                "data": {
                    "user_id": user_id,
                    "timestamp": asyncio.get_event_loop().time()
                }
            }, 
            exclude_user=user_id
        )
    
    except Exception as e:
        logger.error(f"Error handling join project: {e}")
        await send_error_message_to_connection(connection_id, f"Failed to join project: {str(e)}")


async def handle_leave_project(connection_id: str, user_id: str, data: Dict[str, Any]):
    """Handle user leaving a project."""
    project_id = data.get("project_id")
    if not project_id:
        return
    
    # Remove from project subscriptions
    if project_id in connection_manager.project_subscriptions:
        connection_manager.project_subscriptions[project_id].discard(connection_id)
    
    # Update connection metadata
    if connection_id in connection_manager.connection_metadata:
        connection_manager.connection_metadata[connection_id]["project_id"] = None
    
    # Notify other project members
    await connection_manager.broadcast_to_project(
        project_id, 
        {
            "type": "user_left_project",
            "data": {
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
    )


async def handle_project_status_request(
    connection_id: str, 
    user_id: str, 
    project_id: Optional[str], 
    db: AsyncSession
):
    """Handle request for project status information."""
    if not project_id:
        await send_error_message_to_connection(connection_id, "No project context")
        return
    
    try:
        # Get project users
        project_users = await connection_manager.get_project_users(project_id)
        
        # Get connection stats
        stats = connection_manager.get_connection_stats()
        
        # Send project status
        message = {
            "type": "project_status",
            "data": {
                "project_id": project_id,
                "connected_users": project_users,
                "connection_stats": stats,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        websocket = connection_manager.connection_metadata[connection_id]["websocket"]
        await websocket.send_text(json.dumps(message))
    
    except Exception as e:
        logger.error(f"Error handling project status request: {e}")
        await send_error_message_to_connection(connection_id, f"Failed to get project status: {str(e)}")


async def handle_broadcast_message(
    user_id: str, 
    project_id: Optional[str], 
    data: Dict[str, Any], 
    db: AsyncSession
):
    """Handle broadcast message request."""
    if not project_id:
        return
    
    try:
        # Validate user can broadcast (e.g., project admin)
        project_service = ProjectService(db)
        if not await project_service._user_can_edit_project(project_id, user_id):
            return  # Silently ignore unauthorized broadcast attempts
        
        # Broadcast message
        message = {
            "type": "broadcast",
            "data": {
                "from_user_id": user_id,
                "message": data.get("message", ""),
                "message_type": data.get("message_type", "info"),
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        await connection_manager.broadcast_to_project(project_id, message)
    
    except Exception as e:
        logger.error(f"Error handling broadcast message: {e}")


async def send_error_message(websocket: WebSocket, error_message: str):
    """Send error message to WebSocket."""
    try:
        message = {
            "type": "error",
            "data": {
                "message": error_message,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        await websocket.send_text(json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


async def send_error_message_to_connection(connection_id: str, error_message: str):
    """Send error message to specific connection."""
    if connection_id in connection_manager.connection_metadata:
        websocket = connection_manager.connection_metadata[connection_id]["websocket"]
        await send_error_message(websocket, error_message)


# REST API endpoints for WebSocket management

@router.get("/ws/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
):
    """Get WebSocket connection statistics."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    
    return connection_manager.get_connection_stats()


@router.post("/ws/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Broadcast message via WebSocket (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    
    broadcast_data = {
        "type": "admin_broadcast",
        "data": {
            "message": message.get("message", ""),
            "from_admin": current_user.name,
            "timestamp": asyncio.get_event_loop().time()
        }
    }
    
    if project_id:
        sent_count = await connection_manager.broadcast_to_project(project_id, broadcast_data)
    else:
        sent_count = await connection_manager.broadcast_to_all(broadcast_data)
    
    return {
        "success": True,
        "message": "Message broadcasted",
        "recipients": sent_count
    }


@router.post("/ws/cleanup")
async def cleanup_connections(
    timeout_minutes: int = Query(30, ge=5, le=1440),
    current_user: User = Depends(get_current_user)
):
    """Clean up stale WebSocket connections (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    
    cleaned_count = await connection_manager.cleanup_stale_connections(timeout_minutes)
    
    return {
        "success": True,
        "message": f"Cleaned up {cleaned_count} stale connections",
        "cleaned_count": cleaned_count,
        "timeout_minutes": timeout_minutes
    }