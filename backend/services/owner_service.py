"""
services/owner_service.py
─────────────────────────────────────────────────────────────
Owner — coaching management operations.

ID Generation:
  Students: STD + zero-padded number  e.g. STD001, STD002
  Teachers: TCH + zero-padded number  e.g. TCH001, TCH002

Owner creates IDs and passwords manually via the bot FSM flow.
All operations strictly scoped to org_id.
─────────────────────────────────────────────────────────────
"""

from typing import List, Optional

from loguru import logger

from core.security import hash_password
from database.models.student_model import Student
from database.models.teacher_model import Teacher
from database.repositories.student_repo import StudentRepository
from database.repositories.teacher_repo import TeacherRepository
from database.repositories.org_repo import OrgRepository
from database.repositories.attendance_repo import AttendanceRepository
from database.repositories.test_repo import TestRepository
from database.repositories.user_repo_security import AuditLogRepository

_student_repo = StudentRepository()
_teacher_repo = TeacherRepository()
_org_repo = OrgRepository()
_attendance_repo = AttendanceRepository()
_test_repo = TestRepository()
_audit = AuditLogRepository()


async def add_student(
    org_id: str,
    owner_id: str,
    student_id: str,
    name: str,
    class_name: str,
    roll_number: int,
    subjects: List[str],
    father_name: str,
    mother_name: str,
    parent_phone: str,
    password: str,
) -> dict:
    """Add a new student. ID and password provided by owner."""
    # Check institution student limit (max 1000)
    count = await _student_repo.count_by_org(org_id)
    if count >= 1000:
        return {
            "success": False,
            "message": "❌ Student limit reached (max 1000). Please contact support.",
        }

    # Check for duplicate student_id
    existing = await _student_repo.get_by_student_id(student_id.upper(), org_id)
    if existing:
        return {
            "success": False,
            "message": f"❌ Student ID <b>{student_id.upper()}</b> already exists.",
        }

    student = Student(
        org_id=org_id,
        student_id=student_id.upper(),
        name=name,
        class_name=class_name,
        roll_number=roll_number,
        subjects=subjects,
        father_name=father_name,
        mother_name=mother_name,
        parent_phone=parent_phone,
        password_hash=hash_password(password),
    )
    saved = await _student_repo.create(student)

    await _audit.log(
        "STUDENT_ADDED",
        user_id=owner_id, role="owner", org_id=org_id,
        details={"student_id": saved.student_id, "name": name, "class": class_name},
    )

    logger.info(f"Student added | org={org_id} | id={saved.student_id}")

    return {
        "success": True,
        "student": saved,
        "message": (
            f"✅ <b>Student Added Successfully</b>\n\n"
            f"👤 Name: {name}\n"
            f"🏫 Class: {class_name}\n"
            f"🔢 Roll No: {roll_number}\n"
            f"🆔 Login ID: <b>{saved.student_id}</b>"
        ),
    }


async def add_teacher(
    org_id: str,
    owner_id: str,
    teacher_id: str,
    name: str,
    subjects: List[str],
    assigned_classes: List[str],
    phone: str,
    password: str,
) -> dict:
    """Add a new teacher."""
    count = await _teacher_repo.count_by_org(org_id)
    if count >= 50:
        return {
            "success": False,
            "message": "❌ Teacher limit reached (max 50). Please contact support.",
        }

    existing = await _teacher_repo.get_by_teacher_id(teacher_id.upper(), org_id)
    if existing:
        return {
            "success": False,
            "message": f"❌ Teacher ID <b>{teacher_id.upper()}</b> already exists.",
        }

    teacher = Teacher(
        org_id=org_id,
        teacher_id=teacher_id.upper(),
        name=name,
        subjects=subjects,
        assigned_classes=assigned_classes,
        phone=phone,
        password_hash=hash_password(password),
    )
    saved = await _teacher_repo.create(teacher)

    await _audit.log(
        "TEACHER_ADDED",
        user_id=owner_id, role="owner", org_id=org_id,
        details={"teacher_id": saved.teacher_id, "name": name, "subjects": subjects},
    )

    return {
        "success": True,
        "teacher": saved,
        "message": (
            f"✅ <b>Teacher Added Successfully</b>\n\n"
            f"👤 Name: {name}\n"
            f"📖 Subjects: {', '.join(subjects)}\n"
            f"📚 Classes: {', '.join(assigned_classes)}\n"
            f"🆔 Login ID: <b>{saved.teacher_id}</b>"
        ),
    }


async def remove_student(org_id: str, owner_id: str, student_id: str) -> dict:
    deleted = await _student_repo.delete(student_id.upper(), org_id)
    if deleted:
        await _audit.log("STUDENT_REMOVED", user_id=owner_id, role="owner", org_id=org_id,
                         details={"student_id": student_id})
    return {
        "success": deleted,
        "message": "✅ Student removed." if deleted else "❌ Student not found.",
    }


async def remove_teacher(org_id: str, owner_id: str, teacher_id: str) -> dict:
    deleted = await _teacher_repo.delete(teacher_id.upper(), org_id)
    if deleted:
        await _audit.log("TEACHER_REMOVED", user_id=owner_id, role="owner", org_id=org_id,
                         details={"teacher_id": teacher_id})
    return {
        "success": deleted,
        "message": "✅ Teacher removed." if deleted else "❌ Teacher not found.",
    }


async def get_analytics(org_id: str) -> str:
    """Owner analytics dashboard."""
    student_count = await _student_repo.count_by_org(org_id)
    teacher_count = await _teacher_repo.count_by_org(org_id)
    org = await _org_repo.get_by_org_id(org_id)

    return (
        f"📈 <b>Analytics — {org.org_name if org else org_id}</b>\n\n"
        f"👥 Total Students: <b>{student_count}</b>\n"
        f"👨‍🏫 Total Teachers: <b>{teacher_count}</b>\n"
        f"📦 Plan: <b>{org.plan_type.title() if org else '—'}</b>"
    )
