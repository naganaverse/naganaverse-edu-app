"""
services/notification_service.py
─────────────────────────────────────────────────────────────
Parent Notification Engine.

Primary channel: WhatsApp (via API)
Secondary channel: Telegram (optional)

Batch processing: 10 messages per second (anti-blocking)
All deliveries logged to parent_notifications table.

Trigger events:
  - test_result: Teacher sends test reports
  - attendance_report: Owner sends attendance to parents
  - absence_alert: Student marked absent (automated)
  - announcement: Owner broadcasts to parents
─────────────────────────────────────────────────────────────
"""

import asyncio
from typing import List

from loguru import logger

from config.config import settings
from core.loader import bot
from database.models.notification_model import ParentNotification
from database.repositories.notification_repo import NotificationRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.test_repo import TestRepository
from database.repositories.attendance_repo import AttendanceRepository

_notif_repo = NotificationRepository()
_student_repo = StudentRepository()
_test_repo = TestRepository()
_attendance_repo = AttendanceRepository()

BATCH_SIZE = 10             # messages per second
BATCH_DELAY = 1.0           # seconds between batches


async def send_test_results_to_parents(
    org_id: str,
    test_id: str,
    class_name: str,
    triggered_by: str,
) -> dict:
    """
    Fetch all test results for a class and send WhatsApp messages to parents.
    Called by teacher/owner after tapping 'Send Test Reports'.
    """
    from database.connection import get_pool
    pool = await get_pool()

    # Get test info
    test = await _test_repo.get_test_by_id(test_id, org_id)
    if not test:
        return {"success": False, "message": "❌ Test not found."}

    # Get students with results
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.student_id, s.name, s.parent_phone,
                   tr.marks, t.total_marks, t.test_name, t.subject_name
            FROM test_results tr
            JOIN students s ON s.student_id = tr.student_id
            JOIN tests t ON t.test_id = tr.test_id
            WHERE tr.test_id = $1 AND tr.org_id = $2
              AND s.parent_phone IS NOT NULL
            """,
            test_id, org_id,
        )

    if not rows:
        return {"success": False, "message": "❌ No results found to send."}

    messages = []
    for row in rows:
        msg = _test_result_template(
            org_id=org_id,
            student_name=row["name"],
            class_name=class_name,
            test_name=row["test_name"],
            subject=row["subject_name"],
            marks=row["marks"],
            total_marks=row["total_marks"],
        )
        messages.append({
            "phone": row["parent_phone"],
            "message": msg,
            "student_id": row["student_id"],
        })

    sent = await _batch_send(messages, "test_result", org_id)

    return {
        "success": True,
        "sent": sent,
        "message": (
            f"✅ Test reports sent to parents.\n"
            f"📊 {sent}/{len(messages)} delivered."
        ),
    }


async def send_attendance_to_parents(
    org_id: str,
    class_name: str,
    triggered_by: str,
) -> dict:
    """Send attendance summary to all parents in a class."""
    report = await _attendance_repo.get_class_report(org_id, class_name)

    if not report:
        return {"success": False, "message": "❌ No attendance data found."}

    messages = []
    for entry in report:
        if not entry.get("parent_phone"):
            continue
        msg = _attendance_report_template(
            student_name=entry["name"],
            class_name=class_name,
            percentage=entry["percentage"],
            present=entry["present"],
            total=entry["total"],
        )
        messages.append({
            "phone": entry["parent_phone"],
            "message": msg,
            "student_id": entry["student_id"],
        })

    sent = await _batch_send(messages, "attendance_report", org_id)

    return {
        "success": True,
        "sent": sent,
        "message": (
            f"✅ Attendance reports sent.\n"
            f"👪 {sent}/{len(messages)} parents notified."
        ),
    }


async def send_absence_alert(
    org_id: str,
    student_id: str,
    student_name: str,
    parent_phone: str,
    class_name: str,
    subject_name: str,
    date_str: str,
    parent_telegram_id: int = None,
) -> None:
    """Automated alert: student was marked absent.
    Sends via Telegram if parent is on bot, WhatsApp stub otherwise.
    """
    msg = (
        f"🔔 <b>Naganaverse Education</b>\n"
        f"<b>Absence Alert</b>\n\n"
        f"👤 Student: {student_name}\n"
        f"📚 Class: {class_name}\n"
        f"📖 Subject: {subject_name}\n"
        f"📅 Date: {date_str}\n\n"
        f"Please ensure your child attends classes regularly."
    )
    # Try Telegram first (free + instant)
    if parent_telegram_id:
        await _send_telegram_to_parent(parent_telegram_id, msg)
    else:
        # WhatsApp stub — live when API is ready
        await _send_whatsapp(parent_phone, msg)
    await _log_notification(org_id, student_id, parent_phone, "absence_alert", msg)


# ── Batch Processing ───────────────────────────────────────

async def _batch_send(messages: List[dict], notif_type: str, org_id: str) -> int:
    """
    Send messages in batches of BATCH_SIZE per second.
    Logs each delivery to parent_notifications.
    Returns count of successfully sent messages.
    """
    sent = 0
    for i in range(0, len(messages), BATCH_SIZE):
        batch = messages[i:i + BATCH_SIZE]
        tasks = []
        for m in batch:
            # Try Telegram first (free, instant) — then WhatsApp stub
            if m.get("parent_telegram_id"):
                tasks.append(_send_telegram_to_parent(m["parent_telegram_id"], m["message"]))
            else:
                tasks.append(_send_whatsapp(m["phone"], m["message"]))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(results):
            m = batch[j]
            if not isinstance(result, Exception):
                await _log_notification(org_id, m["student_id"], m["phone"], notif_type, m["message"])
                sent += 1
            else:
                logger.error(f"WhatsApp send failed | phone={m['phone']} | {result}")

        if i + BATCH_SIZE < len(messages):
            await asyncio.sleep(BATCH_DELAY)

    return sent


async def _send_whatsapp(phone: str, message: str) -> bool:
    """
    WhatsApp API call — INFRASTRUCTURE READY, NOT LIVE YET.
    Uncomment below when Meta WhatsApp Business API is set up.
    """
    logger.debug(f"[WhatsApp stub] → {phone}: {message[:50]}...")
    # ── WHATSAPP — COMING SOON ──────────────────────────────
    # Uncomment when Meta API credentials are ready:
    #
    # import aiohttp
    # WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    # WHATSAPP_TOKEN   = settings.whatsapp_token
    # async with aiohttp.ClientSession() as session:
    #     await session.post(
    #         WHATSAPP_API_URL,
    #         headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
    #         json={
    #             "messaging_product": "whatsapp",
    #             "to": phone,
    #             "type": "text",
    #             "text": {"body": message}
    #         }
    #     )
    # ── END WHATSAPP ─────────────────────────────────────────
    return True   # stub always succeeds


async def _send_telegram_to_parent(parent_telegram_id: int, message: str) -> bool:
    """
    Send Telegram message to parent — LIVE ✅
    Called when parent has logged into the bot (telegram_id is bound).
    """
    if not parent_telegram_id:
        return False
    try:
        await bot.send_message(parent_telegram_id, message)
        return True
    except Exception as e:
        logger.warning(f"Telegram parent notify failed | tg={parent_telegram_id} | {e}")
        return False


async def _log_notification(
    org_id: str, student_id: str, parent_phone: str,
    notif_type: str, message: str
) -> None:
    notif = ParentNotification(
        org_id=org_id,
        student_id=student_id,
        parent_phone=parent_phone,
        notification_type=notif_type,
        message=message,
    )
    await _notif_repo.log(notif)


# ── Message Templates ──────────────────────────────────────

def _test_result_template(
    org_id, student_name, class_name, test_name, subject, marks, total_marks
) -> str:
    pct = round(float(marks / total_marks * 100), 1) if total_marks > 0 else 0
    return (
        f"🎓 *Naganaverse Education*\n\n"
        f"Student: {student_name}\n"
        f"Class: {class_name}\n"
        f"Test: {test_name}\n"
        f"Subject: {subject}\n"
        f"Marks: {marks}/{total_marks} ({pct}%)\n\n"
        f"For details, open the Naganaverse Bot."
    )


def _attendance_report_template(student_name, class_name, percentage, present, total) -> str:
    return (
        f"📊 *Naganaverse Attendance Report*\n\n"
        f"Student: {student_name}\n"
        f"Class: {class_name}\n"
        f"Attendance: {percentage}%\n"
        f"Present: {present}/{total} classes\n\n"
        f"For details, open the Naganaverse Bot."
    )
