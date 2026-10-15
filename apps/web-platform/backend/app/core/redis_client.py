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
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis connection failed: %s. Running without Redis.", type(e).__name__)
        redis_client = None

# Initialize Redis on module import
init_redis()