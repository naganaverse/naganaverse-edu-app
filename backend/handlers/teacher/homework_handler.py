"""
handlers/teacher/homework_handler.py
─────────────────────────────────────────────────────────────
FSM States:
  HW_SELECT_CLASS   → tap assigned class
  HW_SELECT_SUBJECT → tap subject
  HW_AWAITING_DATE  → custom feed only: enter DD-MM-YYYY
  HW_ENTER_TEXT     → type homework description
  HW_CONFIRM        → Confirm & Send / Edit

On confirmation:
  - homework_service saves record to DB
  - Broadcasts to all students in class who have Telegram linked
─────────────────────────────────────────────────────────────
"""

from datetime import date, datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsTeacher
from core.loader import bot
from services.homework_service import send_homework, get_teacher_homework_history
from services.teacher_service import get_assigned_classes, get_assigned_subjects
from keyboards.teacher_kb import (
    class_select_keyboard, subject_select_keyboard,
    homework_menu_keyboard, confirm_homework_keyboard,
)
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.message.filter(IsTeacher())
router.callback_query.filter(IsTeacher())


class HomeworkFSM(StatesGroup):
    select_class   = State()
    select_subject = State()
    awaiting_date  = State()
    enter_text     = State()
    confirm        = State()


@router.callback_query(F.data == "teacher:send_homework")
async def cb_homework_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📌 <b>Homework</b>\n\nChoose an option:",
        reply_markup=homework_menu_keyboard(),
    )


@router.callback_query(F.data.in_({"hw:send", "hw:custom"}))
async def cb_start_hw(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    mode = "custom" if callback.data == "hw:custom" else "send"
    classes = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if not classes:
        await callback.message.edit_text("❌ No classes assigned.", reply_markup=nav_only_keyboard())
        return
    await state.set_state(HomeworkFSM.select_class)
    await state.update_data(mode=mode)
    title = "Custom Homework Feed" if mode == "custom" else "Send Homework"
    await callback.message.edit_text(
        f"📌 <b>{title}</b>\n\nStep 1 — Select Class:",
        reply_markup=class_select_keyboard(classes, "hw_class"),
    )


@router.callback_query(HomeworkFSM.select_class, F.data.startswith("hw_class:"))
async def cb_hw_class(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    assigned = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if class_name not in assigned:
        await callback.message.edit_text("❌ Not your class.", reply_markup=nav_only_keyboard())
        await state.clear()
        return
    subjects = await get_assigned_subjects(user_session["user_id"], user_session["org_id"])
    await state.update_data(class_name=class_name)
    await state.set_state(HomeworkFSM.select_subject)
    await callback.message.edit_text(
        f"📌 <b>Homework</b>\n📚 Class: <b>{class_name}</b>\n\nStep 2 — Select Subject:",
        reply_markup=subject_select_keyboard(subjects, "hw_subject"),
    )


@router.callback_query(HomeworkFSM.select_subject, F.data.startswith("hw_subject:"))
async def cb_hw_subject(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    subject_name = callback.data.split(":", 1)[1]
    await state.update_data(subject_name=subject_name)
    data = await state.get_data()

    if data.get("mode") == "custom":
        await state.set_state(HomeworkFSM.awaiting_date)
        await callback.message.edit_text(
            f"📌 <b>Custom Feed</b>\n📚 {data['class_name']} | 📖 {subject_name}\n\n"
            "Enter homework date:\n<i>Format: DD-MM-YYYY</i>",
            reply_markup=nav_only_keyboard(),
        )
        return

    await state.update_data(hw_date=str(date.today()))
    await state.set_state(HomeworkFSM.enter_text)
    await callback.message.edit_text(
        f"📌 <b>Send Homework</b>\n📚 {data['class_name']} | 📖 {subject_name}\n\n"
        "Step 3 — Type the homework:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(HomeworkFSM.awaiting_date)
async def msg_hw_date(message: Message, state: FSMContext) -> None:
    try:
        parsed = datetime.strptime(message.text.strip(), "%d-%m-%Y").date()
    except ValueError:
        await message.answer("❌ Wrong format. Use DD-MM-YYYY", reply_markup=nav_only_keyboard())
        return
    await state.update_data(hw_date=str(parsed))
    await state.set_state(HomeworkFSM.enter_text)
    data = await state.get_data()
    await message.answer(
        f"📌 <b>Custom Feed</b>\n📚 {data['class_name']} | 📖 {data['subject_name']}\n"
        f"📅 Date: {message.text.strip()}\n\nEnter homework:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(HomeworkFSM.enter_text)
async def msg_hw_text(message: Message, state: FSMContext) -> None:
    hw_text = message.text.strip()
    if len(hw_text) < 5:
        await message.answer("❌ Too short. Describe the homework properly.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(hw_text=hw_text)
    await state.set_state(HomeworkFSM.confirm)
    data = await state.get_data()
    await message.answer(
        f"📌 <b>Confirm Homework</b>\n\n"
        f"📚 {data['class_name']} | 📖 {data['subject_name']}\n"
        f"📅 {data.get('hw_date', str(date.today()))}\n\n"
        f"📝 <b>Homework:</b>\n{hw_text}\n\nSend to students?",
        reply_markup=confirm_homework_keyboard(),
    )


@router.callback_query(HomeworkFSM.confirm, F.data == "hw:confirm")
async def cb_hw_send(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer("Sending...")
    data = await state.get_data()
    hw_date = datetime.strptime(data.get("hw_date", str(date.today())), "%Y-%m-%d").date()

    result = await send_homework(
        org_id=user_session["org_id"],
        class_name=data["class_name"],
        subject_name=data["subject_name"],
        teacher_id=user_session["user_id"],
        description=data["hw_text"],
        homework_date=hw_date,
    )
    await state.clear()
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())

    if result["success"]:
        broadcast = (
            f"📌 <b>New Homework</b>\n\n"
            f"📚 {data['class_name']} | 📖 {data['subject_name']}\n"
            f"📅 {hw_date.strftime('%d %b %Y')}\n\n"
            f"📝 {data['hw_text']}"
        )
        for tg_id in result.get("student_telegram_ids", []):
            try:
                await bot.send_message(tg_id, broadcast)
            except Exception:
                pass


@router.callback_query(HomeworkFSM.confirm, F.data == "hw:edit")
async def cb_hw_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(HomeworkFSM.enter_text)
    await callback.message.edit_text("✏️ Re-enter the homework:", reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "hw:history")
async def cb_hw_history(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    text = await get_teacher_homework_history(user_session["user_id"], user_session["org_id"])
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
