"""
engines/homework_engine.py
─────────────────────────────────────────────────────────────
Core Homework Engine.

Differs from homework_service:
  - Service handles bot UI, FSM, and direct user requests
  - Engine handles distribution binding, history archiving,
    and the structured retrieval pipeline used by the scheduler

Exposed functions:
  distribute_homework()     — binds homework to org/class/date
  fetch_todays_homework()   — retrieves for student dashboard
  archive_homework()        — structured Year→Month→Subject archive
  get_pending_reminders()   — used by scheduler at 8 PM
─────────────────────────────────────────────────────────────
"""

from datetime import date
from typing import Dict, List, Optional

from loguru import logger

from database.connection import get_pool
from database.models.homework_model import Homework
from database.repositories.homework_repo import HomeworkRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.user_repo_security import AuditLogRepository

_hw_repo      = HomeworkRepository()
_student_repo = StudentRepository()
_audit        = AuditLogRepository()


async def distribute_homework(
    org_id: str,
    class_name: str,
    subject_name: str,
    teacher_id: str,
    description: str,
    homework_date: date = None,
) -> dict:
    """
    Bind a homework assignment to org_id + class + date.
    Returns the saved homework record + list of student telegram_ids
    for the handler to broadcast.
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

    students   = await _student_repo.get_by_class(org_id, class_name)
    tg_ids     = [s.telegram_id for s in students if s.telegram_id]

    await _audit.log(
        "HOMEWORK_DISTRIBUTED",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={
            "class": class_name, "subject": subject_name,
            "date": str(homework_date), "students_to_notify": len(tg_ids),
        },
    )

    logger.info(
        f"Homework distributed | org={org_id} | {class_name}/{subject_name} "
        f"| {homework_date} | {len(tg_ids)} students"
    )

    return {
        "success": True,
        "homework": saved,
        "student_telegram_ids": tg_ids,
    }


async def fetch_todays_homework(
    org_id: str,
    class_name: str,
) -> List[dict]:
    """
    Retrieve today's homework for a class.
    Used by student dashboard "Today Homework" button.

    Returns list of {subject_name, description, date}.
    """
    records = await _hw_repo.get_today(org_id, class_name)
    return [
        {
            "subject_name": hw.subject_name,
            "description":  hw.description,
            "date":         str(hw.date),
        }
        for hw in records
    ]


async def archive_homework(
    org_id: str,
    class_name: str,
    limit: int = 50,
) -> Dict[str, Dict[str, List[dict]]]:
    """
    Organise homework history into Year → Month → Subject structure.

    Returns:
        {
          "2025": {
            "March": {
              "Physics": [{"description": str, "date": str}, ...],
              "Math":    [...],
            },
            "February": { ... },
          },
          "2024": { ... },
        }
    """
    records = await _hw_repo.get_history(org_id, class_name, limit=limit)

    archive: Dict[str, Dict[str, Dict[str, List]]] = {}

    for hw in records:
        year    = str(hw.date.year)
        month   = hw.date.strftime("%B")
        subject = hw.subject_name

        if year not in archive:
            archive[year] = {}
        if month not in archive[year]:
            archive[year][month] = {}
        if subject not in archive[year][month]:
            archive[year][month][subject] = []

        archive[year][month][subject].append({
            "description": hw.description,
            "date": hw.date.strftime("%d %b %Y"),
            "homework_id": str(hw.homework_id),
        })

    return archive


async def get_pending_reminders(org_id: str) -> List[dict]:
    """
    Called by scheduler homework_reminder_job() at 8 PM.
    Finds all classes that have homework assigned for today
    and returns student telegram_ids to notify.

    Returns list of:
        {
          "class_name": str,
          "subject_name": str,
          "description": str,
          "student_telegram_ids": [int, ...],
        }
    """
    pool = await get_pool()

    # Get today's homework grouped by class+subject
    async with pool.acquire() as conn:
        hw_rows = await conn.fetch(
            """
            SELECT class_name, subject_name, description
            FROM homework
            WHERE org_id = $1 AND date = CURRENT_DATE
            """,
            org_id,
        )

    if not hw_rows:
        return []

    result = []
    for row in hw_rows:
        students = await _student_repo.get_by_class(org_id, row["class_name"])
        tg_ids   = [s.telegram_id for s in students if s.telegram_id]
        if tg_ids:
            result.append({
                "class_name":           row["class_name"],
                "subject_name":         row["subject_name"],
                "description":          row["description"],
                "student_telegram_ids": tg_ids,
            })

    return result
