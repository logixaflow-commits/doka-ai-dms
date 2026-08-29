"""
API Routes for Rate Limiting and Quotas
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import User
from app.services.rate_limiting import get_rate_limiting_service

router = APIRouter(prefix="/api/rate-limit", tags=["Rate Limiting"])


@router.get("/check")
async def check_rate_limit(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Check current rate limit status"""
    try:
        rate_limiting_service = get_rate_limiting_service()
        
        endpoint = str(request.url.path)
        result = rate_limiting_service.check_rate_limit(
            current_user.id,
            current_user.role,
            endpoint
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage")
async def get_usage_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get user API usage statistics"""
    try:
        from datetime import datetime
        
        rate_limiting_service = get_rate_limiting_service()
        
        # Parse dates
        parsed_date_from = None
        parsed_date_to = None
        
        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from)
        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to)
        
        result = rate_limiting_service.get_user_usage_stats(
            current_user.id,
            parsed_date_from,
            parsed_date_to
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota")
async def get_user_quota(
    current_user: User = Depends(get_current_user)
):
    """Get user quota status"""
    try:
        rate_limiting_service = get_rate_limiting_service()
        result = rate_limiting_service.check_user_quota(current_user.id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get user quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quota")
async def set_user_quota(
    user_id: int,
    daily_requests: int,
    daily_storage_mb: int,
    monthly_requests: int,
    monthly_storage_mb: int,
    current_user: User = Depends(get_current_user)
):
    """Set user quota (admin only)"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        rate_limiting_service = get_rate_limiting_service()
        quota = rate_limiting_service.set_user_quota(
            user_id,
            daily_requests,
            daily_storage_mb,
            monthly_requests,
            monthly_storage_mb
        )
        
        return {
            "success": True,
            "quota": {
                "user_id": quota.user_id,
                "daily_requests": quota.daily_requests,
                "daily_storage_mb": quota.daily_storage_mb,
                "monthly_requests": quota.monthly_requests,
                "monthly_storage_mb": quota.monthly_storage_mb,
                "reset_date": quota.reset_date.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set user quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))