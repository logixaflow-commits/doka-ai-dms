"""
Performance Optimization Module
Caching, connection pooling, and response optimization
"""
import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
from datetime import timedelta
import redis
from loguru import logger
from fastapi import Response
import gzip


class PerformanceConfig:
    """Performance configuration settings"""
    
    # Redis caching
    REDIS_URL = "redis://localhost:6379/0"
    CACHE_TTL = 3600  # 1 hour
    CACHE_PREFIX = "dms_cache:"
    
    # Database connection pooling
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30
    DB_POOL_RECYCLE = 3600
    
    # Response compression
    ENABLE_COMPRESSION = True
    COMPRESSION_LEVEL = 6
    COMPRESS_MIN_SIZE = 1024  # 1KB
    
    # Async operations
    MAX_CONCURRENT_REQUESTS = 100
    REQUEST_TIMEOUT = 30
    
    # Pagination
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500


class CacheManager:
    """Redis-based caching manager"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                PerformanceConfig.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.enabled = True
            logger.info("Cache connected to Redis")
        except Exception as e:
            logger.warning(f"Cache connection failed: {e}. Caching disabled.")
            self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            cached_value = self.redis_client.get(f"{PerformanceConfig.CACHE_PREFIX}{key}")
            if cached_value:
                return json.loads(cached_value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.enabled:
            return False
        
        try:
            cache_key = f"{PerformanceConfig.CACHE_PREFIX}{key}"
            cache_ttl = ttl or PerformanceConfig.CACHE_TTL
            serialized_value = json.dumps(value)
            self.redis_client.setex(cache_key, cache_ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.delete(f"{PerformanceConfig.CACHE_PREFIX}{key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(f"{PerformanceConfig.CACHE_PREFIX}{pattern}*")
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    def invalidate_all(self) -> bool:
        """Invalidate all cache"""
        if not self.enabled:
            return False
        
        try:
            keys = self.redis_client.keys(f"{PerformanceConfig.CACHE_PREFIX}*")
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache invalidate all error: {e}")
            return False


class ResponseOptimizer:
    """Response optimization for better performance"""
    
    @staticmethod
    def compress_response(content: str, min_size: int = 1024) -> tuple[bytes, bool]:
        """Compress response content"""
        if len(content) < min_size:
            return content.encode('utf-8'), False
        
        try:
            compressed = gzip.compress(content.encode('utf-8'), compresslevel=PerformanceConfig.COMPRESSION_LEVEL)
            if len(compressed) < len(content):
                return compressed, True
            return content.encode('utf-8'), False
        except Exception as e:
            logger.error(f"Compression error: {e}")
            return content.encode('utf-8'), False
    
    @staticmethod
    def optimize_headers(response: Response) -> Response:
        """Add performance-optimized headers"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


def cache_result(ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            
            # Generate cache key
            key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def async_cache_result(ttl: Optional[int] = None):
    """Decorator to cache async function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            
            # Generate cache key
            key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


class QueryOptimizer:
    """Database query optimization"""
    
    @staticmethod
    def optimize_select(query, columns: Optional[list] = None):
        """Optimize SELECT query"""
        if columns:
            query = query.with_entities(*columns)
        return query
    
    @staticmethod
    def add_pagination(query, page: int = 1, page_size: int = 50):
        """Add pagination to query"""
        page_size = min(page_size, PerformanceConfig.MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        return query.limit(page_size).offset(offset)
    
    @staticmethod
    def add_sorting(query, sort_by: str, sort_order: str = "asc"):
        """Add sorting to query"""
        order_column = getattr(query.column_descriptions[0]['type'], sort_by, None)
        if order_column:
            if sort_order == "desc":
                return query.order_by(order_column.desc())
            return query.order_by(order_column.asc())
        return query


# Singleton instances
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get singleton cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager