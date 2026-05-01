"""
tasks/notification_tasks.py
─────────────────────────────────────────────────────────────
Celery tasks for asynchronous parent notification delivery.

These tasks run in separate worker processes, ensuring:
  - Bot UI never freezes while 100s of parents are messaged
  - Failed messages are retried automatically (max 3 times)
  - Each task handles exactly one batch (10 messages)

Queue: "notifications"
─────────────────────────────────────────────────────────────
"""

import asyncio
from typing import List

from loguru import logger

from core.worker import celery_app


@celery_app.task(
    name="tasks.notification_tasks.send_parent_notification",
    queue="notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_parent_notification(self, notification: dict) -> dict:
    """
    Send a single parent notification via WhatsApp.
    Celery task — runs in worker process.

    notification = {
        "org_id": str,
        "student_id": str,
        "parent_phone": str,
        "notification_type": str,
        "message": str,
    }
    """
    try:
        result = asyncio.run(_async_send_notification(notification))
        return result
    except Exception as exc:
        logger.warning(
            f"Notification task failed (attempt {self.request.retries + 1}/3): {exc}"
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="tasks.notification_tasks.send_bulk_message",
    queue="bulk_messages",
    bind=True,
    max_retries=2,
)
def send_bulk_message(self, messages: List[dict]) -> dict:
    """
    Send a batch of messages — used for announcements and broadcasts.
    Processes up to 10 messages per second.

    Each message = {"telegram_id": int, "text": str}
    """
    try:
        result = asyncio.run(_async_bulk_send(messages))
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(
    name="tasks.notification_tasks.generate_report",
    queue="reports",
    bind=True,
    max_retries=1,
)
def generate_report(self, report_type: str, org_id: str, params: dict) -> dict:
    """
    Generate and send a report (attendance/test) to parents.
    report_type: "attendance" | "test_results"
    """
    try:
        result = asyncio.run(_async_generate_report(report_type, org_id, params))
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Async implementations ─────────────────────────────────

async def _async_send_notification(notification: dict) -> dict:
    from engines.parent_notification_engine import dispatch_notification
    success = await dispatch_notification(
        org_id=notification["org_id"],
        student_id=notification["student_id"],
        parent_phone=notification["parent_phone"],
        notification_type=notification["notification_type"],
        message=notification["message"],
    )
    return {"success": success, "phone": notification["parent_phone"]}


async def _async_bulk_send(messages: List[dict]) -> dict:
    """Send Telegram messages in batches of 10/second."""
    import asyncio
    from core.loader import bot

    sent   = 0
    failed = 0

    for i in range(0, len(messages), 10):
        batch = messages[i:i + 10]
        tasks = []
        for m in batch:
            tasks.append(_try_send_tg(bot, m["telegram_id"], m["text"]))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                failed += 1
            else:
                sent += 1
        if i + 10 < len(messages):
            await asyncio.sleep(1.0)

    return {"sent": sent, "failed": failed, "total": len(messages)}


async def _async_generate_report(report_type: str, org_id: str, params: dict) -> dict:
    if report_type == "attendance":
        from services.notification_service import send_attendance_to_parents
        return await send_attendance_to_parents(
            org_id=org_id,
            class_name=params["class_name"],
            triggered_by=params.get("triggered_by", "system"),
        )
    elif report_type == "test_results":
        from services.notification_service import send_test_results_to_parents
        return await send_test_results_to_parents(
            org_id=org_id,
            test_id=params["test_id"],
            class_name=params["class_name"],
            triggered_by=params.get("triggered_by", "system"),
        )
    return {"success": False, "message": "Unknown report type"}


async def _try_send_tg(bot, telegram_id: int, text: str) -> bool:
    await bot.send_message(telegram_id, text)
    return True
