"""
Office DMS - Analytics Routes
Endpoints for dashboard charts and business intelligence data.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.core.logging import get_logger, log_audit
from app.services.analytics import analytics_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_overview_analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get overview analytics for dashboard charts.
    Includes category distribution, status distribution, and source distribution.
    """
    try:
        data = analytics_service.get_overview_analytics(db, days=days)
        return data
    except Exception as e:
        logger.error(f"Failed to get overview analytics: {e}")
        raise


@router.get("/trends")
async def get_daily_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get daily upload trends for the last N days.
    Returns daily upload counts and 7-day moving average.
    """
    try:
        data = analytics_service.get_daily_trends(db, days=days)
        return data
    except Exception as e:
        logger.error(f"Failed to get daily trends: {e}")
        raise


@router.get("/category-trends")
async def get_category_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get daily trends broken down by category.
    Returns daily counts per category for trend analysis.
    """
    try:
        data = analytics_service.get_category_trends(db, days=days)
        return data
    except Exception as e:
        logger.error(f"Failed to get category trends: {e}")
        raise


@router.get("/expiry")
async def get_expiry_analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get analytics about expiring documents.
    Returns documents expiring soon, already expired, and statistics.
    """
    try:
        data = analytics_service.get_expiry_analytics(db, days=days)
        return data
    except Exception as e:
        logger.error(f"Failed to get expiry analytics: {e}")
        raise