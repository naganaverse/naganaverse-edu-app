"""
services/teacher_service.py
─────────────────────────────────────────────────────────────
Teacher academic operations.

Visibility constraints:
  - Teacher sees ONLY their assigned classes and subjects
  - Cannot edit content uploaded by other teachers
  - All queries filtered by org_id + teacher's assigned_classes
─────────────────────────────────────────────────────────────
"""

from typing import List, Optional

from database.repositories.student_repo import StudentRepository
from database.repositories.teacher_repo import TeacherRepository
from database.repositories.attendance_repo import AttendanceRepository

_student_repo = StudentRepository()
_teacher_repo = TeacherRepository()
_attendance_repo = AttendanceRepository()


async def get_teacher_profile(teacher_id: str, org_id: str) -> str:
    """Returns formatted teacher profile."""
    teacher = await _teacher_repo.get_by_teacher_id(teacher_id, org_id)
    if not teacher:
        return "❌ Profile not found."

    return (
        f"👤 <b>Teacher Profile</b>\n\n"
        f"🆔 ID: {teacher.teacher_id}\n"
        f"📛 Name: {teacher.name}\n"
        f"📖 Subjects: {', '.join(teacher.subjects) or '—'}\n"
        f"📚 Classes: {', '.join(teacher.assigned_classes) or '—'}\n"
        f"📞 Phone: {teacher.phone or '—'}"
    )


async def get_assigned_classes(teacher_id: str, org_id: str) -> List[str]:
    """Returns list of classes assigned to a teacher."""
    teacher = await _teacher_repo.get_by_teacher_id(teacher_id, org_id)
    return teacher.assigned_classes if teacher else []


async def get_assigned_subjects(teacher_id: str, org_id: str) -> List[str]:
    """Returns list of subjects the teacher handles."""
    teacher = await _teacher_repo.get_by_teacher_id(teacher_id, org_id)
    return teacher.subjects if teacher else []


async def get_students_in_class(
    teacher_id: str, org_id: str, class_name: str
) -> dict:
    """
    Returns numbered student list for a class.
    Validates teacher is assigned to this class.
    Used for attendance (teacher taps absent numbers).
    """
    assigned = await get_assigned_classes(teacher_id, org_id)
    if class_name not in assigned:
        return {
            "success": False,
            "message": "❌ You are not assigned to this class.",
            "students": [],
        }

    students = await _student_repo.get_by_class(org_id, class_name)
    return {
        "success": True,
        "students": students,
        "numbered_list": _format_numbered_list(students),
        "class_name": class_name,
    }


async def validate_class_access(teacher_id: str, org_id: str, class_name: str) -> bool:
    """Check if teacher is allowed to access a class."""
    assigned = await get_assigned_classes(teacher_id, org_id)
    return class_name in assigned


def _format_numbered_list(students) -> str:
    """Format student list as numbered for absent entry."""
    if not students:
        return "No students found."
    lines = ["👥 <b>Student List</b>\n"]
    for i, s in enumerate(students, 1):
        lines.append(f"{i}. {s.name}")
    lines.append(
        "\n📝 Enter absent student numbers separated by commas.\n"
        "Example: <code>2,4,7</code>\n"
        "Or send <code>0</code> if all are present."
    )
    return "\n".join(lines)
