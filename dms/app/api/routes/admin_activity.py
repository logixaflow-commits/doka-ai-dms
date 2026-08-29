"""
Office DMS - Admin Activity Routes
Endpoints for user activity analysis and heatmap visualization.
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_

from app.core.database import get_db
from app.core.security import require_admin
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/activity/heatmap")
async def get_activity_heatmap(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get user activity data for heatmap visualization.
    Returns activity counts grouped by hour and day.
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query audit logs to get activity data
        # Group by user, day of week, and hour
        activity_data = db.query(
            AuditLog.user_id,
            func.extract('dow', AuditLog.created_at).label('day_of_week'),  # 0 = Monday, 6 = Sunday
            func.extract('hour', AuditLog.created_at).label('hour'),
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date
        ).group_by(
            AuditLog.user_id,
            extract('dow', AuditLog.created_at),
            extract('hour', AuditLog.created_at)
        ).all()
        
        # Reorganize by user
        heatmap_data = {}
        for row in activity_data:
            user_id = row[0]
            day_of_week = int(row[1])  # 0 = Monday, 6 = Sunday
            hour = int(row[2])
            count = row[3]
            
            if user_id not in heatmap_data:
                heatmap_data[user_id] = {}
            
            # Initialize 7 days x 24 hours grid (if not present)
            if 'activity_grid' not in heatmap_data[user_id]:
                heatmap_data[user_id]['activity_grid'] = {}
                for d in range(7):
                    heatmap_data[user_id]['activity_grid'][d] = {}
                    for h in range(24):
                        heatmap_data[user_id]['activity_grid'][d][h] = 0
            
            heatmap_data[user_id]['activity_grid'][day_of_week][hour] = count
        
        # Get user information
        users = db.query(
            AuditLog.user_id,
            User.username,
            User.full_name
        ).join(
            User, AuditLog.user_id == User.id
        ).distinct().all()
        
        user_info = {
            user[0]: {
                'username': user[1],
                'full_name': user[2] or user[1]
            }
            for user in users
        }
        
        # Calculate statistics
        total_activity = sum(row[3] for row in activity_data)
        peak_hour_data = db.query(
            extract('hour', AuditLog.created_at).label('hour'),
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date
        ).group_by(extract('hour', AuditLog.created_at)).order_by(
            func.count(AuditLog.id).desc()
        ).first()
        
        peak_hour = peak_hour_data[0] if peak_hour_data else 12
        peak_hour_count = peak_hour_data[1] if peak_hour_data else 0
        
        logger.info(f"Activity heatmap generated for {len(heatmap_data)} users over {days} days")
        
        return {
            'heatmap_data': heatmap_data,
            'user_info': user_info,
            'statistics': {
                'total_activity': total_activity,
                'peak_hour': peak_hour,
                'peak_hour_count': peak_hour_count,
                'period_days': days,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'users_count': len(user_info)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to generate activity heatmap: {e}")
        return {
            'heatmap_data': {},
            'user_info': {},
            'statistics': {
                'total_activity': 0,
                'peak_hour': 12,
                'peak_hour_count': 0,
                'period_days': days,
                'start_date': '',
                'end_date': '',
                'users_count': 0
            }
        }


@router.get("/activity/summary")
async def get_activity_summary(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get activity summary grouped by user and action type.
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query audit logs grouped by user and action
        user_activity = db.query(
            AuditLog.user_id,
            User.username,
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).join(
            User, AuditLog.user_id == User.id
        ).filter(
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date
        ).group_by(
            AuditLog.user_id,
            User.username,
            AuditLog.action
        ).order_by(func.count(AuditLog.id).desc()).all()
        
        # Organize by user
        user_stats = {}
        for row in user_activity:
            user_id = row[0]
            username = row[1]
            action = row[2]
            count = row[3]
            
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'username': username,
                    'total_actions': 0,
                    'actions': {}
                }
            
            user_stats[user_id]['total_actions'] += count
            user_stats[user_id]['actions'][action] = count
        
        logger.info(f"Activity summary generated for {days} days")
        
        return {
            'user_activity': list(user_stats.values()),
            'total_users': len(user_stats),
            'period_days': days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        logger.error(f"Failed to get activity summary: {e}")
        return {
            'user_activity': [],
            'total_users': 0,
            'period_days': days,
            'start_date': '',
            'end_date': ''
        }