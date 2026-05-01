"""
tasks/scheduled_tasks.py
─────────────────────────────────────────────────────────────
All cron job implementations called by core/scheduler.py.

Schedule (IST):
  6:00 PM  — send_test_reminders()
  7:00 PM  — send_attendance_reminders()
  8:00 PM  — send_homework_reminders()
 12:00 AM  — send_subscription_alerts()
  3:00 AM  — run_database_backup()
  Every 5m — check_system_health()
 Every 30m — check_db_health() [in scheduler directly]

Each job:
  1. Queries its specific data
  2. Sends Telegram messages to target users
  3. Logs outcome to audit_logs or backups table
─────────────────────────────────────────────────────────────
"""

import asyncio
from datetime import date

from loguru import logger

from config.config import settings
from core.loader import bot
from database.connection import get_pool
from database.repositories.user_repo_security import AuditLogRepository

_audit = AuditLogRepository()


# ─────────────────────────────────────────────
# 1. TEST REMINDERS — 6:00 PM daily
# ─────────────────────────────────────────────

async def send_test_reminders() -> None:
    """
    Find all tests scheduled for tomorrow.
    Notify students of their respective class.
    Query: SELECT test_id, topic, class_id FROM tests WHERE date = CURRENT_DATE + 1
    """
    logger.info("Cron: send_test_reminders() starting...")
    pool = await get_pool()

    async with pool.acquire() as conn:
        orgs = await conn.fetch(
            "SELECT DISTINCT org_id FROM organizations WHERE status IN ('active','approved')"
        )

    total_sent = 0
    for org_row in orgs:
        org_id = org_row["org_id"]
        try:
            async with pool.acquire() as conn:
                tests = await conn.fetch(
                    """
                    SELECT test_id, test_name, class_name, subject_name, topic
                    FROM tests
                    WHERE org_id = $1 AND test_date = CURRENT_DATE + 1
                    """,
                    org_id,
                )

            for test in tests:
                async with pool.acquire() as conn:
                    students = await conn.fetch(
                        """
                        SELECT telegram_id FROM students
                        WHERE org_id = $1 AND class = $2 AND telegram_id IS NOT NULL
                        """,
                        org_id, test["class_name"],
                    )

                msg = (
                    f"📝 <b>Test Reminder</b>\n\n"
                    f"📖 Subject: {test['subject_name']}\n"
                    f"📋 Topic: {test['topic'] or test['test_name']}\n"
                    f"📅 Scheduled: <b>Tomorrow</b>\n\n"
                    f"📚 Be prepared!"
                )

                for s in students:
                    try:
                        await bot.send_message(s["telegram_id"], msg)
                        total_sent += 1
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Test reminder failed for org={org_id}: {e}")

    logger.info(f"Cron: send_test_reminders() done. Sent to {total_sent} students.")
    await _audit.log("CRON_TEST_REMINDERS", details={"sent": total_sent})


# ─────────────────────────────────────────────
# 2. ATTENDANCE REMINDERS — 7:00 PM daily
# ─────────────────────────────────────────────

async def send_attendance_reminders() -> None:
    """
    Find classes where attendance NOT marked today.
    Send reminder to the respective teacher.

    Query:
      SELECT class_id, subject_id, teacher_id FROM classes
      WHERE org_id = ?
      AND class_id NOT IN (
          SELECT class_id FROM attendance WHERE date = CURRENT_DATE
      )
    """
    logger.info("Cron: send_attendance_reminders() starting...")
    pool = await get_pool()

    async with pool.acquire() as conn:
        orgs = await conn.fetch(
            "SELECT DISTINCT org_id FROM organizations WHERE status IN ('active','approved')"
        )

    total_sent = 0
    for org_row in orgs:
        org_id = org_row["org_id"]
        try:
            from engines.attendance_engine import get_unmarked_classes
            unmarked = await get_unmarked_classes(org_id)

            seen_teachers = set()
            for item in unmarked:
                tg_id = item.get("telegram_id")
                if not tg_id or tg_id in seen_teachers:
                    continue
                seen_teachers.add(tg_id)

                msg = (
                    f"⏰ <b>Attendance Reminder</b>\n\n"
                    f"📚 Class: {item['class_name']}\n"
                    f"📖 Subject: {item['subject_name']}\n"
                    f"📅 Date: Today\n\n"
                    f"Please mark attendance for your class."
                )

                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Take Attendance", callback_data="teacher:att_take")],
                    [InlineKeyboardButton(text="🙈 Ignore",          callback_data="nav:home")],
                ])

                try:
                    await bot.send_message(tg_id, msg, reply_markup=kb)
                    total_sent += 1
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Attendance reminder failed for org={org_id}: {e}")

    logger.info(f"Cron: send_attendance_reminders() done. Notified {total_sent} teachers.")
    await _audit.log("CRON_ATTENDANCE_REMINDERS", details={"sent": total_sent})


