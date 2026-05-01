"""
handlers/owner/students_handler.py
─────────────────────────────────────────────────────────────
Owner: Students management menu
  - Add Student → delegates to add_student_handler
  - View Students → paginated list
  - Edit Student → select + update single field
  - Remove Student → confirm → delete
─────────────────────────────────────────────────────────────
"""

import math
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.filters import IsOwner
from services.owner_service import remove_student
from keyboards.owner_kb import students_menu_keyboard
from keyboards.common_kb import nav_only_keyboard, confirm_keyboard, nav_row
from database.repositories.student_repo import StudentRepository

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_student_repo = StudentRepository()
PAGE_SIZE = 10  # Number of students to show per page


class RemoveStudentFSM(StatesGroup):
    enter_id = State()
    confirm  = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "owner:students")
async def cb_students_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "👥 <b>Students</b>\n\nManage your students:",
        reply_markup=students_menu_keyboard(),
    )


# ── View Students (Paginated) ─────────────────────────────

@router.callback_query(F.data == "owner:student_view")
async def cb_view_students_start(callback: CallbackQuery, user_session: dict) -> None:
    # Always start on page 0 when first clicking "View Students"
    await _render_students_page(callback, user_session, page=0)


@router.callback_query(F.data.startswith("view_students_page:"))
async def cb_view_students_page(callback: CallbackQuery, user_session: dict) -> None:
    # Extract the requested page number from the callback data
    page = int(callback.data.split(":")[1])
    await _render_students_page(callback, user_session, page)


async def _render_students_page(callback: CallbackQuery, user_session: dict, page: int) -> None:
    org_id = user_session["org_id"]
    
    # Fetch all students for this org
    students = await _student_repo.get_all_by_org(org_id)
    
    if not students:
        await callback.message.edit_text(
            "👥 No students added yet.\nTap <b>Add Student</b> to get started.",
            reply_markup=students_menu_keyboard(),
        )
        await callback.answer()
        return
        
    total_students = len(students)
    total_pages = math.ceil(total_students / PAGE_SIZE)
    
    # Fallback just in case a page is requested out of bounds
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    # ✂️ Slice the array for the current page
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_students = students[start_idx:end_idx]
    
    # Build the message text
    lines = [f"👥 <b>Student List</b> (Total: {total_students})\n"]
    lines.append(f"<i>Page {page + 1} of {total_pages}</i>\n")
    
    for s in page_students:
        lines.append(f"👤 <b>{s.name}</b> | ID: <code>{s.student_id}</code>")
        lines.append(f"   Class: {s.class_name} | Phone: {s.parent_phone}\n")
        
    # Build Pagination Keyboard
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"view_students_page:{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"view_students_page:{page+1}"))
        
    kb_rows = []
    if buttons:
        kb_rows.append(buttons) # Add the prev/next row
        
    # Always provide a way to escape back to the students menu
    kb_rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="owner:students")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    text = "\n".join(lines)
    
    # Send the updated text and keyboard
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        # Ignore Telegram's "message is not modified" error if they click the same button rapidly
        pass 
        
    await callback.answer()


# ── Remove Student ────────────────────────────────────────

@router.callback_query(F.data == "owner:student_remove")
async def cb_remove_student_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(RemoveStudentFSM.enter_id)
    await callback.message.edit_text(
        "🗑 <b>Remove Student</b>\n\n"
        "Enter the <b>Student ID</b> to remove:\n"
        "<i>Example: STD102</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(RemoveStudentFSM.enter_id)
async def msg_remove_student_id(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    std_id   = message.text.strip().upper()
    org_id   = user_session["org_id"]
    student  = await _student_repo.get_by_student_id(std_id, org_id)

    if not student:
        await message.answer(
            f"❌ Student <code>{std_id}</code> not found in your institute.",
            reply_markup=nav_only_keyboard(),
        )
        await state.clear()
        return

    await state.update_data(std_id=std_id, std_name=student.name)
    await state.set_state(RemoveStudentFSM.confirm)
    await message.answer(
        f"⚠️ <b>Confirm Removal</b>\n\n"
        f"👤 Name: {student.name}\n"
        f"🆔 ID: {std_id}\n"
        f"📚 Class: {student.class_name}\n\n"
        "This will permanently remove the student.",
        reply_markup=confirm_keyboard("owner:student_remove_confirm", "nav:home"),
    )


@router.callback_query(RemoveStudentFSM.confirm, F.data == "owner:student_remove_confirm")
async def cb_remove_student_confirm(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    data   = await state.get_data()
    result = await remove_student(
        org_id=user_session["org_id"],
        owner_id=user_session["user_id"],
        student_id=data["std_id"],
    )
    await state.clear()
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


# ── Edit Student (field update) ───────────────────────────

class EditStudentFSM(StatesGroup):
    enter_id    = State()
    select_field = State()
    enter_value  = State()


@router.callback_query(F.data == "owner:student_edit")
async def cb_edit_student_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(EditStudentFSM.enter_id)
    await callback.message.edit_text(
        "✏️ <b>Edit Student</b>\n\nEnter <b>Student ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(EditStudentFSM.enter_id)
async def msg_edit_student_id(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    std_id  = message.text.strip().upper()
    student = await _student_repo.get_by_student_id(std_id, user_session["org_id"])
    if not student:
        await message.answer(f"❌ Student <code>{std_id}</code> not found.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    await state.update_data(std_id=std_id)
    await state.set_state(EditStudentFSM.select_field)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📛 Name",          callback_data="edit_std:name")],
        [InlineKeyboardButton(text="📚 Class",          callback_data="edit_std:class")],
        [InlineKeyboardButton(text="🔢 Roll Number",    callback_data="edit_std:roll_number")],
        [InlineKeyboardButton(text="📞 Parent Phone",   callback_data="edit_std:parent_phone")],
        nav_row(),
    ])
    await message.answer(
        f"✏️ <b>Edit: {student.name}</b>\n\nWhat to update?",
        reply_markup=kb,
    )


@router.callback_query(EditStudentFSM.select_field, F.data.startswith("edit_std:"))
async def cb_edit_field_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    field = callback.data.split(":", 1)[1]
    await state.update_data(field=field)
    await state.set_state(EditStudentFSM.enter_value)
    labels = {
        "name": "new name", "class": "new class",
        "roll_number": "new roll number", "parent_phone": "new parent phone",
    }
    await callback.message.edit_text(
        f"✏️ Enter {labels.get(field, field)}:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(EditStudentFSM.enter_value)
async def msg_edit_value(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    value = message.text.strip()
    data  = await state.get_data()
    await state.clear()

    kwargs = {data["field"]: value}
    updated = await _student_repo.update(data["std_id"], user_session["org_id"], **kwargs)

    await message.answer(
        "✅ Student updated successfully." if updated else "❌ Update failed.",
        reply_markup=nav_only_keyboard(),
)
