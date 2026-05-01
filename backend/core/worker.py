"""
core/worker.py
─────────────────────────────────────────────────────────────
Celery worker configuration for background task processing.

Handles:
  - Parent notifications (WhatsApp delivery)
  - Bulk message broadcasting
  - Heavy background processing (report generation, etc.)

Run the worker separately:
  celery -A core.worker worker --loglevel=info --concurrency=4
─────────────────────────────────────────────────────────────
"""

from celery import Celery
from celery.utils.log import get_task_logger
from kombu import Queue

from config.config import settings

logger = get_task_logger(__name__)

# ── Celery App ────────────────────────────────────────────
celery_app = Celery(
    "naganaverse",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.notification_tasks",
        "tasks.scheduled_tasks",
    ],
)

# ── Celery Configuration ──────────────────────────────────
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone=settings.SCHEDULER_TIMEZONE,
    enable_utc=True,

    # Task behavior
    task_acks_late=True,             # Acknowledge only after completion
    task_reject_on_worker_lost=True, # Re-queue if worker dies mid-task
    task_track_started=True,

    # Retry policy
    task_max_retries=3,
    task_default_retry_delay=60,     # 60 seconds between retries

    # Result expiry
    result_expires=86400,            # Results kept 24 hours

    # Queue routing
    task_queues=(
        Queue("default"),
        Queue("notifications"),      # Parent WhatsApp notifications
        Queue("bulk_messages"),      # Broadcast messages
        Queue("reports"),            # Report generation
    ),
    task_default_queue="default",
    task_routes={
        "tasks.notification_tasks.send_parent_notification": {"queue": "notifications"},
        "tasks.notification_tasks.send_bulk_message": {"queue": "bulk_messages"},
        "tasks.notification_tasks.generate_report": {"queue": "reports"},
    },

    # Worker settings
    worker_prefetch_multiplier=1,    # Fair task distribution
    worker_max_tasks_per_child=1000, # Restart worker after 1000 tasks (memory leak prevention)
)


# ── Health Check Task ─────────────────────────────────────
@celery_app.task(name="core.worker.health_check", bind=True)
def health_check(self) -> dict:
    """
    Simple ping task to verify Celery workers are alive.
    Called by monitoring systems.
    """
    logger.info("Celery health check ping received.")
    return {"status": "ok", "worker": self.request.hostname}
