"""
Rate Limiter Middleware
Implements per-IP rate limiting for API endpoints.
"""
import os
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger


class RateLimiter:
    """Simple in-memory rate limiter (production should use Redis)."""
    
    def __init__(self):
        self.requests_per_minute = int(os.getenv('RATE_LIMIT_PER_MINUTE', '100'))
        self.burst_size = int(os.getenv('RATE_LIMIT_BURST', '20'))
        self.exempt_paths = os.getenv('RATE_LIMIT_EXEMPT', '/health,/metrics,/docs').split(',')
        
        # In-memory store: {ip_address: [(timestamp, count)]}
        self.request_log: Dict[str, list] = {}
        self.cleanup_interval = 300  # Cleanup old entries every 5 minutes
        self.last_cleanup = time.time()

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        return any(path.startswith(exempt.strip()) for exempt in self.exempt_paths)

    def check_rate_limit(self, client_ip: str) -> tuple[bool, Optional[int]]:
        """
        Check if client is within rate limits.
        
        Returns:
            (allowed, retry_after_seconds)
        """
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup(current_time)
            self.last_cleanup = current_time

        # Get or initialize client's request log
        if client_ip not in self.request_log:
            self.request_log[client_ip] = []
        
        # Remove requests older than 1 minute
        minute_ago = current_time - 60
        self.request_log[client_ip] = [
            req for req in self.request_log[client_ip] 
            if req[0] > minute_ago
        ]
        
        # Check rate limit
        request_count = len(self.request_log[client_ip])
        
        if request_count >= self.requests_per_minute:
            # Calculate retry after time (when oldest request will expire)
            if self.request_log[client_ip]:
                oldest_request = min(req[0] for req in self.request_log[client_ip])
                retry_after = int(oldest_request + 60 - current_time) + 1
                return False, retry_after
            return False, 60
        
        # Add current request
        self.request_log[client_ip].append((current_time, request_count + 1))
        
        return True, None

    def _cleanup(self, current_time: float):
        """Clean up old entries from request log."""
        minute_ago = current_time - 60
        for ip in list(self.request_log.keys()):
            self.request_log[ip] = [
                req for req in self.request_log[ip] 
                if req[0] > minute_ago
            ]
            # Remove empty entries
            if not self.request_log[ip]:
                del self.request_log[ip]

    def get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"


# Singleton rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting.
    """
    # Check if path is exempt
    if rate_limiter.is_exempt(request.url.path):
        return await call_next(request)
    
    # Get client IP
    client_ip = rate_limiter.get_client_ip(request)
    
    # Check rate limit
    allowed, retry_after = rate_limiter.check_rate_limit(client_ip)
    
    if not allowed:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Too many requests. Please try again in {retry_after} seconds.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = rate_limiter.requests_per_minute - len(rate_limiter.request_log.get(client_ip, []))
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    
    return response
