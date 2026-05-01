"""
handlers/teacher/attendance_handler.py
─────────────────────────────────────────────────────────────
Paginated Attendance System — spec compliant.

FSM States:
  select_class    → tap assigned class
  select_subject  → tap subject
  awaiting_date   → manual feed: enter DD-MM-YYYY
  mark_absent     → paginated toggle (10 students/page)
  confirm         → confirmation screen before save

Page size: 10 students per page
All students = Present by default
Teacher taps to mark Absent (❌)

Callbacks:
  att_toggle:{student_id}  — toggle present/absent
  att_page:next            — next page
  att_page:prev            — previous page
  att_all_present          — reset page to all present
  att_submit               — go to confirmation
  att_confirm_yes          — final save to DB
  att_edit                 — go back to last page from confirm

Security:
  - IsTeacher filter on all handlers
  - class_name validated against teacher's assigned_classes
  - org_id from session on every DB call
─────────────────────────────────────────────────────────────
"""

from datetime import date, datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger

from core.filters import IsTeacher
from services.attendance_service import take_attendance, get_teacher_attendance_history
from services.teacher_service import get_assigned_classes, get_assigned_subjects
from services.notification_service import send_absence_alert
from keyboards.teacher_kb import (
    class_select_keyboard,
    subject_select_keyboard,
    attendance_menu_keyboard,
    paginated_attendance_keyboard,
)
from keyboards.common_kb import nav_only_keyboard
from database.repositories.student_repo import StudentRepository

router = Router()
router.message.filter(IsTeacher())
router.callback_query.filter(IsTeacher())

_student_repo = StudentRepository()

PAGE_SIZE = 10


class AttendanceFSM(StatesGroup):
    select_class   = State()
    select_subject = State()
    awaiting_date  = State()
    mark_absent    = State()
    confirm        = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "teacher:attendance")
async def cb_attendance_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📋 <b>Attendance</b>\n\nChoose an option:",
        reply_markup=attendance_menu_keyboard(),
    )


