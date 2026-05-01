"""
handlers/teacher/students_handler.py
─────────────────────────────────────────────────────────────
Teacher: view students in their assigned classes only.
Security: class_name must be in teacher's assigned_classes.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from core.filters import IsTeacher
from services.teacher_service import get_assigned_classes, get_students_in_class
from keyboards.teacher_kb import class_select_keyboard
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.callback_query.filter(IsTeacher())


class StudentViewFSM(StatesGroup):
    select_class = State()


@router.callback_query(F.data == "teacher:view_students")
async def cb_students_start(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    await state.clear()
    classes = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if not classes:
        await callback.message.edit_text(
            "❌ No classes assigned.", reply_markup=nav_only_keyboard()
        )
        return
    await state.set_state(StudentViewFSM.select_class)
    await callback.message.edit_text(
        "👥 <b>View Students</b>\n\nSelect a class:",
        reply_markup=class_select_keyboard(classes, "sv_class"),
    )


@router.callback_query(StudentViewFSM.select_class, F.data.startswith("sv_class:"))
async def cb_sv_class(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]

    result = await get_students_in_class(
        user_session["user_id"], user_session["org_id"], class_name
    )
    await state.clear()

    if not result["success"]:
        await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())
        return

    await callback.message.edit_text(
        f"👥 <b>Students — {class_name}</b>\n\n{result['numbered_list']}",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(F.data == "teacher:settings")
async def cb_teacher_settings(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    await callback.message.edit_text(
        f"⚙️ <b>Teacher Settings</b>\n\n"
        f"🆔 ID: {user_session.get('user_id')}\n"
        f"📛 Name: {user_session.get('name')}\n"
        f"📖 Subjects: {', '.join(user_session.get('subjects', []))}\n"
        f"📚 Classes: {', '.join(user_session.get('assigned_classes', []))}\n\n"
        "To change password, contact your institution owner.",
        reply_markup=nav_only_keyboard(),
    )