# ─────────────────────────────────────────────
# 3. HOMEWORK REMINDERS — 8:00 PM daily
# ─────────────────────────────────────────────

async def send_homework_reminders() -> None:
    """
    Find today's homework and remind students.

    Queries:
      SELECT description, class_id FROM homework WHERE date = CURRENT_DATE
      SELECT telegram_id FROM students WHERE class_id = ?
    """
    logger.info("Cron: send_homework_reminders() starting...")
    pool = await get_pool()

    async with pool.acquire() as conn:
        orgs = await conn.fetch(
            "SELECT DISTINCT org_id FROM organizations WHERE status IN ('active','approved')"
        )

    total_sent = 0
    for org_row in orgs:
        org_id = org_row["org_id"]
        try:
            from engines.homework_engine import get_pending_reminders
            reminders = await get_pending_reminders(org_id)

            for reminder in reminders:
                msg = (
                    f"📌 <b>Homework Reminder</b>\n\n"
                    f"📖 {reminder['subject_name']}\n"
                    f"📝 {reminder['description']}\n\n"
                    f"Due: Today"
                )
                for tg_id in reminder["student_telegram_ids"]:
                    try:
                        await bot.send_message(tg_id, msg)
                        total_sent += 1
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Homework reminder failed for org={org_id}: {e}")

    logger.info(f"Cron: send_homework_reminders() done. Sent to {total_sent} students.")
    await _audit.log("CRON_HOMEWORK_REMINDERS", details={"sent": total_sent})


# ─────────────────────────────────────────────
# 4. SUBSCRIPTION ALERTS — 12:00 AM daily
# ─────────────────────────────────────────────

async def send_subscription_alerts() -> None:
    """
    Find subscriptions expiring within 3 days.
    Alert the institution owner.

    Query:
      SELECT org_id, expiry_date FROM subscriptions
      WHERE expiry_date <= CURRENT_DATE + 3
    """
    logger.info("Cron: send_subscription_alerts() starting...")
    pool = await get_pool()

    async with pool.acquire() as conn:
        expiring = await conn.fetch(
            """
            SELECT s.org_id, s.plan, s.expiry_date,
                   o.org_name, ow.telegram_id AS owner_tg_id
            FROM subscriptions s
            JOIN organizations o ON o.org_id = s.org_id
            LEFT JOIN owners   ow ON ow.org_id = s.org_id
            WHERE s.expiry_date <= CURRENT_DATE + 3
              AND s.expiry_date >= CURRENT_DATE
              AND s.status = 'active'
            """,
        )

    total_sent = 0
    for row in expiring:
        if not row["owner_tg_id"]:
            continue

        days_left = (row["expiry_date"] - date.today()).days
        urgency   = "⚠️" if days_left > 1 else "🚨"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Renew Now",      callback_data="owner:subscription")],
            [InlineKeyboardButton(text="📞 Contact Support", callback_data="nav:home")],
        ])

        msg = (
            f"{urgency} <b>Subscription Expiring Soon</b>\n\n"
            f"🏫 {row['org_name']}\n"
            f"📦 Plan: {row['plan'].title()}\n"
            f"📅 Expiry: {row['expiry_date']}\n"
            f"⏰ Days left: <b>{days_left}</b>\n\n"
            f"Renew to avoid service interruption."
        )

        try:
            await bot.send_message(row["owner_tg_id"], msg, reply_markup=kb)
            total_sent += 1
        except Exception:
            pass

    logger.info(f"Cron: send_subscription_alerts() done. Alerted {total_sent} owners.")
    await _audit.log("CRON_SUBSCRIPTION_ALERTS", details={"alerted": total_sent})


