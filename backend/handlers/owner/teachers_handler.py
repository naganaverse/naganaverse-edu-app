"""
handlers/owner/teachers_handler.py
─────────────────────────────────────────────────────────────
Owner: Teachers management menu
  - Add Teacher → delegates to add_teacher_handler
  - View Teachers
  - Remove Teacher → confirm → delete
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsOwner
from services.owner_service import remove_teacher
from keyboards.owner_kb import teachers_menu_keyboard
from keyboards.common_kb import nav_only_keyboard, confirm_keyboard
from database.repositories.teacher_repo import TeacherRepository

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_teacher_repo = TeacherRepository()


class RemoveTeacherFSM(StatesGroup):
    enter_id = State()
    confirm  = State()


@router.callback_query(F.data == "owner:teachers")
async def cb_teachers_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "👨‍🏫 <b>Teachers</b>\n\nManage your teachers:",
        reply_markup=teachers_menu_keyboard(),
    )


@router.callback_query(F.data == "owner:teacher_view")
async def cb_view_teachers(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    teachers = await _teacher_repo.get_all_by_org(user_session["org_id"])

    if not teachers:
        await callback.message.edit_text(
            "👨‍🏫 No teachers added yet.",
            reply_markup=teachers_menu_keyboard(),
        )
        return

    lines = [f"👨‍🏫 <b>Teachers</b> ({len(teachers)} total)\n"]
    for t in teachers:
        lines.append(
            f"👤 <b>{t.name}</b> — <code>{t.teacher_id}</code>\n"
            f"   📖 {', '.join(t.subjects) or '—'} | 📚 {', '.join(t.assigned_classes) or '—'}\n"
        )

    await callback.message.edit_text("\n".join(lines), reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "owner:teacher_remove")
async def cb_remove_teacher_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(RemoveTeacherFSM.enter_id)
    await callback.message.edit_text(
        "🗑 <b>Remove Teacher</b>\n\nEnter <b>Teacher ID</b>:\n"
        "<i>Example: TCH102</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(RemoveTeacherFSM.enter_id)
async def msg_remove_teacher_id(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    tch_id  = message.text.strip().upper()
    teacher = await _teacher_repo.get_by_teacher_id(tch_id, user_session["org_id"])

    if not teacher:
        await message.answer(f"❌ Teacher <code>{tch_id}</code> not found.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    await state.update_data(tch_id=tch_id, tch_name=teacher.name)
    await state.set_state(RemoveTeacherFSM.confirm)
    await message.answer(
        f"⚠️ <b>Confirm Removal</b>\n\n"
        f"👤 {teacher.name} — <code>{tch_id}</code>\n"
        f"📖 {', '.join(teacher.subjects)}\n\n"
        "This will permanently remove the teacher.",
        reply_markup=confirm_keyboard("owner:teacher_remove_confirm", "nav:home"),
    )


@router.callback_query(RemoveTeacherFSM.confirm, F.data == "owner:teacher_remove_confirm")
async def cb_remove_teacher_confirm(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    data   = await state.get_data()
    result = await remove_teacher(
        org_id=user_session["org_id"],
        owner_id=user_session["user_id"],
        teacher_id=data["tch_id"],
    )
    await state.clear()
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "owner:teacher_edit")
async def cb_teacher_edit(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "✏️ To edit a teacher's subjects or classes, remove and re-add them.\n\n"
        "This ensures all attendance and test records remain consistent.",
        reply_markup=nav_only_keyboard(),
    )