@router.callback_query(F.data.in_({"teacher:att_take", "teacher:att_manual"}))
async def cb_start_attendance(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    await callback.answer()
    mode       = "manual" if callback.data == "teacher:att_manual" else "take"
    org_id     = user_session["org_id"]
    teacher_id = user_session["user_id"]

    classes = await get_assigned_classes(teacher_id, org_id)
    if not classes:
        await callback.message.edit_text(
            "❌ No classes assigned to you. Contact your institution owner.",
            reply_markup=nav_only_keyboard(),
        )
        return

    await state.set_state(AttendanceFSM.select_class)
    await state.update_data(mode=mode)

    title = "Manual Attendance Feed" if mode == "manual" else "Take Attendance"
    await callback.message.edit_text(
        f"📋 <b>{title}</b>\n\nStep 1 — Select Class:",
        reply_markup=class_select_keyboard(classes, "att_class"),
    )


# ── State 1: Class ────────────────────────────────────────

@router.callback_query(AttendanceFSM.select_class, F.data.startswith("att_class:"))
async def cb_att_class(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    org_id     = user_session["org_id"]
    teacher_id = user_session["user_id"]

    assigned = await get_assigned_classes(teacher_id, org_id)
    if class_name not in assigned:
        await callback.message.edit_text(
            "❌ You are not assigned to this class.",
            reply_markup=nav_only_keyboard(),
        )
        await state.clear()
        return

    subjects = await get_assigned_subjects(teacher_id, org_id)
    await state.update_data(class_name=class_name)
    await state.set_state(AttendanceFSM.select_subject)

    await callback.message.edit_text(
        f"📋 <b>Attendance</b>\n"
        f"📚 Class: <b>{class_name}</b>\n\n"
        "Step 2 — Select Subject:",
        reply_markup=subject_select_keyboard(subjects, "att_subject"),
    )


# ── State 2: Subject ──────────────────────────────────────

@router.callback_query(AttendanceFSM.select_subject, F.data.startswith("att_subject:"))
async def cb_att_subject(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    subject_name = callback.data.split(":", 1)[1]
    data         = await state.get_data()
    class_name   = data["class_name"]
    org_id       = user_session["org_id"]
    mode         = data.get("mode", "take")

    # 🛡️ GUARDRAIL: Check if attendance already exists for today before proceeding
    if mode == "take":
        if await _is_attendance_taken(org_id, class_name, subject_name, date.today()):
            await callback.answer(
                f"⚠️ Attendance for {subject_name} has ALREADY been submitted today!", 
                show_alert=True
            )
            return

    await callback.answer()

    students = await _student_repo.get_by_class(org_id, class_name)
    if not students:
        await callback.message.edit_text(
            f"❌ No students found in <b>{class_name}</b>.",
            reply_markup=nav_only_keyboard(),
        )
        await state.clear()
        return

    # Store as plain dicts for Redis JSON serialisation
    student_list = [
        {
            "student_id":  s.student_id,
            "name":        s.name,
            "roll_number": s.roll_number or "",
        }
        for s in students
    ]
    total_pages = max(1, (len(student_list) + PAGE_SIZE - 1) // PAGE_SIZE)

    await state.update_data(
        subject_name=subject_name,
        students=student_list,
        absent_ids=[],
        current_page=0,
        total_pages=total_pages,
    )

    if mode == "manual":
        await state.set_state(AttendanceFSM.awaiting_date)
        await callback.message.edit_text(
            f"📋 <b>Manual Attendance Feed</b>\n"
            f"📚 {class_name} | 📖 {subject_name}\n\n"
            "Enter attendance date:\n"
            "<i>Format: DD-MM-YYYY  e.g. 15-03-2025</i>",
            reply_markup=nav_only_keyboard(),
        )
        return

    await state.update_data(attendance_date=str(date.today()))
    await state.set_state(AttendanceFSM.mark_absent)
    await _show_page(callback.message, await state.get_data(), edit=True)


# ── State 2.5: Manual date ────────────────────────────────

@router.message(AttendanceFSM.awaiting_date)
async def msg_manual_date(message: Message, state: FSMContext, user_session: dict) -> None:
    raw = message.text.strip()
    try:
        parsed = datetime.strptime(raw, "%d-%m-%Y").date()
    except ValueError:
        await message.answer(
            "❌ Wrong format. Use DD-MM-YYYY\n<i>Example: 15-03-2025</i>",
            reply_markup=nav_only_keyboard(),
        )
        return

    data         = await state.get_data()
    org_id       = user_session["org_id"]
    class_name   = data["class_name"]
    subject_name = data["subject_name"]

    # 🛡️ GUARDRAIL: Check if manual date already exists
    if await _is_attendance_taken(org_id, class_name, subject_name, parsed):
        await message.answer(
            f"⚠️ Attendance for {parsed.strftime('%d-%m-%Y')} has already been submitted!\n"
            "Please enter a different date, or tap Back to cancel.",
            reply_markup=nav_only_keyboard()
        )
        return

    await state.update_data(attendance_date=str(parsed))
    await state.set_state(AttendanceFSM.mark_absent)
    data = await state.get_data()
    await _show_page(message, data, edit=False)


# ── State 3: Toggle student ───────────────────────────────

@router.callback_query(AttendanceFSM.mark_absent, F.data.startswith("att_toggle:"))
async def cb_toggle_student(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    student_id = callback.data.split(":", 1)[1]
    data       = await state.get_data()
    absent_ids = list(data.get("absent_ids", []))

    if student_id in absent_ids:
        absent_ids.remove(student_id)
    else:
        absent_ids.append(student_id)

    await state.update_data(absent_ids=absent_ids)
    data = await state.get_data()
    await _show_page(callback.message, data, edit=True)


# ── Pagination: Next ──────────────────────────────────────

@router.callback_query(AttendanceFSM.mark_absent, F.data == "att_page:next")
async def cb_page_next(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data         = await state.get_data()
    current_page = data.get("current_page", 0)
    total_pages  = data.get("total_pages", 1)

    if current_page < total_pages - 1:
        await state.update_data(current_page=current_page + 1)
        data = await state.get_data()
    await _show_page(callback.message, data, edit=True)


# ── Pagination: Back ──────────────────────────────────────

@router.callback_query(AttendanceFSM.mark_absent, F.data == "att_page:prev")
async def cb_page_prev(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data         = await state.get_data()
    current_page = data.get("current_page", 0)

    if current_page > 0:
        await state.update_data(current_page=current_page - 1)
        data = await state.get_data()
    await _show_page(callback.message, data, edit=True)


# ── Mark All Present (current page) ──────────────────────

@router.callback_query(AttendanceFSM.mark_absent, F.data == "att_all_present")
async def cb_all_present(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("✅ All marked present on this page")
    data         = await state.get_data()
    current_page = data.get("current_page", 0)
    students     = data.get("students", [])
    absent_ids   = list(data.get("absent_ids", []))

    # Get student IDs on current page
    start = current_page * PAGE_SIZE
    end   = start + PAGE_SIZE
    page_ids = {s["student_id"] for s in students[start:end]}

    # Remove all page students from absent list
    absent_ids = [sid for sid in absent_ids if sid not in page_ids]

    await state.update_data(absent_ids=absent_ids)
    data = await state.get_data()
    await _show_page(callback.message, data, edit=True)


# ── Submit → Confirmation screen ──────────────────────────

@router.callback_query(AttendanceFSM.mark_absent, F.data == "att_submit")
async def cb_att_submit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data         = await state.get_data()
    absent_ids   = data.get("absent_ids", [])
    students     = data.get("students", [])
    class_name   = data["class_name"]
    subject_name = data["subject_name"]
    att_date     = data.get("attendance_date", str(date.today()))
    total        = len(students)
    absent_count = len(absent_ids)
    present_count = total - absent_count

    # Build absent names list
    sid_to_student = {s["student_id"]: s for s in students}
    if absent_ids:
        absent_lines = "\n".join(
            f"  ❌ {sid_to_student.get(sid, {}).get('roll_number', '')}. "
            f"{sid_to_student.get(sid, {}).get('name', sid)}"
            for sid in absent_ids
        )
        absent_text = f"<b>Absent Students:</b>\n{absent_lines}"
    else:
        absent_text = "✅ <b>All students are present!</b>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Edit",    callback_data="att_edit"),
            InlineKeyboardButton(text="✅ Confirm", callback_data="att_confirm_yes"),
        ],
    ])

    await state.set_state(AttendanceFSM.confirm)
    await callback.message.edit_text(
        f"📋 <b>Confirm Attendance</b>\n\n"
        f"📚 {class_name} | 📖 {subject_name}\n"
        f"📅 Date: {att_date}\n\n"
        f"👥 Total: {total}  ✅ Present: {present_count}  ❌ Absent: {absent_count}\n\n"
        f"{absent_text}",
        reply_markup=kb,
    )


# ── Edit → Back to last page ──────────────────────────────

@router.callback_query(AttendanceFSM.confirm, F.data == "att_edit")
async def cb_att_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AttendanceFSM.mark_absent)
    data = await state.get_data()
    # Go to last page so teacher sees where they left off
    total_pages = data.get("total_pages", 1)
    await state.update_data(current_page=total_pages - 1)
    data = await state.get_data()
    await _show_page(callback.message, data, edit=True)


# ── Final Confirm → Save to DB ────────────────────────────

@router.callback_query(AttendanceFSM.confirm, F.data == "att_confirm_yes")
async def cb_att_confirmed(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    await callback.answer("Saving...")
    data         = await state.get_data()
    org_id       = user_session["org_id"]
    teacher_id   = user_session["user_id"]
    class_name   = data["class_name"]
    subject_name = data["subject_name"]
    absent_ids   = data.get("absent_ids", [])
    att_date     = datetime.strptime(
        data.get("attendance_date", str(date.today())), "%Y-%m-%d"
    ).date()

    result = await take_attendance(
        org_id=org_id,
        class_name=class_name,
        subject_name=subject_name,
        teacher_id=teacher_id,
        absent_student_ids=absent_ids,
        attendance_date=att_date,
    )

    await state.clear()
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())

    # Fire absence alerts to parents (non-blocking)
    if absent_ids and result["success"]:
        students_db = await _student_repo.get_by_class(org_id, class_name)
        sm = {s.student_id: s for s in students_db}
        for sid in absent_ids:
            s = sm.get(sid)
            if s and s.parent_phone:
                await send_absence_alert(
                    org_id=org_id,
                    student_id=sid,
                    student_name=s.name,
                    parent_phone=s.parent_phone,
                    class_name=class_name,
                    subject_name=subject_name,
                    date_str=str(att_date),
                )


# ── History ───────────────────────────────────────────────

@router.callback_query(F.data == "teacher:att_history")
async def cb_att_history(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    history = await get_teacher_attendance_history(
        user_session["user_id"], user_session["org_id"]
    )
    if not history:
        await callback.message.edit_text(
            "📊 No attendance records yet.", reply_markup=nav_only_keyboard()
        )
        return

    lines = ["📊 <b>Attendance History</b>\n"]
    for r in history:
        lines.append(
            f"📅 {r['date']} | 📚 {r['class_name']} | 📖 {r['subject_name']}\n"
            f"   ✅ Present: {r['present']}  ❌ Absent: {r['absent']}\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=nav_only_keyboard())


# ── Helpers ───────────────────────────────────────────────

async def _is_attendance_taken(org_id: str, class_name: str, subject_name: str, att_date: date) -> bool:
    """Safely check the DB directly to see if a session already exists to prevent duplicates."""
    from database.connection import get_pool
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Assumes table is attendance_sessions based on standard structure
            row = await conn.fetchrow(
                "SELECT 1 FROM attendance_sessions WHERE org_id = $1 AND class_name = $2 AND subject_name = $3 AND date = $4",
                org_id, class_name, subject_name, att_date
            )
            return bool(row)
    except Exception as e:
        logger.error(f"Error checking attendance exists: {e}")
        return False


async def _show_page(msg, data: dict, edit: bool = False) -> None:
    """Render current page of students with toggle buttons."""
    students     = data.get("students", [])
    absent_ids   = set(data.get("absent_ids", []))
    current_page = data.get("current_page", 0)
    total_pages  = data.get("total_pages", 1)
    class_name   = data.get("class_name", "")
    subject_name = data.get("subject_name", "")
    att_date     = data.get("attendance_date", str(date.today()))

    # Slice current page
    start        = current_page * PAGE_SIZE
    end          = start + PAGE_SIZE
    page_students = students[start:end]

    absent_count  = len(absent_ids)
    total         = len(students)

    text = (
        f"📋 <b>{class_name} — {subject_name}</b>\n"
        f"📅 {att_date}  |  Page {current_page + 1}/{total_pages}\n\n"
        f"👥 Total: {total}  ✅ Present: {total - absent_count}  ❌ Absent: {absent_count}\n\n"
        f"Tap a student to toggle absent:"
    )

    kb = paginated_attendance_keyboard(
        students=page_students,
        absent_ids=absent_ids,
        current_page=current_page,
        total_pages=total_pages,
    )

    try:
        if edit:
            await msg.edit_text(text, reply_markup=kb)
        else:
            await msg.answer(text, reply_markup=kb)
    except Exception:
        await msg.answer(text, reply_markup=kb)