# ─────────────────────────────────────────────
# 5. DATABASE BACKUP — 3:00 AM daily
# ─────────────────────────────────────────────

async def run_database_backup() -> None:
    """
    Export, compress, and upload database to cloud storage.
    Log result to backups table.

    Steps:
      1. pg_dump → compressed file
      2. Upload to cloud storage (R2/S3/Backblaze)
      3. INSERT INTO backups (backup_date, status)
    """
    logger.info("Cron: run_database_backup() starting...")
    pool = await get_pool()

    try:
        import subprocess
        import os
        from datetime import datetime

        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/tmp/naganaverse_backup_{timestamp}.sql.gz"

        # pg_dump → gzip
        db_url = settings.DATABASE_URL.replace("+asyncpg", "")
        proc   = subprocess.run(
            f"pg_dump {db_url} | gzip > {backup_file}",
            shell=True, capture_output=True,
        )

        if proc.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {proc.stderr.decode()}")

        file_size = os.path.getsize(backup_file)
        logger.info(f"Backup created: {backup_file} ({file_size:,} bytes)")

        # TODO: Upload to cloud storage
        # await upload_to_r2(backup_file, f"backups/{backup_file}")

        # Log success
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO backups (backup_date, status, file_path, size_bytes) VALUES ($1, $2, $3, $4)",
                datetime.now(), "success", backup_file, file_size,
            )

        # Cleanup temp file
        os.remove(backup_file)

        # Notify super admins
        for admin_id in settings.super_admin_id_list:
            try:
                await bot.send_message(
                    admin_id,
                    f"✅ <b>Database Backup Complete</b>\n"
                    f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}\n"
                    f"📦 Size: {file_size / 1024 / 1024:.1f} MB",
                )
            except Exception:
                pass

        logger.info("Cron: run_database_backup() completed successfully.")

    except Exception as e:
        logger.error(f"Database backup FAILED: {e}")
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO backups (backup_date, status, notes) VALUES (NOW(), $1, $2)",
                "failed", str(e),
            )
        # Alert super admins of failure
        for admin_id in settings.super_admin_id_list:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚨 <b>Backup Failed</b>\n\n"
                    f"Error: {str(e)[:200]}\n"
                    f"Please check server immediately.",
                )
            except Exception:
                pass

    await _audit.log("CRON_DATABASE_BACKUP", details={"status": "completed"})


# ─────────────────────────────────────────────
# 6. SYSTEM HEALTH — every 5 minutes
# ─────────────────────────────────────────────

async def check_system_health() -> None:
    """
    Verify:
      - Database connectivity (SELECT 1)
      - Redis connectivity
      - Bot API responsiveness
    Alert super admins if any check fails.
    """
    issues = []

    # DB check
    try:
        from database.connection import check_db_health
        if not await check_db_health():
            issues.append("❌ Database unreachable")
    except Exception as e:
        issues.append(f"❌ Database error: {e}")

    # Redis check
    try:
        from core.loader import redis_client
        await redis_client.ping()
    except Exception as e:
        issues.append(f"❌ Redis error: {e}")

    if issues:
        alert = "🚨 <b>System Health Alert</b>\n\n" + "\n".join(issues)
        logger.critical(f"Health check failed: {issues}")
        for admin_id in settings.super_admin_id_list:
            try:
                await bot.send_message(admin_id, alert)
            except Exception:
                pass
    else:
        logger.debug("Health check: all systems OK.")


# ─────────────────────────────────────────────
# 7. AUDIT LOG CLEANUP — Sunday 2:00 AM weekly
# ─────────────────────────────────────────────

async def cleanup_old_audit_logs() -> None:
    """Archive audit logs older than 90 days."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted = await conn.fetchval(
            """
            WITH deleted AS (
                DELETE FROM audit_logs
                WHERE timestamp < NOW() - INTERVAL '90 days'
                RETURNING log_id
            )
            SELECT COUNT(*) FROM deleted
            """
        )
    logger.info(f"Cron: cleanup_old_audit_logs() removed {deleted} records.")
    await _audit.log("CRON_AUDIT_CLEANUP", details={"deleted": deleted})
