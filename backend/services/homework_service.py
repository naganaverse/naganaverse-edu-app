"""
services/homework_service.py
─────────────────────────────────────────────────────────────
Homework Engine.

Features:
  - Send homework to a class (stored permanently)
  - Custom feed: teacher manually specifies date
  - Today's homework for students
  - Archived history (Year → Month → Subject)
  - Student telegram IDs fetched for immediate broadcast
─────────────────────────────────────────────────────────────
"""

from datetime import date
from typing import List, Optional

from loguru import logger

from database.models.homework_model import Homework
from database.repositories.homework_repo import HomeworkRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.user_repo_security import AuditLogRepository

_hw_repo = HomeworkRepository()
_student_repo = StudentRepository()
_audit = AuditLogRepository()


async def send_homework(
    org_id: str,
    class_name: str,
    subject_name: str,
    teacher_id: str,
    description: str,
    homework_date: date = None,
) -> dict:
    """
    Create a homework record and return student telegram IDs for broadcast.

    Returns:
        {
          "success": True,
          "homework": Homework,
          "student_telegram_ids": [int, ...],
          "message": str,
        }
    """
    if homework_date is None:
        homework_date = date.today()

    hw = Homework(
        org_id=org_id,
        class_name=class_name,
        subject_name=subject_name,
        teacher_id=teacher_id,
        description=description,
        date=homework_date,
    )
    saved = await _hw_repo.create(hw)

    # Fetch students to notify
    students = await _student_repo.get_by_class(org_id, class_name)
    telegram_ids = [s.telegram_id for s in students if s.telegram_id]

    await _audit.log(
        "HOMEWORK_SENT",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={
            "class": class_name, "subject": subject_name,
            "date": str(homework_date), "students_notified": len(telegram_ids),
        },
    )

    logger.info(
        f"Homework sent | org={org_id} | class={class_name} "
        f"| subject={subject_name} | notifying {len(telegram_ids)} students"
    )

    return {
        "success": True,
        "homework": saved,
        "student_telegram_ids": telegram_ids,
        "message": (
            f"✅ <b>Homework Sent Successfully</b>\n\n"
            f"📚 Class: {class_name}\n"
            f"📖 Subject: {subject_name}\n"
            f"📅 Date: {homework_date.strftime('%d %b %Y')}\n"
            f"👥 Students notified: {len(telegram_ids)}"
        ),
    }


async def get_today_homework(org_id: str, class_name: str) -> str:
    """
    Fetch today's homework for a student.
    Groups by subject.
    """
    records = await _hw_repo.get_today(org_id, class_name)

    if not records:
        return "📌 No homework assigned for today! 🎉"

    lines = [f"📌 <b>Today's Homework</b>\n📅 {date.today().strftime('%d %b %Y')}\n"]
    for hw in records:
        lines.append(f"📖 <b>{hw.subject_name}</b>\n{hw.description}\n")

    return "\n".join(lines)


async def get_homework_history(org_id: str, class_name: str, limit: int = 10) -> str:
    """
    Previous homework — last `limit` entries.
    Displayed as archive: date + subject + description.
    """
    records = await _hw_repo.get_history(org_id, class_name, limit)

    if not records:
        return "📚 No homework history found."

    lines = ["📚 <b>Homework History</b>\n"]
    current_month = None

    for hw in records:
        month_label = hw.date.strftime("%B %Y")
        if month_label != current_month:
            lines.append(f"\n🗓 <b>{month_label}</b>")
            current_month = month_label
        lines.append(
            f"  📖 {hw.subject_name} — {hw.date.strftime('%d %b')}\n"
            f"  {hw.description[:80]}{'...' if len(hw.description) > 80 else ''}\n"
        )

    return "\n".join(lines)


async def get_teacher_homework_history(teacher_id: str, org_id: str) -> str:
    """Homework history view for teacher's own sent homework."""
    records = await _hw_repo.get_by_teacher(teacher_id, org_id)

    if not records:
        return "📋 No homework sent yet."

    lines = ["📋 <b>Your Homework History</b>\n"]
    for hw in records:
        lines.append(
            f"📅 {hw.date.strftime('%d %b %Y')} | "
            f"📚 {hw.class_name} | "
            f"📖 {hw.subject_name}\n"
            f"  {hw.description[:60]}{'...' if len(hw.description) > 60 else ''}\n"
        )

    return "\n".join(lines)
