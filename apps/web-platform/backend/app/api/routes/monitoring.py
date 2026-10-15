"""
Monitoring Routes
Handles system health and performance monitoring endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.models.database import User
from app.services.monitoring_service import get_monitoring_service
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "Enterprise DMS",
        "version": "4.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Detailed health check for all services."""
    try:
        monitoring_service = get_monitoring_service(db)
        health = monitoring_service.check_health()
        return health
        
    except Exception as e:
        logger.error(f"Failed to perform detailed health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


@router.get("/metrics")
async def prometheus_metrics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus format.
    """
    try:
        monitoring_service = get_monitoring_service(db)
        metrics = monitoring_service.collect_metrics()
        
        # Convert to Prometheus format
        prometheus_output = []
        
        # CPU metrics
        prometheus_output.append(f'# HELP dms_cpu_percent CPU usage percentage')
        prometheus_output.append(f'# TYPE dms_cpu_percent gauge')
        prometheus_output.append(f'dms_cpu_percent {metrics.get("cpu", {}).get("percent", 0)}')
        
        # Memory metrics
        prometheus_output.append(f'# HELP dms_memory_percent Memory usage percentage')
        prometheus_output.append(f'# TYPE dms_memory_percent gauge')
        prometheus_output.append(f'dms_memory_percent {metrics.get("memory", {}).get("percent", 0)}')
        
        prometheus_output.append(f'# HELP dms_memory_available_gb Available memory in GB')
        prometheus_output.append(f'# TYPE dms_memory_available_gb gauge')
        prometheus_output.append(f'dms_memory_available_gb {metrics.get("memory", {}).get("available_gb", 0)}')
        
        # Disk metrics
        prometheus_output.append(f'# HELP dms_disk_percent Disk usage percentage')
        prometheus_output.append(f'# TYPE dms_disk_percent gauge')
        prometheus_output.append(f'dms_disk_percent {metrics.get("disk", {}).get("percent", 0)}')
        
        prometheus_output.append(f'# HELP dms_disk_free_gb Free disk space in GB')
        prometheus_output.append(f'# TYPE dms_disk_free_gb gauge')
        prometheus_output.append(f'dms_disk_free_gb {metrics.get("disk", {}).get("free_gb", 0)}')
        
        # Database metrics
        prometheus_output.append(f'# HELP dms_db_active_connections Active database connections')
        prometheus_output.append(f'# TYPE dms_db_active_connections gauge')
        prometheus_output.append(f'dms_db_active_connections {metrics.get("database", {}).get("active_connections", 0)}')
        
        # Celery metrics
        prometheus_output.append(f'# HELP dms_celery_queue_depth Celery queue depth')
        prometheus_output.append(f'# TYPE dms_celery_queue_depth gauge')
        prometheus_output.append(f'dms_celery_queue_depth {metrics.get("celery", {}).get("queue_depth", 0)}')
        
        return "\n".join(prometheus_output), {"Content-Type": "text/plain"}
        
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate metrics"
        )


@router.get("/monitoring")
async def monitoring_dashboard(
    hours: int = 24,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get monitoring dashboard data (admin only)."""
    try:
        monitoring_service = get_monitoring_service(db)
        
        current_metrics = monitoring_service.collect_metrics()
        health = monitoring_service.check_health()
        metrics_summary = monitoring_service.get_metrics_summary(hours)
        alerts = monitoring_service.alert_if_unhealthy()
        
        return {
            "current_metrics": current_metrics,
            "health": health,
            "metrics_summary": metrics_summary,
            "active_alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get monitoring data"
        )


@router.get("/alerts")
async def get_recent_alerts(
    hours: int = 24,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get recent health alerts (admin only)."""
    try:
        from app.models.database import SystemHealthLog
        from datetime import timedelta, datetime
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        unhealthy_logs = db.query(SystemHealthLog).filter(
            SystemHealthLog.timestamp >= cutoff_time,
            SystemHealthLog.status != "healthy"
        ).order_by(SystemHealthLog.timestamp.desc()).limit(100).all()
        
        return {
            "period_hours": hours,
            "alerts_count": len(unhealthy_logs),
            "alerts": [
                {
                    "id": log.id,
                    "service": log.service,
                    "status": log.status,
                    "metrics": log.metrics,
                    "timestamp": log.timestamp
                }
                for log in unhealthy_logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get alerts"
        )