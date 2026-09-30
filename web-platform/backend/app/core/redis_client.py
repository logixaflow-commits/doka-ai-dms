"""
Redis Client Module
Provides Redis connection for caching and rate limiting.
"""
import os
import redis
from loguru import logger

# Redis client instance (None if Redis is not available)
redis_client = None

def init_redis():
    """Initialize Redis connection if REDIS_URL is configured."""
    global redis_client
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        logger.info(f"✓ Redis connected: {redis_url}")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without Redis.")
        redis_client = None

# Initialize Redis on module import
init_redis()