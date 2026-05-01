"""
handlers/student/profile_handler.py
─────────────────────────────────────────────────────────────
Direct action — fetches and displays student profile.
All data sourced from student's own record — no cross-student access.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsStudent
from keyboards.common_kb import nav_only_keyboard
from database.repositories.student_repo import StudentRepository

router = Router()
router.callback_query.filter(IsStudent())

_student_repo = StudentRepository()


@router.callback_query(F.data == "student:profile")
async def cb_student_profile(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    await callback.answer()
    student_id = user_session["user_id"]
    org_id     = user_session["org_id"]

    student = await _student_repo.get_by_student_id(student_id, org_id)
    if not student:
        await callback.message.edit_text(
            "❌ Profile not found. Please contact your institution.",
            reply_markup=nav_only_keyboard(),
        )
        return

    subjects_text = ", ".join(student.subjects) if student.subjects else "—"

    await callback.message.edit_text(
        f"👤 <b>My Profile</b>\n\n"
        f"📛 Name: <b>{student.name}</b>\n"
        f"🆔 Student ID: {student.student_id}\n"
        f"📚 Class: {student.class_name}\n"
        f"🔢 Roll No: {student.roll_number or '—'}\n"
        f"📖 Subjects: {subjects_text}\n\n"
        f"👨 Father: {student.father_name or '—'}\n"
        f"👩 Mother: {student.mother_name or '—'}\n"
        f"📞 Parent Phone: {student.parent_phone or '—'}",
        reply_markup=nav_only_keyboard(),
    )
