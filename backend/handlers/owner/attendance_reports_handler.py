"""
handlers/owner/attendance_reports_handler.py
─────────────────────────────────────────────────────────────
Owner attendance reports:
  - Class-wise summary → send to parents
  - Student-wise lookup by ID/name → send to single parent
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.filters import IsOwner
from services.attendance_service import get_class_attendance_report
from services.notification_service import send_attendance_to_parents
from keyboards.owner_kb import class_select_keyboard, attendance_report_actions_keyboard
from keyboards.common_kb import nav_only_keyboard, nav_row
from database.repositories.student_repo import StudentRepository
from database.repositories.attendance_repo import AttendanceRepository

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_student_repo = StudentRepository()
_attendance_repo = AttendanceRepository()


class AttendanceReportFSM(StatesGroup):
    select_type   = State()
    select_class  = State()
    lookup_student = State()


@router.callback_query(F.data == "owner:attendance_reports")
async def cb_att_reports_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(AttendanceReportFSM.select_type)

    await callback.message.edit_text(
        "📊 <b>Attendance Reports</b>\n\nChoose report type:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Class-wise Report",   callback_data="att_rpt:class")],
            [InlineKeyboardButton(text="👤 Student Attendance",  callback_data="att_rpt:student")],
            nav_row(),
        ]),
    )


# ── Class-wise ────────────────────────────────────────────

@router.callback_query(AttendanceReportFSM.select_type, F.data == "att_rpt:class")
async def cb_att_class_select(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    from database.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT class FROM students WHERE org_id = $1 ORDER BY class",
            user_session["org_id"],
        )
    classes = [r["class"] for r in rows]
    if not classes:
        await callback.message.edit_text("❌ No students added yet.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    await state.update_data(report_type="class")
    await state.set_state(AttendanceReportFSM.select_class)
    await callback.message.edit_text(
        "📊 <b>Class-wise Attendance</b>\n\nSelect a class:",
        reply_markup=class_select_keyboard(classes, "att_cls"),
    )


@router.callback_query(AttendanceReportFSM.select_class, F.data.startswith("att_cls:"))
async def cb_att_class_report(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    org_id     = user_session["org_id"]

    report = await get_class_attendance_report(org_id, class_name)
    await state.clear()

    if not report["success"]:
        await callback.message.edit_text(report["message"], reply_markup=nav_only_keyboard())
        return

    highest = report.get("highest", {})
    lowest  = report.get("lowest", {})

    lines = [
        f"📊 <b>Attendance Report — {class_name}</b>\n",
        f"👥 Total Students: {report['total_students']}\n",
        f"🏆 Highest: {highest.get('name','—')} — {highest.get('percentage',0)}%",
        f"📉 Lowest:  {lowest.get('name','—')} — {lowest.get('percentage',0)}%\n",
        "<b>All Students:</b>",
    ]
    for s in report["report"]:
        bar = "█" * int(s["percentage"] / 10) + "░" * (10 - int(s["percentage"] / 10))
        lines.append(f"  {s['name']}: {bar} {s['percentage']}%")

    text = "\n".join(lines)
    if len(text) > 3800:
        text = text[:3800] + "\n..."

    await callback.message.edit_text(
        text,
        reply_markup=attendance_report_actions_keyboard(class_name),
    )


@router.callback_query(F.data.startswith("owner:att_send_parents:"))
async def cb_send_att_to_parents(
    callback: CallbackQuery, user_session: dict
) -> None:
    await callback.answer("Sending to parents...")
    class_name = callback.data.split(":", 2)[2]
    result = await send_attendance_to_parents(
        org_id=user_session["org_id"],
        class_name=class_name,
        triggered_by=user_session["user_id"],
    )
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


# ── Student-wise ──────────────────────────────────────────

@router.callback_query(AttendanceReportFSM.select_type, F.data == "att_rpt:student")
async def cb_att_student_lookup(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AttendanceReportFSM.lookup_student)
    await callback.message.edit_text(
        "👤 <b>Student Attendance</b>\n\n"
        "Enter <b>Student ID</b>:\n<i>Example: STD102</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AttendanceReportFSM.lookup_student)
async def msg_att_student_id(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    std_id   = message.text.strip().upper()
    org_id   = user_session["org_id"]
    student  = await _student_repo.get_by_student_id(std_id, org_id)

    if not student:
        await message.answer(f"❌ Student <code>{std_id}</code> not found.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    records = await _attendance_repo.get_student_attendance(std_id, org_id)
    await state.clear()

    if not records:
        await message.answer(
            f"👤 {student.name}\n📊 No attendance records found yet.",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = [f"👤 <b>{student.name}</b> — {std_id}\n📚 {student.class_name}\n"]
    for r in records:
        bar = "█" * int(r["percentage"] / 10) + "░" * (10 - int(r["percentage"] / 10))
        lines.append(f"📖 {r['subject_name']}: {bar} {r['percentage']}%")

    send_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📲 Send to Parent",
            callback_data=f"owner:att_send_one:{std_id}",
        )],
        nav_row(),
    ])

    await message.answer("\n".join(lines), reply_markup=send_btn)


@router.callback_query(F.data.startswith("owner:att_send_one:"))
async def cb_send_single_att(
    callback: CallbackQuery, user_session: dict
) -> None:
    await callback.answer("Sending...")
    std_id  = callback.data.split(":", 2)[2]
    org_id  = user_session["org_id"]
    student = await _student_repo.get_by_student_id(std_id, org_id)

    if not student or not student.parent_phone:
        await callback.message.edit_text("❌ Parent phone not available.", reply_markup=nav_only_keyboard())
        return

    records = await _attendance_repo.get_student_attendance(std_id, org_id)
    summary = "\n".join(
        f"{r['subject_name']}: {r['percentage']}% ({r['present_count']}/{r['total_classes']})"
        for r in records
    )
    msg = (
        f"📊 *Naganaverse Attendance Report*\n\n"
        f"Student: {student.name}\n"
        f"Class: {student.class_name}\n\n"
        f"{summary}"
    )

    from services.notification_service import _send_whatsapp, _log_notification
    await _send_whatsapp(student.parent_phone, msg)
    await _log_notification(org_id, std_id, student.parent_phone, "attendance_report", msg)

    await callback.message.edit_text(
        f"✅ Attendance report sent to parent of {student.name}.",
        reply_markup=nav_only_keyboard(),
    )
