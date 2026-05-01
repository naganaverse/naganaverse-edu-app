"""
engines/attendance_engine.py
─────────────────────────────────────────────────────────────
Core Attendance Engine.

Differs from attendance_service:
  - Service handles the bot UI interaction and FSM flow
  - Engine handles the raw data transformation, default-present
    logic, batch DB inserts, and cross-module analytics calculation

Exposed functions:
  process_attendance_feed()   — converts teacher input to records
  calculate_analytics()       — historical % per student per subject
  get_class_analytics()       — class-level summary for owner reports
─────────────────────────────────────────────────────────────
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

from loguru import logger

from database.connection import get_pool
from database.models.attendance_model import Attendance, AttendanceDetail
from database.repositories.attendance_repo import AttendanceRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.user_repo_security import AuditLogRepository

_attendance_repo = AttendanceRepository()
_student_repo    = StudentRepository()
_audit           = AuditLogRepository()


async def process_attendance_feed(
    org_id: str,
    class_name: str,
    subject_name: str,
    teacher_id: str,
    absent_input: str | List[str],
    attendance_date: date = None,
) -> dict:
    """
    Core attendance processing pipeline.

    Accepts either:
      - Raw string from teacher: "2,4,7"  (position numbers)
      - List of student_ids:     ["STD002","STD004","STD007"]

    Steps:
      1. Fetch all students in class
      2. Parse absent input into student_id set
      3. Apply default-present logic
      4. Save attendance session + per-student details
      5. Return structured result with counts

    Returns:
        {
          "success": bool,
          "attendance_id": str,
          "total": int,
          "present": int,
          "absent": int,
          "absent_students": [{"student_id": str, "name": str}],
        }
    """
    if attendance_date is None:
        attendance_date = date.today()

    all_students = await _student_repo.get_by_class(org_id, class_name)
    if not all_students:
        return {"success": False, "message": f"No students in class {class_name}"}

    # Parse absent input
    absent_ids = _parse_absent_input(absent_input, all_students)

    total         = len(all_students)
    absent_count  = len(absent_ids)
    present_count = total - absent_count

    # Create session header
    session = Attendance(
        org_id=org_id,
        class_name=class_name,
        subject_name=subject_name,
        teacher_id=teacher_id,
        date=attendance_date,
        present_count=present_count,
        absent_count=absent_count,
    )
    saved = await _attendance_repo.create_session(session)

    # Bulk insert per-student detail rows
    details = [
        AttendanceDetail(
            attendance_id=saved.attendance_id,
            student_id=s.student_id,
            status="absent" if s.student_id.upper() in absent_ids else "present",
        )
        for s in all_students
    ]
    await _attendance_repo.save_details(saved.attendance_id, details)

    absent_students = [
        {"student_id": s.student_id, "name": s.name, "parent_phone": s.parent_phone}
        for s in all_students
        if s.student_id.upper() in absent_ids
    ]

    await _audit.log(
        "ATTENDANCE_PROCESSED",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={
            "class": class_name, "subject": subject_name,
            "date": str(attendance_date), "present": present_count, "absent": absent_count,
        },
    )

    logger.info(
        f"Attendance processed | org={org_id} | {class_name}/{subject_name} "
        f"| {present_count}P/{absent_count}A/{total}T"
    )

    return {
        "success": True,
        "attendance_id": str(saved.attendance_id),
        "total": total,
        "present": present_count,
        "absent": absent_count,
        "absent_students": absent_students,
        "date": str(attendance_date),
    }


async def calculate_analytics(
    student_id: str,
    org_id: str,
) -> List[dict]:
    """
    Historical attendance percentage per subject for a student.

    Formula: attendance % = present_classes / total_classes × 100

    Returns list of:
        {
          "subject_name": str,
          "total_classes": int,
          "present_count": int,
          "absent_count": int,
          "percentage": float,
        }
    """
    records = await _attendance_repo.get_student_attendance(student_id, org_id)

    # Percentage already calculated in repo — enrich here if needed
    for r in records:
        r["status_label"] = _attendance_status_label(r["percentage"])

    return records


async def get_class_analytics(
    org_id: str,
    class_name: str,
) -> dict:
    """
    Class-level attendance analytics for owner reports.

    Returns:
        {
          "class_name": str,
          "total_students": int,
          "highest": {"name": str, "percentage": float},
          "lowest":  {"name": str, "percentage": float},
          "average": float,
          "students": [per-student records],
        }
    """
    report = await _attendance_repo.get_class_report(org_id, class_name)

    if not report:
        return {
            "class_name": class_name,
            "total_students": 0,
            "highest": None,
            "lowest": None,
            "average": 0.0,
            "students": [],
        }

    sorted_report = sorted(report, key=lambda x: x["percentage"], reverse=True)
    total         = len(sorted_report)
    avg           = round(sum(r["percentage"] for r in sorted_report) / total, 1) if total > 0 else 0.0

    return {
        "class_name": class_name,
        "total_students": total,
        "highest": sorted_report[0] if sorted_report else None,
        "lowest":  sorted_report[-1] if sorted_report else None,
        "average": avg,
        "students": sorted_report,
    }


async def get_unmarked_classes(org_id: str) -> List[dict]:
    """
    Called by scheduler at 7 PM to find classes where attendance
    has NOT been marked today.

    Returns list of {class_name, subject_name, teacher_id, telegram_id}.
    Used to send reminders to teachers.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT
                s.class     AS class_name,
                sub.subject_name,
                t.teacher_id,
                t.telegram_id,
                t.name      AS teacher_name
            FROM students s
            CROSS JOIN subjects sub
            JOIN teachers t ON t.org_id = s.org_id
            WHERE s.org_id = $1
              AND sub.org_id = $1
              AND NOT EXISTS (
                  SELECT 1 FROM attendance a
                  WHERE a.org_id = $1
                    AND a.class_name = s.class
                    AND a.subject_name = sub.subject_name
                    AND a.date = CURRENT_DATE
              )
            LIMIT 100
            """,
            org_id,
        )
    return [dict(r) for r in rows]


# ── Helpers ────────────────────────────────────────────────

def _parse_absent_input(
    absent_input: str | List[str],
    all_students: list,
) -> set:
    """
    Parse absent input into a set of uppercase student_ids.

    Accepts:
      - "0"          → all present
      - "2,4,7"      → position numbers (1-indexed)
      - ["STD002"]   → direct student_ids
    """
    if isinstance(absent_input, list):
        return {s.upper() for s in absent_input if s}

    raw = str(absent_input).strip()
    if not raw or raw == "0":
        return set()

    absent_ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            # Position number (1-indexed)
            idx = int(part) - 1
            if 0 <= idx < len(all_students):
                absent_ids.add(all_students[idx].student_id.upper())
        elif part:
            # Direct student_id
            absent_ids.add(part.upper())

    return absent_ids


def _attendance_status_label(pct: float) -> str:
    if pct >= 90:
        return "🟢 Excellent"
    elif pct >= 75:
        return "🟡 Good"
    elif pct >= 60:
        return "🟠 Average"
    else:
        return "🔴 Low"
