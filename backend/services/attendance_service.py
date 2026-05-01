"""
services/attendance_service.py
─────────────────────────────────────────────────────────────
Attendance Engine.

Core Logic:
  - Default-Present: All students in class = present by default
  - Teacher submits ONLY absent student IDs
  - System generates full present/absent records for everyone
  - Analytics: present_classes / total_classes × 100
─────────────────────────────────────────────────────────────
"""

from datetime import date
from typing import List

from loguru import logger

from database.models.attendance_model import Attendance, AttendanceDetail
from database.repositories.attendance_repo import AttendanceRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.user_repo_security import AuditLogRepository

_attendance_repo = AttendanceRepository()
_student_repo = StudentRepository()
_audit = AuditLogRepository()


async def take_attendance(
    org_id: str,
    class_name: str,
    subject_name: str,
    teacher_id: str,
    absent_student_ids: List[str],
    attendance_date: date = None,
) -> dict:
    """
    Core attendance-taking flow.

    1. Fetch full student list for the class
    2. Apply default-present logic
    3. Mark absent_student_ids as absent
    4. Save session header + all detail records
    5. Return confirmation summary
    """
    if attendance_date is None:
        attendance_date = date.today()

    # Fetch all students in this class
    all_students = await _student_repo.get_by_class(org_id, class_name)
    if not all_students:
        return {"success": False, "message": "❌ No students found in this class."}

    total = len(all_students)
    absent_set = set(s.upper() for s in absent_student_ids)
    absent_count = len(absent_set)
    present_count = total - absent_count

    # Create attendance session header
    session = Attendance(
        org_id=org_id,
        class_name=class_name,
        subject_name=subject_name,
        teacher_id=teacher_id,
        date=attendance_date,
        present_count=present_count,
        absent_count=absent_count,
    )
    saved_session = await _attendance_repo.create_session(session)

    # Build detail records for every student (default-present)
    details = [
        AttendanceDetail(
            attendance_id=saved_session.attendance_id,
            student_id=s.student_id,
            status="absent" if s.student_id.upper() in absent_set else "present",
        )
        for s in all_students
    ]
    await _attendance_repo.save_details(saved_session.attendance_id, details)

    await _audit.log(
        "ATTENDANCE_TAKEN",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={
            "class": class_name, "subject": subject_name,
            "date": str(attendance_date),
            "total": total, "present": present_count, "absent": absent_count,
        },
    )

    logger.info(
        f"Attendance saved | org={org_id} | class={class_name} "
        f"| subject={subject_name} | present={present_count}/{total}"
    )

    return {
        "success": True,
        "message": (
            f"✅ <b>Attendance Saved</b>\n\n"
            f"📚 Class: {class_name}\n"
            f"📖 Subject: {subject_name}\n"
            f"📅 Date: {attendance_date.strftime('%d %b %Y')}\n"
            f"✅ Present: {present_count}\n"
            f"❌ Absent: {absent_count}\n"
            f"👥 Total: {total}"
        ),
        "present_count": present_count,
        "absent_count": absent_count,
        "total": total,
    }


async def get_student_attendance_summary(student_id: str, org_id: str) -> str:
    """
    Returns formatted attendance summary for a student.
    Used by student dashboard Attendance button.
    """
    records = await _attendance_repo.get_student_attendance(student_id, org_id)

    if not records:
        return "📊 No attendance records found yet."

    lines = ["📊 <b>Attendance Summary</b>\n"]
    for r in records:
        bar = _percentage_bar(r["percentage"])
        lines.append(
            f"📖 <b>{r['subject_name']}</b>\n"
            f"   {bar} {r['percentage']}%\n"
            f"   Present: {r['present_count']} / {r['total_classes']}\n"
        )

    return "\n".join(lines)


async def get_class_attendance_report(org_id: str, class_name: str) -> dict:
    """
    Owner attendance report — all students in a class with %.
    Returns sorted list: highest attendance first.
    """
    report = await _attendance_repo.get_class_report(org_id, class_name)
    if not report:
        return {"success": False, "message": "No attendance data available."}

    sorted_report = sorted(report, key=lambda x: x["percentage"], reverse=True)

    highest = sorted_report[0] if sorted_report else None
    lowest = sorted_report[-1] if sorted_report else None

    return {
        "success": True,
        "report": sorted_report,
        "highest": highest,
        "lowest": lowest,
        "class_name": class_name,
        "total_students": len(report),
    }


async def get_teacher_attendance_history(teacher_id: str, org_id: str) -> List[dict]:
    """History of attendance sessions taken by a teacher."""
    records = await _attendance_repo.get_history_by_teacher(teacher_id, org_id)
    return [
        {
            "date": r.date.strftime("%d %b %Y"),
            "class_name": r.class_name,
            "subject_name": r.subject_name,
            "present": r.present_count,
            "absent": r.absent_count,
        }
        for r in records
    ]


def _percentage_bar(pct: float) -> str:
    """Simple ASCII progress bar for attendance %."""
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled)
