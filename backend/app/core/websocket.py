"""WebSocket connection manager for real-time communication."""

import json
import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.services.activity import ActivityService, PresenceService
from app.schemas.activity import UserPresenceCreate, UserPresenceStatus, ActivityType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time communication."""

    def __init__(self):
        # Active connections: {project_id: {user_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        # User to connection mapping: {user_id: set(connection_ids)}
        self.user_connections: Dict[str, Set[str]] = {}
        # Project subscriptions: {project_id: set(connection_ids)}
        self.project_subscriptions: Dict[str, Set[str]] = {}

    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        project_id: Optional[str] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
            project_id: Optional project ID for project-specific connections
            session_metadata: Optional session metadata
            
        Returns:
            Connection ID
        """
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid4())
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "project_id": project_id,
            "websocket": websocket,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "metadata": session_metadata or {}
        }
        
        # Update user connections mapping
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Update project subscriptions if project_id provided
        if project_id:
            if project_id not in self.project_subscriptions:
                self.project_subscriptions[project_id] = set()
            self.project_subscriptions[project_id].add(connection_id)
            
            # Store in active connections for backward compatibility
            if project_id not in self.active_connections:
                self.active_connections[project_id] = {}
            self.active_connections[project_id][user_id] = websocket
        
        logger.info(f"WebSocket connected: user={user_id}, project={project_id}, connection={connection_id}")
        
        # Update user presence
        await self._update_user_presence(user_id, project_id, UserPresenceStatus.ONLINE)
        
        # Notify other users about the connection
        if project_id:
            await self._broadcast_user_status_change(user_id, project_id, "connected")
        
        return connection_id

    async def disconnect(self, connection_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            connection_id: Connection ID to remove
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        user_id = metadata["user_id"]
        project_id = metadata.get("project_id")
        
        # Remove from connection metadata
        del self.connection_metadata[connection_id]
        
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from project subscriptions
        if project_id and project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(connection_id)
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        # Remove from active connections (backward compatibility)
        if project_id and project_id in self.active_connections:
            if user_id in self.active_connections[project_id]:
                del self.active_connections[project_id][user_id]
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        
        logger.info(f"WebSocket disconnected: user={user_id}, project={project_id}, connection={connection_id}")
        
        # Update user presence if no more connections
        if user_id not in self.user_connections:
            await self._update_user_presence(user_id, project_id, UserPresenceStatus.OFFLINE)
            
            # Notify other users about the disconnection
            if project_id:
                await self._broadcast_user_status_change(user_id, project_id, "disconnected")

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to all connections of a specific user.
        
        Args:
            user_id: Target user ID
            message: Message to send
            
        Returns:
            True if message was sent to at least one connection
        """
        if user_id not in self.user_connections:
            return False
        
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.user_connections[user_id].copy():
            if connection_id in self.connection_metadata:
                websocket = self.connection_metadata[connection_id]["websocket"]
                try:
                    await websocket.send_text(json.dumps(message))
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send message to connection {connection_id}: {e}")
                    failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
        
        return sent_count > 0

    async def broadcast_to_project(
        self, 
        project_id: str, 
        message: Dict[str, Any], 
        exclude_user: Optional[str] = None
    ) -> int:
        """
        Broadcast a message to all users in a project.
        
        Args:
            project_id: Project ID
            message: Message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
            
        Returns:
            Number of connections that received the message
        """
        if project_id not in self.project_subscriptions:
            return 0
        
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.project_subscriptions[project_id].copy():
            if connection_id in self.connection_metadata:
                metadata = self.connection_metadata[connection_id]
                
                # Skip excluded user
                if exclude_user and metadata["user_id"] == exclude_user:
                    continue
                
                websocket = metadata["websocket"]
                try:
                    await websocket.send_text(json.dumps(message))
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to connection {connection_id}: {e}")
                    failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
        
        return sent_count

    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected users.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of connections that received the message
        """
        sent_count = 0
        failed_connections = []
        
        for connection_id in list(self.connection_metadata.keys()):
            websocket = self.connection_metadata[connection_id]["websocket"]
            try:
                await websocket.send_text(json.dumps(message))
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to connection {connection_id}: {e}")
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
        
        return sent_count

    async def get_project_users(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all users currently connected to a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of user information
        """
        if project_id not in self.project_subscriptions:
            return []
        
        users = {}
        for connection_id in self.project_subscriptions[project_id]:
            if connection_id in self.connection_metadata:
                metadata = self.connection_metadata[connection_id]
                user_id = metadata["user_id"]
                
                if user_id not in users:
                    users[user_id] = {
                        "user_id": user_id,
                        "connected_at": metadata["connected_at"],
                        "last_activity": metadata["last_activity"],
                        "connection_count": 0
                    }
                users[user_id]["connection_count"] += 1
        
        return list(users.values())

    async def update_user_activity(self, user_id: str, activity_data: Dict[str, Any]):
        """
        Update user activity and broadcast to relevant projects.
        
        Args:
            user_id: User ID
            activity_data: Activity data to broadcast
        """
        # Update last activity for all user connections
        current_time = datetime.utcnow()
        
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = current_time
        
        # Broadcast activity update to relevant projects
        projects_to_notify = set()
        
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.connection_metadata:
                    project_id = self.connection_metadata[connection_id].get("project_id")
                    if project_id:
                        projects_to_notify.add(project_id)
        
        # Broadcast to each project
        message = {
            "type": "user_activity_update",
            "data": {
                "user_id": user_id,
                "activity": activity_data,
                "timestamp": current_time.isoformat()
            }
        }
        
        for project_id in projects_to_notify:
            await self.broadcast_to_project(project_id, message, exclude_user=user_id)

    async def handle_ping(self, connection_id: str) -> bool:
        """
        Handle ping message to keep connection alive.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            True if ping was handled successfully
        """
        if connection_id not in self.connection_metadata:
            return False
        
        # Update last activity
        self.connection_metadata[connection_id]["last_activity"] = datetime.utcnow()
        
        # Send pong response
        websocket = self.connection_metadata[connection_id]["websocket"]
        try:
            pong_message = {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(pong_message))
            return True
        except Exception as e:
            logger.error(f"Failed to send pong to connection {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def cleanup_stale_connections(self, timeout_minutes: int = 30) -> int:
        """
        Clean up stale connections that haven't been active.
        
        Args:
            timeout_minutes: Minutes of inactivity before considering connection stale
            
        Returns:
            Number of connections cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stale_connections = []
        
        for connection_id, metadata in self.connection_metadata.items():
            if metadata["last_activity"] < cutoff_time:
                stale_connections.append(connection_id)
        
        # Disconnect stale connections
        for connection_id in stale_connections:
            await self.disconnect(connection_id)
        
        logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")
        return len(stale_connections)

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.
        
        Returns:
            Connection statistics
        """
        total_connections = len(self.connection_metadata)
        unique_users = len(self.user_connections)
        active_projects = len(self.project_subscriptions)
        
        # Calculate connections per project
        project_stats = {}
        for project_id, connections in self.project_subscriptions.items():
            project_stats[project_id] = len(connections)
        
        return {
            "total_connections": total_connections,
            "unique_users": unique_users,
            "active_projects": active_projects,
            "project_stats": project_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _update_user_presence(
        self, 
        user_id: str, 
        project_id: Optional[str], 
        status: UserPresenceStatus
    ):
        """Update user presence in database."""
        try:
            # Get database session
            async for db in get_db():
                presence_service = PresenceService(db)
                
                presence_data = UserPresenceCreate(
                    status=status,
                    project_id=project_id,
                    session_id=f"ws_{user_id}_{datetime.utcnow().timestamp()}",
                    metadata={"connection_type": "websocket"}
                )
                
                await presence_service.update_presence(user_id, presence_data)
                break
        except Exception as e:
            logger.error(f"Failed to update user presence: {e}")

    async def _broadcast_user_status_change(
        self, 
        user_id: str, 
        project_id: str, 
        status: str
    ):
        """Broadcast user status change to project members."""
        message = {
            "type": "user_status_change",
            "data": {
                "user_id": user_id,
                "status": status,
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.broadcast_to_project(project_id, message, exclude_user=user_id)

    async def publish_to_redis(self, channel: str, message: Dict[str, Any]):
        """
        Publish message to Redis for cross-instance communication.
        
        Args:
            channel: Redis channel
            message: Message to publish
        """
        try:
            redis = await get_redis()
            await redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to publish to Redis channel {channel}: {e}")

    async def subscribe_to_redis(self, channel: str):
        """
        Subscribe to Redis channel for cross-instance communication.
        
        Args:
            channel: Redis channel to subscribe to
        """
        try:
            redis = await get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._handle_redis_message(data)
                    except Exception as e:
                        logger.error(f"Failed to handle Redis message: {e}")
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis channel {channel}: {e}")

    async def _handle_redis_message(self, message: Dict[str, Any]):
        """Handle message received from Redis."""
        message_type = message.get("type")
        
        if message_type == "broadcast_to_project":
            project_id = message.get("project_id")
            data = message.get("data")
            exclude_user = message.get("exclude_user")
            
            if project_id and data:
                await self.broadcast_to_project(project_id, data, exclude_user)
        
        elif message_type == "send_to_user":
            user_id = message.get("user_id")
            data = message.get("data")
            
            if user_id and data:
                await self.send_personal_message(user_id, data)


# Global connection manager instance
connection_manager = ConnectionManager()


# Background task to clean up stale connections
async def cleanup_stale_connections_task():
    """Background task to periodically clean up stale connections."""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            await connection_manager.cleanup_stale_connections()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


# Start cleanup task when module is imported
asyncio.create_task(cleanup_stale_connections_task())