"""Redis pub/sub service for WebSocket cross-instance communication."""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from app.core.redis import get_redis
from app.core.websocket import connection_manager

logger = logging.getLogger(__name__)


class WebSocketPubSubService:
    """Service for handling WebSocket pub/sub communication via Redis."""

    def __init__(self):
        self.redis = None
        self.pubsub = None
        self.subscriptions: Dict[str, Callable] = {}
        self.is_listening = False

    async def initialize(self):
        """Initialize Redis connection and pub/sub."""
        try:
            self.redis = await get_redis()
            self.pubsub = self.redis.pubsub()
            logger.info("WebSocket pub/sub service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket pub/sub service: {e}")
            raise

    async def subscribe_to_channels(self):
        """Subscribe to WebSocket-related Redis channels."""
        channels = [
            "websocket:broadcast",
            "websocket:project_broadcast",
            "websocket:user_message",
            "websocket:presence_update",
            "websocket:activity_update"
        ]
        
        try:
            await self.pubsub.subscribe(*channels)
            logger.info(f"Subscribed to WebSocket channels: {channels}")
        except Exception as e:
            logger.error(f"Failed to subscribe to WebSocket channels: {e}")
            raise

    async def start_listening(self):
        """Start listening for Redis pub/sub messages."""
        if self.is_listening:
            return
        
        self.is_listening = True
        logger.info("Starting WebSocket pub/sub listener")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_redis_message(message)
        except Exception as e:
            logger.error(f"Error in WebSocket pub/sub listener: {e}")
        finally:
            self.is_listening = False

    async def stop_listening(self):
        """Stop listening for Redis pub/sub messages."""
        self.is_listening = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        logger.info("Stopped WebSocket pub/sub listener")

    async def publish_broadcast_message(self, message: Dict[str, Any]):
        """
        Publish a broadcast message to all WebSocket instances.
        
        Args:
            message: Message to broadcast
        """
        try:
            payload = {
                "type": "broadcast_all",
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "instance_id": self._get_instance_id()
            }
            
            await self.redis.publish("websocket:broadcast", json.dumps(payload))
            logger.debug("Published broadcast message to Redis")
        except Exception as e:
            logger.error(f"Failed to publish broadcast message: {e}")

    async def publish_project_message(
        self, 
        project_id: str, 
        message: Dict[str, Any], 
        exclude_user: Optional[str] = None
    ):
        """
        Publish a message to all instances for a specific project.
        
        Args:
            project_id: Target project ID
            message: Message to send
            exclude_user: Optional user ID to exclude
        """
        try:
            payload = {
                "type": "project_broadcast",
                "project_id": project_id,
                "message": message,
                "exclude_user": exclude_user,
                "timestamp": datetime.utcnow().isoformat(),
                "instance_id": self._get_instance_id()
            }
            
            await self.redis.publish("websocket:project_broadcast", json.dumps(payload))
            logger.debug(f"Published project message to Redis: project={project_id}")
        except Exception as e:
            logger.error(f"Failed to publish project message: {e}")

    async def publish_user_message(self, user_id: str, message: Dict[str, Any]):
        """
        Publish a message to all instances for a specific user.
        
        Args:
            user_id: Target user ID
            message: Message to send
        """
        try:
            payload = {
                "type": "user_message",
                "user_id": user_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "instance_id": self._get_instance_id()
            }
            
            await self.redis.publish("websocket:user_message", json.dumps(payload))
            logger.debug(f"Published user message to Redis: user={user_id}")
        except Exception as e:
            logger.error(f"Failed to publish user message: {e}")

    async def publish_presence_update(
        self, 
        user_id: str, 
        project_id: Optional[str], 
        presence_data: Dict[str, Any]
    ):
        """
        Publish a presence update to all instances.
        
        Args:
            user_id: User ID
            project_id: Optional project ID
            presence_data: Presence data
        """
        try:
            payload = {
                "type": "presence_update",
                "user_id": user_id,
                "project_id": project_id,
                "presence_data": presence_data,
                "timestamp": datetime.utcnow().isoformat(),
                "instance_id": self._get_instance_id()
            }
            
            await self.redis.publish("websocket:presence_update", json.dumps(payload))
            logger.debug(f"Published presence update to Redis: user={user_id}")
        except Exception as e:
            logger.error(f"Failed to publish presence update: {e}")

    async def publish_activity_update(
        self, 
        user_id: str, 
        project_id: Optional[str], 
        activity_data: Dict[str, Any]
    ):
        """
        Publish an activity update to all instances.
        
        Args:
            user_id: User ID
            project_id: Optional project ID
            activity_data: Activity data
        """
        try:
            payload = {
                "type": "activity_update",
                "user_id": user_id,
                "project_id": project_id,
                "activity_data": activity_data,
                "timestamp": datetime.utcnow().isoformat(),
                "instance_id": self._get_instance_id()
            }
            
            await self.redis.publish("websocket:activity_update", json.dumps(payload))
            logger.debug(f"Published activity update to Redis: user={user_id}")
        except Exception as e:
            logger.error(f"Failed to publish activity update: {e}")

    async def _handle_redis_message(self, message):
        """Handle incoming Redis pub/sub message."""
        try:
            channel = message["channel"].decode("utf-8")
            data = json.loads(message["data"].decode("utf-8"))
            
            # Skip messages from this instance to avoid loops
            if data.get("instance_id") == self._get_instance_id():
                return
            
            message_type = data.get("type")
            logger.debug(f"Handling Redis message: channel={channel}, type={message_type}")
            
            if channel == "websocket:broadcast":
                await self._handle_broadcast_message(data)
            elif channel == "websocket:project_broadcast":
                await self._handle_project_broadcast_message(data)
            elif channel == "websocket:user_message":
                await self._handle_user_message(data)
            elif channel == "websocket:presence_update":
                await self._handle_presence_update_message(data)
            elif channel == "websocket:activity_update":
                await self._handle_activity_update_message(data)
            else:
                logger.warning(f"Unknown Redis channel: {channel}")
                
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _handle_broadcast_message(self, data: Dict[str, Any]):
        """Handle broadcast message from Redis."""
        message = data.get("message")
        if message:
            await connection_manager.broadcast_to_all(message)

    async def _handle_project_broadcast_message(self, data: Dict[str, Any]):
        """Handle project broadcast message from Redis."""
        project_id = data.get("project_id")
        message = data.get("message")
        exclude_user = data.get("exclude_user")
        
        if project_id and message:
            await connection_manager.broadcast_to_project(project_id, message, exclude_user)

    async def _handle_user_message(self, data: Dict[str, Any]):
        """Handle user message from Redis."""
        user_id = data.get("user_id")
        message = data.get("message")
        
        if user_id and message:
            await connection_manager.send_personal_message(user_id, message)

    async def _handle_presence_update_message(self, data: Dict[str, Any]):
        """Handle presence update message from Redis."""
        user_id = data.get("user_id")
        project_id = data.get("project_id")
        presence_data = data.get("presence_data")
        
        if user_id and presence_data:
            # Broadcast presence update to project members
            if project_id:
                message = {
                    "type": "presence_update",
                    "data": {
                        "user_id": user_id,
                        "project_id": project_id,
                        **presence_data
                    }
                }
                await connection_manager.broadcast_to_project(project_id, message, exclude_user=user_id)

    async def _handle_activity_update_message(self, data: Dict[str, Any]):
        """Handle activity update message from Redis."""
        user_id = data.get("user_id")
        project_id = data.get("project_id")
        activity_data = data.get("activity_data")
        
        if user_id and activity_data:
            # Broadcast activity update to project members
            if project_id:
                message = {
                    "type": "user_activity_update",
                    "data": {
                        "user_id": user_id,
                        "project_id": project_id,
                        **activity_data
                    }
                }
                await connection_manager.broadcast_to_project(project_id, message, exclude_user=user_id)

    def _get_instance_id(self) -> str:
        """Get unique instance ID to avoid message loops."""
        import os
        import socket
        
        # Use hostname + process ID as instance identifier
        hostname = socket.gethostname()
        pid = os.getpid()
        return f"{hostname}:{pid}"

    async def get_stats(self) -> Dict[str, Any]:
        """Get pub/sub service statistics."""
        try:
            # Get Redis info
            redis_info = await self.redis.info()
            
            return {
                "is_listening": self.is_listening,
                "instance_id": self._get_instance_id(),
                "redis_connected": self.redis is not None,
                "pubsub_active": self.pubsub is not None,
                "redis_clients": redis_info.get("connected_clients", 0),
                "redis_memory_usage": redis_info.get("used_memory_human", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get pub/sub stats: {e}")
            return {
                "is_listening": self.is_listening,
                "instance_id": self._get_instance_id(),
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global pub/sub service instance
pubsub_service = WebSocketPubSubService()


async def initialize_websocket_pubsub():
    """Initialize WebSocket pub/sub service."""
    try:
        await pubsub_service.initialize()
        await pubsub_service.subscribe_to_channels()
        
        # Start listening in background task
        asyncio.create_task(pubsub_service.start_listening())
        
        logger.info("WebSocket pub/sub service started")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket pub/sub service: {e}")


async def shutdown_websocket_pubsub():
    """Shutdown WebSocket pub/sub service."""
    try:
        await pubsub_service.stop_listening()
        logger.info("WebSocket pub/sub service stopped")
    except Exception as e:
        logger.error(f"Error shutting down WebSocket pub/sub service: {e}")


# Convenience functions for publishing messages

async def broadcast_to_all_instances(message: Dict[str, Any]):
    """Broadcast message to all WebSocket instances."""
    await pubsub_service.publish_broadcast_message(message)


async def broadcast_to_project_instances(
    project_id: str, 
    message: Dict[str, Any], 
    exclude_user: Optional[str] = None
):
    """Broadcast message to all instances for a project."""
    await pubsub_service.publish_project_message(project_id, message, exclude_user)


async def send_to_user_instances(user_id: str, message: Dict[str, Any]):
    """Send message to all instances for a user."""
    await pubsub_service.publish_user_message(user_id, message)


async def notify_presence_update_instances(
    user_id: str, 
    project_id: Optional[str], 
    presence_data: Dict[str, Any]
):
    """Notify all instances of a presence update."""
    await pubsub_service.publish_presence_update(user_id, project_id, presence_data)


async def notify_activity_update_instances(
    user_id: str, 
    project_id: Optional[str], 
    activity_data: Dict[str, Any]
):
    """Notify all instances of an activity update."""
    await pubsub_service.publish_activity_update(user_id, project_id, activity_data)