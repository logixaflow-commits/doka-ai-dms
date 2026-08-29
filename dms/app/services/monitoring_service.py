"""
Monitoring Service - System health and performance monitoring
"""
import psutil
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.database import SystemHealthLog
from app.core.config import settings
from app.core.redis_client import redis_client


class MonitoringService:
    """Service for system health monitoring and metrics collection."""

    def __init__(self, db: Session):
        self.db = db
        self.alert_thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90,
            "queue_depth": 1000,
            "db_connections": 80
        }

    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect system metrics.
        
        Returns:
            System metrics dictionary
        """
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "count": psutil.cpu_count(),
                    "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                },
                "memory": {
                    "percent": psutil.virtual_memory().percent,
                    "available_gb": psutil.virtual_memory().available / (1024**3),
                    "total_gb": psutil.virtual_memory().total / (1024**3),
                    "used_gb": psutil.virtual_memory().used / (1024**3)
                },
                "disk": {
                    "percent": psutil.disk_usage('/').percent,
                    "free_gb": psutil.disk_usage('/').free / (1024**3),
                    "total_gb": psutil.disk_usage('/').total / (1024**3),
                    "used_gb": psutil.disk_usage('/').used / (1024**3)
                }
            }

            # Add database metrics
            metrics["database"] = self._get_database_metrics()
            
            # Add Redis metrics
            metrics["redis"] = self._get_redis_metrics()
            
            # Add Celery queue metrics
            metrics["celery"] = self._get_celery_metrics()

            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}

    def check_health(self) -> Dict[str, Any]:
        """
        Check health of all services.
        
        Returns:
            Health check results
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall": "healthy",
            "services": {}
        }

        # Check Database
        db_health = self._check_database_health()
        health["services"]["database"] = db_health
        if db_health["status"] != "healthy":
            health["overall"] = "unhealthy"

        # Check Redis
        redis_health = self._check_redis_health()
        health["services"]["redis"] = redis_health
        if redis_health["status"] != "healthy":
            health["overall"] = "unhealthy"

        # Check MinIO (Storage)
        minio_health = self._check_minio_health()
        health["services"]["minio"] = minio_health
        if minio_health["status"] != "healthy":
            health["overall"] = "unhealthy"

        # Check Celery Workers
        celery_health = self._check_celery_health()
        health["services"]["celery"] = celery_health
        if celery_health["status"] != "healthy":
            health["overall"] = "degraded"

        return health

    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get metrics summary over time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Metrics summary
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            logs = self.db.query(SystemHealthLog).filter(
                SystemHealthLog.timestamp >= cutoff_time
            ).all()

            summary = {
                "period_hours": hours,
                "total_checks": len(logs),
                "healthy_count": sum(1 for log in logs if log.status == "healthy"),
                "degraded_count": sum(1 for log in logs if log.status == "degraded"),
                "unhealthy_count": sum(1 for log in logs if log.status == "unhealthy"),
                "services": {}
            }

            # Aggregate by service
            services = set(log.service for log in logs)
            for service in services:
                service_logs = [log for log in logs if log.service == service]
                summary["services"][service] = {
                    "total": len(service_logs),
                    "healthy": sum(1 for log in service_logs if log.status == "healthy"),
                    "degraded": sum(1 for log in service_logs if log.status == "degraded"),
                    "unhealthy": sum(1 for log in service_logs if log.status == "unhealthy")
                }

            return summary

        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}

    def alert_if_unhealthy(self) -> List[str]:
        """
        Check for unhealthy conditions and trigger alerts.
        
        Returns:
            List of alert messages
        """
        alerts = []
        
        try:
            metrics = self.collect_metrics()
            
            # CPU Alert
            if metrics.get("cpu", {}).get("percent", 0) > self.alert_thresholds["cpu_percent"]:
                alerts.append(f"High CPU usage: {metrics['cpu']['percent']}%")
            
            # Memory Alert
            if metrics.get("memory", {}).get("percent", 0) > self.alert_thresholds["memory_percent"]:
                alerts.append(f"High memory usage: {metrics['memory']['percent']}%")
            
            # Disk Alert
            if metrics.get("disk", {}).get("percent", 0) > self.alert_thresholds["disk_percent"]:
                alerts.append(f"Low disk space: {metrics['disk']['percent']}% used")

            # Queue Alert
            celery_metrics = metrics.get("celery", {})
            if celery_metrics.get("queue_depth", 0) > self.alert_thresholds["queue_depth"]:
                alerts.append(f"High queue depth: {celery_metrics['queue_depth']}")

            # DB Connections Alert
            db_metrics = metrics.get("database", {})
            if db_metrics.get("active_connections", 0) > self.alert_thresholds["db_connections"]:
                alerts.append(f"High DB connections: {db_metrics['active_connections']}")

            # Send email alerts if any
            if alerts:
                self._send_alert_email(alerts)

            return alerts

        except Exception as e:
            logger.error(f"Failed to check health alerts: {e}")
            return []

    def log_health_check(self):
        """Log health check to database."""
        try:
            health = self.check_health()
            
            for service_name, service_health in health["services"].items():
                log = SystemHealthLog(
                    service=service_name,
                    status=service_health["status"],
                    metrics=service_health.get("metrics", {}),
                    timestamp=datetime.utcnow()
                )
                self.db.add(log)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log health check: {e}")
            self.db.rollback()

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            start_time = time.time()
            self.db.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000  # ms
            
            status = "healthy" if response_time < 1000 else "degraded"
            
            metrics = {
                "response_time_ms": response_time,
                "active_connections": self._get_db_connection_count()
            }
            
            return {
                "status": status,
                "metrics": metrics
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "metrics": {}
            }

    def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health."""
        try:
            if redis_client:
                start_time = time.time()
                redis_client.ping()
                response_time = (time.time() - start_time) * 1000
                
                status = "healthy" if response_time < 500 else "degraded"
                
                return {
                    "status": status,
                    "metrics": {
                        "response_time_ms": response_time,
                        "connected_clients": redis_client.client_list() if hasattr(redis_client, 'client_list') else 0
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Redis client not configured"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "metrics": {}
            }

    def _check_minio_health(self) -> Dict[str, Any]:
        """Check MinIO health."""
        try:
            from app.core.storage import storage_manager
            
            start_time = time.time()
            storage_manager.list_buckets()
            response_time = (time.time() - start_time) * 1000
            
            status = "healthy" if response_time < 2000 else "degraded"
            
            return {
                "status": status,
                "metrics": {
                    "response_time_ms": response_time
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "metrics": {}
            }

    def _check_celery_health(self) -> Dict[str, Any]:
        """Check Celery workers health."""
        try:
            from app.core.celery_app import celery_app
            
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            stats = inspect.stats()
            
            if active_tasks:
                status = "healthy"
            else:
                status = "degraded"
            
            metrics = {
                "active_workers": len(active_tasks) if active_tasks else 0,
                "queue_depth": self._get_celery_metrics().get("queue_depth", 0)
            }
            
            return {
                "status": status,
                "metrics": metrics
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "metrics": {}
            }

    def _get_database_metrics(self) -> Dict[str, Any]:
        """Get detailed database metrics."""
        try:
            return {
                "active_connections": self._get_db_connection_count(),
                "idle_connections": self._get_db_connection_count()  # Simplified
            }
        except Exception as e:
            logger.error(f"Failed to get database metrics: {e}")
            return {}

    def _get_redis_metrics(self) -> Dict[str, Any]:
        """Get Redis metrics."""
        try:
            if redis_client:
                info = redis_client.info()
                return {
                    "used_memory_mb": info.get("used_memory", 0) / (1024 * 1024),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands": info.get("total_commands_processed", 0)
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get Redis metrics: {e}")
            return {}

    def _get_celery_metrics(self) -> Dict[str, Any]:
        """Get Celery queue metrics."""
        try:
            from app.core.celery_app import celery_app
            
            # Get queue depth (simplified)
            return {
                "queue_depth": 0,  # Would need actual queue inspection
                "active_tasks": 0
            }
        except Exception as e:
            logger.error(f"Failed to get Celery metrics: {e}")
            return {}

    def _get_db_connection_count(self) -> int:
        """Get current database connection count."""
        try:
            result = self.db.execute(text("SELECT count(*) FROM pg_stat_activity"))
            return result.scalar() or 0
        except:
            # Fallback for SQLite or other databases
            return 0

    def _send_alert_email(self, alerts: List[str]):
        """Send alert email for unhealthy conditions."""
        try:
            from app.services.email_service import email_service
            
            subject = f"⚠️ System Health Alert - {len(alerts)} Issues"
            body = f"The following health issues were detected:\n\n"
            for alert in alerts:
                body += f"- {alert}\n"
            body += f"\nTimestamp: {datetime.utcnow()}"
            
            # In production, send to configured admin email
            # email_service.send_alert_email(subject, body)
            
            logger.warning(f"Health alerts (would send email): {alerts}")
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")


def get_monitoring_service(db: Session) -> MonitoringService:
    """Factory function to get MonitoringService instance."""
    return MonitoringService(db)