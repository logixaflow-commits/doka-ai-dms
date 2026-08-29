"""
Rule Trigger Middleware - Triggers rules on document events
Intercepts document events and executes matching automation rules.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.services.rule_manager_service import rule_manager_service
from app.services.rule_engine import rule_engine


class RuleTriggerMiddleware(BaseHTTPMiddleware):
    """Middleware to trigger rules on document events."""

    async def dispatch(self, request: Request, call_next):
        # Process request first
        response = await call_next(request)
        
        # Only trigger rules on successful document updates
        path = request.url.path
        
        # Trigger on document approval, rejection, or creation
        trigger_paths = [
            '/api/documents',  # POST (creation)
            '/api/documents/',  # PUT (update)
        ]
        
        if any(trigger_path in path for trigger_path in trigger_paths):
            if response.status_code == 200:
                try:
                    # Extract document info from response or request
                    # In production, you'd parse the response body
                    await self._trigger_rules(request)
                except Exception as e:
                    logger.error(f"Failed to trigger rules: {e}")
        
        return response

    async def _trigger_rules(self, request: Request):
        """Trigger rules for the request."""
        # In production, this would:
        # 1. Extract document data from request/response
        # 2. Evaluate rules against the data
        # 3. Execute matching rule actions
        # 4. Log rule execution
        pass  # Placeholder - would need full implementation


# Alternative: Decorator-based approach for rule triggering
def trigger_rules_on_event(event_type: str):
    """
    Decorator to trigger rules on specific events.
    
    Args:
        event_type: Type of event (create, update, approve, reject)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Trigger rules after successful execution
            try:
                # Extract document from kwargs or result
                # Process against rules
                pass  # Placeholder
            except Exception as e:
                logger.error(f"Failed to trigger rules on {event_type}: {e}")
            
            return result
        return wrapper
    return decorator