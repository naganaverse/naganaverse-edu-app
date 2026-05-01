"""
core/scheduler.py
─────────────────────────────────────────────────────────────
APScheduler setup for all automated background jobs.

Scheduled Jobs:
  - Attendance reminders       → Daily 8:00 AM IST
  - Homework reminders         → Daily 7:00 PM IST
  - Test reminders             → Daily 6:00 PM IST
  - Subscription alerts        → Daily 9:00 AM IST
  - Database health check      → Every 30 minutes
  - Audit log cleanup          → Weekly Sunday 2:00 AM IST
─────────────────────────────────────────────────────────────
"""

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config.config import settings

IST = pytz.timezone(settings.SCHEDULER_TIMEZONE)


def setup_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance.
    Returns the scheduler (not yet started — caller must call .start()).
    """
    scheduler = AsyncIOScheduler(timezone=IST)

    _register_jobs(scheduler)
    logger.info("Scheduler configured with all jobs.")
    return scheduler


def _register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register all scheduled tasks."""

    # ── Attendance Reminder ───────────────────────────────
    scheduler.add_job(
        _attendance_reminder,
        trigger=CronTrigger(hour=8, minute=0, timezone=IST),
        id="attendance_reminder",
        name="Daily Attendance Reminder",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # ── Homework Reminder ─────────────────────────────────
    scheduler.add_job(
        _homework_reminder,
        trigger=CronTrigger(hour=19, minute=0, timezone=IST),
        id="homework_reminder",
        name="Daily Homework Reminder",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # ── Test Reminder ─────────────────────────────────────
    scheduler.add_job(
        _test_reminder,
        trigger=CronTrigger(hour=18, minute=0, timezone=IST),
        id="test_reminder",
        name="Daily Test Reminder",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # ── Subscription Alert ────────────────────────────────
    scheduler.add_job(
        _subscription_alert,
        trigger=CronTrigger(hour=9, minute=0, timezone=IST),
        id="subscription_alert",
        name="Daily Subscription Alert",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # ── Database Health Check ─────────────────────────────
    scheduler.add_job(
        _database_health_check,
        trigger=CronTrigger(minute="*/30", timezone=IST),
        id="db_health_check",
        name="Database Health Check",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # ── Audit Log Cleanup ─────────────────────────────────
    scheduler.add_job(
        _audit_log_cleanup,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=IST),
        id="audit_log_cleanup",
        name="Weekly Audit Log Cleanup",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    logger.debug(f"Registered {len(scheduler.get_jobs())} scheduled jobs.")


# ── Job Implementations ───────────────────────────────────

async def _attendance_reminder() -> None:
    """Send attendance reminder to all teachers across all orgs."""
    try:
        from tasks.scheduled_tasks import send_attendance_reminders
        await send_attendance_reminders()
    except Exception as e:
        logger.error(f"Attendance reminder job failed: {e}")


async def _homework_reminder() -> None:
    """Send homework reminder to students with pending homework."""
    try:
        from tasks.scheduled_tasks import send_homework_reminders
        await send_homework_reminders()
    except Exception as e:
        logger.error(f"Homework reminder job failed: {e}")


async def _test_reminder() -> None:
    """Notify students about upcoming scheduled tests."""
    try:
        from tasks.scheduled_tasks import send_test_reminders
        await send_test_reminders()
    except Exception as e:
        logger.error(f"Test reminder job failed: {e}")


async def _subscription_alert() -> None:
    """Alert owners whose subscriptions are expiring within 7 days."""
    try:
        from tasks.scheduled_tasks import send_subscription_alerts
        await send_subscription_alerts()
    except Exception as e:
        logger.error(f"Subscription alert job failed: {e}")


async def _database_health_check() -> None:
    """Verify database connectivity; log warning if unreachable."""
    try:
        from database.connection import check_db_health
        healthy = await check_db_health()
        if not healthy:
            logger.critical("DATABASE HEALTH CHECK FAILED — connection unavailable.")
    except Exception as e:
        logger.critical(f"Database health check exception: {e}")


async def _audit_log_cleanup() -> None:
    """Archive or purge audit logs older than 90 days."""
    try:
        from tasks.scheduled_tasks import cleanup_old_audit_logs
        await cleanup_old_audit_logs()
    except Exception as e:
        logger.error(f"Audit log cleanup job failed: {e}")
