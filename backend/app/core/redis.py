"""
Redis configuration for caching and pub/sub messaging.
"""

import redis.asyncio as redis
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection pool."""
    global redis_pool, redis_client
    
    try:
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


async def close_redis():
    """Close Redis connections."""
    global redis_pool, redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
    
    logger.info("Redis connections closed")