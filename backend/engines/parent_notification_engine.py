"""
engines/parent_notification_engine.py
─────────────────────────────────────────────────────────────
Core Parent Notification Engine.

Differs from notification_service:
  - Service handles per-event triggers from bot UI
  - Engine handles the batch queue processor, delivery pipeline,
    and cross-module dispatch routing

Batch rule: 10 messages per second (hard limit to prevent API block)

Trigger events:
  test_result       — teacher sends test reports
  attendance_report — owner/teacher sends class report
  absence_alert     — student marked absent (automated)
  announcement      — owner/teacher broadcasts

Exposed functions:
  dispatch_notification()  — trigger a notification for one student
  process_queue()          — batch-send pending notifications
  dispatch_class_results() — bulk test results to a whole class
  dispatch_absence_alerts()— bulk absence alerts after attendance
─────────────────────────────────────────────────────────────
"""

import asyncio
from typing import List

from loguru import logger

from database.connection import get_pool
from database.models.notification_model import ParentNotification
from database.repositories.notification_repo import NotificationRepository
from database.repositories.student_repo import StudentRepository

_notif_repo   = NotificationRepository()
_student_repo = StudentRepository()

# ── Rate limit constants ──────────────────────────────────
BATCH_SIZE  = 10    # messages per batch
BATCH_DELAY = 1.0   # seconds between batches


async def dispatch_notification(
    org_id: str,
    student_id: str,
    parent_phone: str,
    notification_type: str,
    message: str,
) -> bool:
    """
    Dispatch a single parent notification.
    Sends via WhatsApp API + logs delivery to DB.

    notification_type: test_result | attendance_report | absence_alert | announcement
    """
    success = await _send_whatsapp(parent_phone, message)

    notif = ParentNotification(
        org_id=org_id,
        student_id=student_id,
        parent_phone=parent_phone,
        notification_type=notification_type,
        message=message,
    )
    await _notif_repo.log(notif)

    if success:
        logger.debug(f"Notification dispatched | type={notification_type} | phone={parent_phone}")
    return success


async def process_queue(notifications: List[dict]) -> dict:
    """
    Batch-send a list of notifications at 10/second.
    Each item: {org_id, student_id, parent_phone, notification_type, message}

    Returns: {"sent": int, "failed": int, "total": int}
    """
    sent   = 0
    failed = 0
    total  = len(notifications)

    for i in range(0, total, BATCH_SIZE):
        batch   = notifications[i:i + BATCH_SIZE]
        tasks   = [_send_whatsapp(n["parent_phone"], n["message"]) for n in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(results):
            n = batch[j]
            if isinstance(result, Exception):
                failed += 1
                logger.warning(f"Notification failed | phone={n['parent_phone']} | {result}")
            else:
                sent += 1
                notif = ParentNotification(
                    org_id=n["org_id"],
                    student_id=n["student_id"],
                    parent_phone=n["parent_phone"],
                    notification_type=n["notification_type"],
                    message=n["message"],
                )
                await _notif_repo.log(notif)

        if i + BATCH_SIZE < total:
            await asyncio.sleep(BATCH_DELAY)

    logger.info(f"Notification queue processed | sent={sent} | failed={failed} | total={total}")
    return {"sent": sent, "failed": failed, "total": total}


async def dispatch_class_results(
    org_id: str,
    test_id: str,
    class_name: str,
) -> dict:
    """
    Bulk dispatch test results to all parents of a class.
    Called by teacher "Send Test Reports" or owner "Test Reports → Send to Parents".
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.student_id, s.name, s.parent_phone,
                   tr.marks, t.total_marks, t.test_name, t.subject_name
            FROM test_results tr
            JOIN students s ON s.student_id = tr.student_id
            JOIN tests    t ON t.test_id    = tr.test_id
            WHERE tr.test_id = $1 AND tr.org_id = $2
              AND s.parent_phone IS NOT NULL
            """,
            test_id, org_id,
        )

    if not rows:
        return {"sent": 0, "total": 0, "message": "No results to send."}

    notifications = []
    for r in rows:
        pct = round(float(r["marks"] / r["total_marks"] * 100), 1) if r["total_marks"] > 0 else 0
        msg = (
            f"🎓 *Naganaverse Education*\n\n"
            f"Student: {r['name']}\n"
            f"Class: {class_name}\n"
            f"Test: {r['test_name']}\n"
            f"Subject: {r['subject_name']}\n"
            f"Marks: {r['marks']}/{r['total_marks']} ({pct}%)"
        )
        notifications.append({
            "org_id": org_id,
            "student_id": r["student_id"],
            "parent_phone": r["parent_phone"],
            "notification_type": "test_result",
            "message": msg,
        })

    result = await process_queue(notifications)
    return result


async def dispatch_absence_alerts(
    org_id: str,
    class_name: str,
    subject_name: str,
    absent_students: List[dict],  # [{"student_id", "name", "parent_phone"}]
    date_str: str,
) -> dict:
    """
    Dispatch absence alerts to parents of absent students.
    Called automatically after attendance is taken.
    """
    notifications = []
    for s in absent_students:
        if not s.get("parent_phone"):
            continue
        msg = (
            f"🔔 *Naganaverse Education*\n"
            f"Absence Alert\n\n"
            f"Student: {s['name']}\n"
            f"Class: {class_name}\n"
            f"Subject: {subject_name}\n"
            f"Date: {date_str}\n\n"
            f"Please ensure regular attendance."
        )
        notifications.append({
            "org_id": org_id,
            "student_id": s["student_id"],
            "parent_phone": s["parent_phone"],
            "notification_type": "absence_alert",
            "message": msg,
        })

    if not notifications:
        return {"sent": 0, "total": 0}

    return await process_queue(notifications)


# ── WhatsApp API stub ─────────────────────────────────────

async def _send_whatsapp(phone: str, message: str) -> bool:
    """
    WhatsApp Business API call.
    Replace with your provider: Meta Cloud API, WATI, 360dialog, Twilio.

    Example (Meta Cloud API):
        POST https://graph.facebook.com/v18.0/{phone_id}/messages
        Headers: Authorization: Bearer {token}
        Body: {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message}
        }
    """
    logger.debug(f"[WhatsApp stub] → {phone}: {message[:40]}...")
    # TODO: Wire your WhatsApp API provider here
    return True
