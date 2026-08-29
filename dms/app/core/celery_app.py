"""
Office DMS - Celery Application Configuration
Async task queue with Redis broker, result backend, and scheduled tasks.
"""

from celery import Celery
from celery.signals import task_failure, task_success, task_retry
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Celery App Instance
# =============================================================================
celery_app = Celery(
    "office_dms",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.core.tasks"],
)

# =============================================================================
# Celery Configuration
# =============================================================================
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600 * 24,  # Results expire after 24 hours
    # Task execution
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit 9 minutes
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory leaks)
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute initial delay
    task_max_retries=3,
    task_default_exponential_backoff=True,
    # Result backend
    result_backend=settings.REDIS_URL,
    result_extended=True,
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_heartbeat=30,
    # Task routing (optional optimization)
    task_routes={
        "app.core.tasks.process_document": {"queue": "documents"},
        "app.core.tasks.check_eta_reminders": {"queue": "scheduled"},
        "app.core.tasks.cleanup_workspace": {"queue": "maintenance"},
        "app.core.tasks.backup_database": {"queue": "maintenance"},
    },
    # Beat scheduler (Celery Beat)
    beat_schedule={
        "check-eta-reminders": {
            "task": "app.core.tasks.check_eta_reminders",
            "schedule": 3600.0 * 6,  # Every 6 hours
        },
        "cleanup-workspace": {
            "task": "app.core.tasks.cleanup_workspace",
            "schedule": 3600.0 * 24,  # Daily
        },
        "check-overdue-sops": {
            "task": "app.core.tasks.check_overdue_sops",
            "schedule": 3600.0 * 12,  # Every 12 hours
        },
    },
    beat_schedule_filename="/tmp/celerybeat-schedule",
    beat_max_loop_interval=300,
    timezone="UTC",
    enable_utc=True,
)


# =============================================================================
# Celery Signals
# =============================================================================
@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    """Log successful task completion."""
    logger.info(f"Task {sender.name} [{sender.request.id}] completed successfully")


@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Log task failures."""
    logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")


@task_retry.connect
def on_task_retry(sender=None, request=None, reason=None, **kwargs):
    """Log task retries."""
    logger.warning(f"Task {sender.name} [{request.id}] retrying: {reason}")
