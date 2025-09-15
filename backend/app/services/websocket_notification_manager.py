"""Lightweight websocket notification manager stub for demo.

Provides a minimal interface used by notification triggers so the app can import
successfully in the demo environment. Real implementation would manage active
WebSocket connections and broadcast messages to connected clients.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class _NoOpManager:
    async def send_deployment_update(self, payload: Dict[str, Any], user_ids: List[str]):
        logger.debug("No-op send_deployment_update called", extra={"payload": payload, "user_ids": user_ids})

    async def send_activity_notification(self, payload: Dict[str, Any], user_ids: List[str]):
        logger.debug("No-op send_activity_notification called", extra={"payload": payload, "user_ids": user_ids})


notification_websocket_manager = _NoOpManager()
