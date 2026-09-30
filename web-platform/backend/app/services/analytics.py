"""
Office DMS - Analytics Service
Data aggregation for dashboard charts and business intelligence.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_

from app.core.logging import get_logger
from app.models.database import Document, AuditLog, User

logger = get_logger(__name__)


class AnalyticsService:
    """
    Service for aggregating analytics data for dashboard charts.
    Provides data for category distribution, status distribution, and trends.
    """

    def get_overview_analytics(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get overview analytics for the dashboard charts.
        
        Args:
            db: Database session
            days: Number of days to analyze
            
        Returns:
            Dictionary with category distribution, status distribution, and trends
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            # Category distribution (documents per category)
            category_data = db.query(
                Document.category,
                func.count(Document.id).label('count')
            ).filter(
                Document.created_at >= start_date,
                Document.category.isnot(None)
            ).group_by(Document.category).all()
            
            categories = {row[0]: row[1] for row in category_data}
            
            # Status distribution
            status_data = db.query(
                Document.status,
                func.count(Document.id).label('count')
            ).filter(Document.created_at >= start_date).group_by(Document.status).all()
            
            statuses = {row[0]: row[1] for row in status_data}
            
            # Source distribution
            source_data = db.query(
                Document.source,
                func.count(Document.id).label('count')
            ).filter(
                Document.created_at >= start_date,
                Document.source.isnot(None)
            ).group_by(Document.source).all()
            
            sources = {row[0]: row[1] for row in source_data}
            
            # Total statistics
            total_docs = db.query(func.count(Document.id)).filter(
                Document.created_at >= start_date
            ).scalar() or 0
            
            approved_docs = db.query(func.count(Document.id)).filter(
                Document.created_at >= start_date,
                Document.status == 'approved'
            ).scalar() or 0
            
            rejected_docs = db.query(func.count(Document.id)).filter(
                Document.created_at >= start_date,
                Document.status == 'rejected'
            ).scalar() or 0
            
            # Calculate approval rate
            approval_rate = (approved_docs / total_docs * 100) if total_docs > 0 else 0
            
            logger.info(f"Overview analytics computed for {days} days")
            
            return {
                'category_distribution': categories,
                'status_distribution': statuses,
                'source_distribution': sources,
                'statistics': {
                    'total_documents': total_docs,
                    'approved': approved_docs,
                    'rejected': rejected_docs,
                    'approval_rate': round(approval_rate, 2),
                    'period_days': days
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to compute overview analytics: {e}")
            return {
                'category_distribution': {},
                'status_distribution': {},
                'source_distribution': {},
                'statistics': {
                    'total_documents': 0,
                    'approved': 0,
                    'rejected': 0,
                    'approval_rate': 0,
                    'period_days': days
                }
            }

    def get_daily_trends(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get daily upload trends for the last N days.
        
        Args:
            db: Database session
            days: Number of days to analyze
            
        Returns:
            Dictionary with daily upload counts by date
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Query daily document counts
            daily_data = db.query(
                func.date(Document.created_at).label('date'),
                func.count(Document.id).label('count')
            ).filter(
                Document.created_at >= start_date,
                Document.created_at <= end_date
            ).group_by(func.date(Document.created_at)).order_by(func.date(Document.created_at)).all()
            
            # Fill missing days with zero
            trends = {}
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                trends[date_str] = 0
                current_date += timedelta(days=1)
            
            # Fill in actual data
            for row in daily_data:
                date_str = row[0].strftime('%Y-%m-%d') if row[0] else str(row[0])
                trends[date_str] = row[1]
            
            # Calculate moving average (7-day)
            sorted_dates = sorted(trends.keys())
            moving_average = {}
            
            for i in range(len(sorted_dates)):
                date_str = sorted_dates[i]
                if i >= 6:
                    recent_7_days = [trends[sorted_dates[j]] for j in range(i-6, i+1)]
                    moving_average[date_str] = round(sum(recent_7_days) / 7, 2)
                else:
                    moving_average[date_str] = trends[date_str]
            
            logger.info(f"Daily trends computed for {days} days")
            
            return {
                'daily_uploads': trends,
                'moving_average': moving_average,
                'total_uploads': sum(trends.values()),
                'period_days': days,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"Failed to compute daily trends: {e}")
            return {
                'daily_uploads': {},
                'moving_average': {},
                'total_uploads': 0,
                'period_days': days,
                'start_date': '',
                'end_date': ''
            }

    def get_category_trends(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get daily trends broken down by category.
        
        Args:
            db: Database session
            days: Number of days to analyze
            
        Returns:
            Dictionary with daily counts per category
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Query daily document counts by category
            category_trends = db.query(
                func.date(Document.created_at).label('date'),
                Document.category,
                func.count(Document.id).label('count')
            ).filter(
                Document.created_at >= start_date,
                Document.created_at <= end_date,
                Document.category.isnot(None)
            ).group_by(
                func.date(Document.created_at),
                Document.category
            ).order_by(func.date(Document.created_at)).all()
            
            # Organize by date and category
            trends_by_date = {}
            all_categories = set()
            
            for row in category_trends:
                date_str = row[0].strftime('%Y-%m-%d') if row[0] else str(row[0])
                category = row[1]
                count = row[2]
                
                if date_str not in trends_by_date:
                    trends_by_date[date_str] = {}
                
                trends_by_date[date_str][category] = count
                all_categories.add(category)
            
            # Fill missing dates and categories
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                if date_str not in trends_by_date:
                    trends_by_date[date_str] = {}
                
                for category in all_categories:
                    if category not in trends_by_date[date_str]:
                        trends_by_date[date_str][category] = 0
                
                current_date += timedelta(days=1)
            
            logger.info(f"Category trends computed for {days} days")
            
            return {
                'trends_by_date': trends_by_date,
                'categories': sorted(list(all_categories)),
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to compute category trends: {e}")
            return {
                'trends_by_date': {},
                'categories': [],
                'period_days': days
            }

    def get_expiry_analytics(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics about expiring documents.
        
        Args:
            db: Database session
            days: Number of days ahead to look
            
        Returns:
            Dictionary with expiring documents and statistics
        """
        try:
            now = datetime.utcnow()
            expiry_threshold = now + timedelta(days=days)
            
            # Get documents expiring in the next N days
            expiring_docs = db.query(Document).filter(
                Document.expiry_date.isnot(None),
                Document.expiry_date <= expiry_threshold,
                Document.expiry_date >= now,
                Document.status.in_(['pending', 'approved'])  # Only active documents
            ).order_by(Document.expiry_date.asc()).all()
            
            # Get already expired documents
            expired_docs = db.query(Document).filter(
                Document.expiry_date.isnot(None),
                Document.expiry_date < now,
                Document.status.in_(['pending', 'approved'])
            ).order_by(Document.expiry_date.desc()).all()
            
            # Get documents without expiry date
            no_expiry_docs = db.query(func.count(Document.id)).filter(
                Document.expiry_date.is_(None),
                Document.status.in_(['pending', 'approved'])
            ).scalar() or 0
            
            # Count by urgency
            expiring_7_days = len([d for d in expiring_docs if (d.expiry_date - now).days <= 7])
            expiring_30_days = len([d for d in expiring_docs if (d.expiry_date - now).days <= 30])
            
            logger.info(f"Expiry analytics computed for {days} days")
            
            return {
                'expiring_soon': expiring_7_days,
                'expiring_30_days': expiring_30_days,
                'already_expired': len(expired_docs),
                'no_expiry_set': no_expiry_docs,
                'expiring_documents': [
                    {
                        'id': doc.id,
                        'filename': doc.original_filename,
                        'category': doc.category,
                        'status': doc.status,
                        'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
                        'expiry_notes': doc.expiry_notes,
                        'days_until_expiry': (doc.expiry_date - now).days if doc.expiry_date else None,
                        'uploaded_by': doc.uploaded_by
                    }
                    for doc in expiring_docs
                ],
                'expired_documents': [
                    {
                        'id': doc.id,
                        'filename': doc.original_filename,
                        'category': doc.category,
                        'status': doc.status,
                        'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
                        'days_since_expiry': (now - doc.expiry_date).days if doc.expiry_date else None
                    }
                    for doc in expired_docs
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to compute expiry analytics: {e}")
            return {
                'expiring_soon': 0,
                'expiring_30_days': 0,
                'already_expired': 0,
                'no_expiry_set': 0,
                'expiring_documents': [],
                'expired_documents': []
            }


# Global instance
analytics_service = AnalyticsService()