"""
handlers/student/attendance_handler.py
─────────────────────────────────────────────────────────────
Attendance Summary:
  - Per-subject attendance percentage with ASCII bar
  - Tap subject → detailed date-wise present/absent list

Security:
  - IsStudent filter
  - student_id + org_id on every query — no cross-student data
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from core.filters import IsStudent
from services.attendance_service import get_student_attendance_summary
from keyboards.common_kb import nav_only_keyboard, nav_row
from database.connection import get_pool

router = Router()
router.callback_query.filter(IsStudent())


@router.callback_query(F.data == "student:attendance")
async def cb_attendance_summary(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    await callback.answer()
    student_id = user_session["user_id"]
    org_id     = user_session["org_id"]

    from database.repositories.attendance_repo import AttendanceRepository
    repo    = AttendanceRepository()
    records = await repo.get_student_attendance(student_id, org_id)

    if not records:
        await callback.message.edit_text(
            "📊 No attendance records found yet.\n"
            "Attendance will appear here once your teacher marks it.",
            reply_markup=nav_only_keyboard(),
        )
        return

    # Summary with tap-to-detail buttons
    lines = ["📊 <b>My Attendance Summary</b>\n"]
    rows  = []

    for r in records:
        bar = _bar(r["percentage"])
        lines.append(
            f"📖 <b>{r['subject_name']}</b>\n"
            f"   {bar} <b>{r['percentage']}%</b>\n"
            f"   ✅ {r['present_count']} / {r['total_classes']} classes\n"
        )
        rows.append([
            InlineKeyboardButton(
                text=f"📖 {r['subject_name']} — Details",
                callback_data=f"att_detail:{r['subject_name']}",
            )
        ])

    rows.append(nav_row())

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("att_detail:"))
async def cb_attendance_detail(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    """Date-wise attendance detail for one subject."""
    await callback.answer()
    subject_name = callback.data.split(":", 1)[1]
    student_id   = user_session["user_id"]
    org_id       = user_session["org_id"]

    rows = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.date, ad.status
                FROM attendance_details ad
                JOIN attendance a ON a.attendance_id = ad.attendance_id
                WHERE ad.student_id = $1
                  AND a.org_id = $2
                  AND a.subject_name = $3
                ORDER BY a.date DESC
                LIMIT 30
                """,
                student_id, org_id, subject_name,
            )
    except Exception as e:
        logger.error(f"DB Error fetching attendance details for {student_id}: {e}")

    if not rows:
        await callback.message.edit_text(
            f"📖 <b>{subject_name}</b>\n\nNo records found yet.",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = [f"📖 <b>{subject_name} — Attendance Details</b>\n"]
    for r in rows:
        icon = "✅" if r["status"] == "present" else "❌"
        lines.append(f"  {icon} {r['date'].strftime('%d %b %Y')}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=nav_only_keyboard(),
    )


def _bar(pct: float) -> str:
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled)
  
