"""
handlers/student/homework_handler.py
─────────────────────────────────────────────────────────────
Direct actions — no deep FSM needed.

Today Homework:
  Fetch homework WHERE org_id = ? AND class = ? AND date = TODAY
  Group by subject → display formatted

Homework History:
  Fetch last 10 entries → display grouped by month
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsStudent
from services.homework_service import get_today_homework, get_homework_history
from keyboards.student_kb import homework_menu_keyboard
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.callback_query.filter(IsStudent())


@router.callback_query(F.data == "student:homework_today")
async def cb_homework_today(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    await callback.answer()
    org_id     = user_session["org_id"]
    class_name = user_session.get("class_name", "")

    text = await get_today_homework(org_id, class_name)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from keyboards.common_kb import nav_row
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📚 Previous Homework",
            callback_data="student:homework_history"
        )],
        nav_row(),
    ])

    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "student:homework_history")
async def cb_homework_history(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    await callback.answer()
    org_id     = user_session["org_id"]
    class_name = user_session.get("class_name", "")

    text = await get_homework_history(org_id, class_name, limit=10)
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
