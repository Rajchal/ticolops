"""Advanced presence management service with heartbeat and idle detection."""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import get_redis
from app.services.activity import PresenceService
from app.services.websocket_pubsub import notify_presence_update_instances
from app.schemas.activity import (
    UserPresenceCreate, UserPresenceUpdate, UserPresenceStatus, ActivityType
)
from app.models.activity import UserPresence
from app.models.user import User

logger = logging.getLogger(__name__)


class PresenceManager:
    """Advanced presence manager with heartbeat system and idle detection."""

    def __init__(self):
        # Active user sessions: {user_id: session_data}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        # User heartbeats: {user_id: last_heartbeat_time}
        self.user_heartbeats: Dict[str, datetime] = {}
        # Project presence: {project_id: {user_id: presence_data}}
        self.project_presence: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Status change callbacks: {callback_id: callback_function}
        self.status_callbacks: Dict[str, Callable] = {}
        # Idle detection settings
        self.idle_threshold_minutes = 5
        self.offline_threshold_minutes = 15
        # Background tasks
        self._heartbeat_task = None
        self._cleanup_task = None
        self._is_running = False

    async def start(self):
        """Start the presence manager background tasks."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_presence())
        
        logger.info("Presence manager started")

    async def stop(self):
        """Stop the presence manager background tasks."""
        self._is_running = False
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        logger.info("Presence manager stopped")

    async def register_user_session(
        self, 
        user_id: str, 
        session_id: str,
        project_id: Optional[str] = None,
        initial_status: UserPresenceStatus = UserPresenceStatus.ONLINE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new user session.
        
        Args:
            user_id: User ID
            session_id: Unique session ID
            project_id: Optional project ID
            initial_status: Initial presence status
            metadata: Optional session metadata
            
        Returns:
            Session data
        """
        now = datetime.utcnow()
        
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "project_id": project_id,
            "status": initial_status.value,
            "current_location": None,
            "current_activity": None,
            "started_at": now,
            "last_activity": now,
            "last_heartbeat": now,
            "metadata": metadata or {}
        }
        
        # Store session
        self.active_sessions[user_id] = session_data
        self.user_heartbeats[user_id] = now
        
        # Update project presence
        if project_id:
            if project_id not in self.project_presence:
                self.project_presence[project_id] = {}
            self.project_presence[project_id][user_id] = session_data.copy()
        
        # Update database
        await self._update_database_presence(user_id, project_id, {
            "status": initial_status,
            "session_id": session_id,
            "metadata": metadata or {}
        })
        
        # Broadcast presence update
        await self._broadcast_presence_change(user_id, project_id, session_data)
        
        logger.info(f"User session registered: user={user_id}, project={project_id}")
        return session_data

    async def unregister_user_session(self, user_id: str):
        """
        Unregister a user session.
        
        Args:
            user_id: User ID
        """
        if user_id not in self.active_sessions:
            return
        
        session_data = self.active_sessions[user_id]
        project_id = session_data.get("project_id")
        
        # Remove from active sessions
        del self.active_sessions[user_id]
        if user_id in self.user_heartbeats:
            del self.user_heartbeats[user_id]
        
        # Remove from project presence
        if project_id and project_id in self.project_presence:
            if user_id in self.project_presence[project_id]:
                del self.project_presence[project_id][user_id]
            if not self.project_presence[project_id]:
                del self.project_presence[project_id]
        
        # Update database to offline
        await self._update_database_presence(user_id, project_id, {
            "status": UserPresenceStatus.OFFLINE
        })
        
        # Broadcast offline status
        offline_data = session_data.copy()
        offline_data["status"] = UserPresenceStatus.OFFLINE.value
        await self._broadcast_presence_change(user_id, project_id, offline_data)
        
        logger.info(f"User session unregistered: user={user_id}")

    async def update_user_presence(
        self, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update user presence information.
        
        Args:
            user_id: User ID
            updates: Updates to apply
            
        Returns:
            Updated session data or None if user not found
        """
        if user_id not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[user_id]
        project_id = session_data.get("project_id")
        
        # Apply updates
        for key, value in updates.items():
            if key in ["status", "current_location", "current_activity", "metadata"]:
                session_data[key] = value
        
        # Update last activity
        session_data["last_activity"] = datetime.utcnow()
        
        # Update project presence
        if project_id and project_id in self.project_presence:
            if user_id in self.project_presence[project_id]:
                self.project_presence[project_id][user_id].update(session_data)
        
        # Update database
        await self._update_database_presence(user_id, project_id, updates)
        
        # Broadcast presence update
        await self._broadcast_presence_change(user_id, project_id, session_data)
        
        return session_data

    async def heartbeat(self, user_id: str, activity_data: Optional[Dict[str, Any]] = None):
        """
        Process user heartbeat to maintain active status.
        
        Args:
            user_id: User ID
            activity_data: Optional activity data
        """
        now = datetime.utcnow()
        
        # Update heartbeat
        self.user_heartbeats[user_id] = now
        
        # Update session if exists
        if user_id in self.active_sessions:
            session_data = self.active_sessions[user_id]
            session_data["last_heartbeat"] = now
            session_data["last_activity"] = now
            
            # Update activity data if provided
            if activity_data:
                if "location" in activity_data:
                    session_data["current_location"] = activity_data["location"]
                if "activity_type" in activity_data:
                    session_data["current_activity"] = activity_data["activity_type"]
                if "metadata" in activity_data:
                    session_data["metadata"].update(activity_data["metadata"])
            
            # Ensure user is marked as active if they were idle
            if session_data["status"] in [UserPresenceStatus.AWAY.value, UserPresenceStatus.OFFLINE.value]:
                await self.update_user_presence(user_id, {"status": UserPresenceStatus.ACTIVE.value})

    async def get_user_presence(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current user presence.
        
        Args:
            user_id: User ID
            
        Returns:
            User presence data or None
        """
        return self.active_sessions.get(user_id)

    async def get_project_presence(self, project_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all user presence for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project presence data
        """
        return self.project_presence.get(project_id, {})

    async def get_online_users(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get currently online users.
        
        Args:
            project_id: Optional project ID filter
            
        Returns:
            List of online users
        """
        online_users = []
        
        if project_id:
            # Get users for specific project
            project_users = self.project_presence.get(project_id, {})
            for user_data in project_users.values():
                if user_data["status"] in [UserPresenceStatus.ONLINE.value, UserPresenceStatus.ACTIVE.value]:
                    online_users.append(user_data)
        else:
            # Get all online users
            for user_data in self.active_sessions.values():
                if user_data["status"] in [UserPresenceStatus.ONLINE.value, UserPresenceStatus.ACTIVE.value]:
                    online_users.append(user_data)
        
        return online_users

    async def get_user_activity_summary(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get user activity summary.
        
        Args:
            user_id: User ID
            hours: Hours to look back
            
        Returns:
            Activity summary
        """
        if user_id not in self.active_sessions:
            return {"status": "offline", "summary": "User not active"}
        
        session_data = self.active_sessions[user_id]
        now = datetime.utcnow()
        
        # Calculate session duration
        session_duration = now - session_data["started_at"]
        
        # Calculate time since last activity
        time_since_activity = now - session_data["last_activity"]
        
        return {
            "user_id": user_id,
            "status": session_data["status"],
            "current_location": session_data["current_location"],
            "current_activity": session_data["current_activity"],
            "session_duration_minutes": int(session_duration.total_seconds() / 60),
            "time_since_last_activity_minutes": int(time_since_activity.total_seconds() / 60),
            "project_id": session_data.get("project_id"),
            "metadata": session_data.get("metadata", {})
        }

    def register_status_callback(self, callback_id: str, callback: Callable):
        """
        Register a callback for status changes.
        
        Args:
            callback_id: Unique callback ID
            callback: Callback function
        """
        self.status_callbacks[callback_id] = callback

    def unregister_status_callback(self, callback_id: str):
        """
        Unregister a status callback.
        
        Args:
            callback_id: Callback ID to remove
        """
        if callback_id in self.status_callbacks:
            del self.status_callbacks[callback_id]

    async def _heartbeat_monitor(self):
        """Background task to monitor user heartbeats and detect idle/offline users."""
        while self._is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._check_user_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")

    async def _check_user_status(self):
        """Check user status based on heartbeats and update accordingly."""
        now = datetime.utcnow()
        idle_threshold = timedelta(minutes=self.idle_threshold_minutes)
        offline_threshold = timedelta(minutes=self.offline_threshold_minutes)
        
        users_to_update = []
        
        for user_id, session_data in self.active_sessions.items():
            last_heartbeat = self.user_heartbeats.get(user_id, session_data["last_activity"])
            time_since_heartbeat = now - last_heartbeat
            current_status = session_data["status"]
            
            new_status = None
            
            # Determine new status based on time since last heartbeat
            if time_since_heartbeat >= offline_threshold:
                if current_status != UserPresenceStatus.OFFLINE.value:
                    new_status = UserPresenceStatus.OFFLINE.value
            elif time_since_heartbeat >= idle_threshold:
                if current_status not in [UserPresenceStatus.AWAY.value, UserPresenceStatus.OFFLINE.value]:
                    new_status = UserPresenceStatus.AWAY.value
            else:
                if current_status in [UserPresenceStatus.AWAY.value, UserPresenceStatus.OFFLINE.value]:
                    new_status = UserPresenceStatus.ACTIVE.value
            
            if new_status:
                users_to_update.append((user_id, new_status))
        
        # Update user statuses
        for user_id, new_status in users_to_update:
            await self.update_user_presence(user_id, {"status": new_status})
            logger.debug(f"Updated user status: user={user_id}, status={new_status}")

    async def _cleanup_stale_presence(self):
        """Background task to clean up stale presence data."""
        while self._is_running:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                await self._cleanup_offline_users()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _cleanup_offline_users(self):
        """Remove users who have been offline for too long."""
        now = datetime.utcnow()
        cleanup_threshold = timedelta(hours=1)  # Remove after 1 hour offline
        
        users_to_remove = []
        
        for user_id, session_data in self.active_sessions.items():
            if session_data["status"] == UserPresenceStatus.OFFLINE.value:
                time_offline = now - session_data["last_activity"]
                if time_offline >= cleanup_threshold:
                    users_to_remove.append(user_id)
        
        # Remove stale users
        for user_id in users_to_remove:
            await self.unregister_user_session(user_id)
            logger.info(f"Cleaned up stale user session: user={user_id}")

    async def _update_database_presence(
        self, 
        user_id: str, 
        project_id: Optional[str], 
        updates: Dict[str, Any]
    ):
        """Update user presence in database."""
        try:
            # In DEBUG mode we avoid writing presence to the database to keep the
            # local demo simple (avoids requiring migrations/tables).
            if settings.DEBUG:
                return
            async for db in get_db():
                presence_service = PresenceService(db)
                
                # Convert status enum if needed
                if "status" in updates and isinstance(updates["status"], UserPresenceStatus):
                    updates["status"] = updates["status"]
                
                presence_data = UserPresenceCreate(
                    status=updates.get("status", UserPresenceStatus.ONLINE),
                    project_id=project_id,
                    current_location=updates.get("current_location"),
                    current_activity=updates.get("current_activity"),
                    session_id=updates.get("session_id"),
                    metadata=updates.get("metadata", {})
                )
                
                await presence_service.update_presence(user_id, presence_data)
                break
        except Exception as e:
            logger.error(f"Failed to update database presence: {e}")

    async def _broadcast_presence_change(
        self, 
        user_id: str, 
        project_id: Optional[str], 
        presence_data: Dict[str, Any]
    ):
        """Broadcast presence change to other instances and trigger callbacks."""
        try:
            # Notify other instances via Redis
            await notify_presence_update_instances(user_id, project_id, presence_data)
            
            # Trigger local callbacks
            for callback in self.status_callbacks.values():
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(user_id, project_id, presence_data)
                    else:
                        callback(user_id, project_id, presence_data)
                except Exception as e:
                    logger.error(f"Error in presence callback: {e}")
        
        except Exception as e:
            logger.error(f"Failed to broadcast presence change: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get presence manager statistics."""
        now = datetime.utcnow()
        
        # Count users by status
        status_counts = {}
        for session_data in self.active_sessions.values():
            status = session_data["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count users by project
        project_counts = {}
        for session_data in self.active_sessions.values():
            project_id = session_data.get("project_id")
            if project_id:
                project_counts[project_id] = project_counts.get(project_id, 0) + 1
        
        # Calculate average session duration
        total_duration = 0
        session_count = len(self.active_sessions)
        
        for session_data in self.active_sessions.values():
            duration = now - session_data["started_at"]
            total_duration += duration.total_seconds()
        
        avg_session_duration = total_duration / session_count if session_count > 0 else 0
        
        return {
            "total_active_sessions": session_count,
            "status_distribution": status_counts,
            "project_distribution": project_counts,
            "average_session_duration_minutes": int(avg_session_duration / 60),
            "idle_threshold_minutes": self.idle_threshold_minutes,
            "offline_threshold_minutes": self.offline_threshold_minutes,
            "is_running": self._is_running,
            "timestamp": now.isoformat()
        }


# Global presence manager instance
presence_manager = PresenceManager()


# Convenience functions

async def start_presence_manager():
    """Start the global presence manager."""
    await presence_manager.start()


async def stop_presence_manager():
    """Stop the global presence manager."""
    await presence_manager.stop()


async def register_user_online(
    user_id: str, 
    session_id: str, 
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Register user as online."""
    return await presence_manager.register_user_session(
        user_id, session_id, project_id, UserPresenceStatus.ONLINE, metadata
    )


async def register_user_offline(user_id: str):
    """Register user as offline."""
    await presence_manager.unregister_user_session(user_id)


async def update_user_activity(
    user_id: str, 
    location: Optional[str] = None,
    activity_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Update user activity and send heartbeat."""
    activity_data = {}
    if location:
        activity_data["location"] = location
    if activity_type:
        activity_data["activity_type"] = activity_type
    if metadata:
        activity_data["metadata"] = metadata
    
    await presence_manager.heartbeat(user_id, activity_data)


async def get_project_online_users(project_id: str) -> List[Dict[str, Any]]:
    """Get online users for a project."""
    return await presence_manager.get_online_users(project_id)


async def get_user_status(user_id: str) -> Optional[Dict[str, Any]]:
    """Get current user status."""
    return await presence_manager.get_user_presence(user_id)