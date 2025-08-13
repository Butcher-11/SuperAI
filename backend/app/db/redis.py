import asyncio
import json
from typing import Optional, Any, Dict
import redis.asyncio as redis
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisManager:
    redis_client: Optional[redis.Redis] = None

redis_manager = RedisManager()

async def connect_to_redis():
    """Create Redis connection"""
    logger.info("Connecting to Redis...")
    redis_manager.redis_client = redis.from_url(
        settings.REDIS_URL, 
        decode_responses=True,
        socket_connect_timeout=30,
        socket_keepalive=True,
        socket_keepalive_options={},
        retry_on_timeout=True
    )
    
    # Test connection
    try:
        await redis_manager.redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

async def close_redis_connection():
    """Close Redis connection"""
    logger.info("Closing connection to Redis...")
    if redis_manager.redis_client:
        await redis_manager.redis_client.aclose()

def get_redis() -> redis.Redis:
    """Get Redis instance"""
    if not redis_manager.redis_client:
        raise Exception("Redis not connected")
    return redis_manager.redis_client

# Cache utilities
async def cache_set(key: str, value: Any, expire: int = 3600):
    """Set cache with expiration"""
    redis_client = get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await redis_client.set(key, value, ex=expire)

async def cache_get(key: str) -> Optional[Any]:
    """Get cache value"""
    redis_client = get_redis()
    value = await redis_client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None

async def cache_delete(key: str):
    """Delete cache key"""
    redis_client = get_redis()
    await redis_client.delete(key)

async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    redis_client = get_redis()
    return await redis_client.exists(key)

# Session management
async def store_session(session_id: str, data: Dict[str, Any], expire: int = 86400):
    """Store session data"""
    await cache_set(f"session:{session_id}", data, expire)

async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data"""
    return await cache_get(f"session:{session_id}")

async def delete_session(session_id: str):
    """Delete session"""
    await cache_delete(f"session:{session_id}")

# Rate limiting
async def check_rate_limit(key: str, limit: int, window: int) -> Dict[str, Any]:
    """Check rate limit using sliding window"""
    redis_client = get_redis()
    current_time = int(asyncio.get_event_loop().time())
    
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, current_time - window)
    pipe.zcard(key)
    pipe.zadd(key, {str(current_time): current_time})
    pipe.expire(key, window)
    
    results = await pipe.execute()
    current_requests = results[1]
    
    return {
        "allowed": current_requests < limit,
        "current_requests": current_requests,
        "limit": limit,
        "reset_time": current_time + window
    }