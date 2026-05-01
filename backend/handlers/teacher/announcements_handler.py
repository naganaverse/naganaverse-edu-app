"""
handlers/teacher/announcements_handler.py
─────────────────────────────────────────────────────────────
FSM: ANNOUNCE_SELECT_TARGET → ANNOUNCE_ENTER_MESSAGE
On completion: saves to DB + broadcasts to target students
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsTeacher
from core.loader import bot
from services.teacher_service import get_assigned_classes
from keyboards.teacher_kb import announcement_target_keyboard, class_select_keyboard
from keyboards.common_kb import nav_only_keyboard
from database.models.announcement_model import Announcement
from database.repositories.announcement_repo import AnnouncementRepository

router = Router()
router.message.filter(IsTeacher())
router.callback_query.filter(IsTeacher())

_ann_repo = AnnouncementRepository()


class AnnounceFSM(StatesGroup):
    select_target  = State()
    select_class   = State()
    enter_message  = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "teacher:announcement")
async def cb_announce_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(AnnounceFSM.select_target)
    await callback.message.edit_text(
        "📢 <b>Send Announcement</b>\n\nWho should receive this?",
        reply_markup=announcement_target_keyboard("teacher"),
    )


@router.callback_query(AnnounceFSM.select_target, F.data.startswith("ann:"))
async def cb_announce_target(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    target = callback.data.split(":", 1)[1]

    if target == "class":
        classes = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
        await state.update_data(target="class")
        await state.set_state(AnnounceFSM.select_class)
        await callback.message.edit_text(
            "📢 <b>Announcement</b>\n\nSelect target class:",
            reply_markup=class_select_keyboard(classes, "ann_class"),
        )
        return

    await state.update_data(target="all", target_class=None)
    await state.set_state(AnnounceFSM.enter_message)
    await callback.message.edit_text(
        "📢 <b>Announcement — All Students</b>\n\nEnter your message:",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(AnnounceFSM.select_class, F.data.startswith("ann_class:"))
async def cb_announce_class(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    await state.update_data(target_class=class_name)
    await state.set_state(AnnounceFSM.enter_message)
    await callback.message.edit_text(
        f"📢 <b>Announcement — {class_name}</b>\n\nEnter your message:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AnnounceFSM.enter_message)
async def msg_announce_text(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("❌ Message too short.", reply_markup=nav_only_keyboard())
        return

    data        = await state.get_data()
    org_id      = user_session["org_id"]
    teacher_id  = user_session["user_id"]
    target_class = data.get("target_class")

    ann = Announcement(
        org_id=org_id,
        message=text,
        created_by=teacher_id,
        target_class=target_class,
    )
    await _ann_repo.create(ann)

    # Broadcast to students
    telegram_ids = await _ann_repo.get_target_telegram_ids(org_id, target_class)
    sent = 0
    broadcast_msg = (
        f"📢 <b>Announcement</b>\n\n"
        f"{text}"
    )
    for tg_id in telegram_ids:
        try:
            await bot.send_message(tg_id, broadcast_msg)
            sent += 1
        except Exception:
            pass

    await state.clear()
    target_label = target_class or "All Students"
    await message.answer(
        f"✅ <b>Announcement Sent</b>\n\n"
        f"📢 Target: {target_label}\n"
        f"👥 Delivered to: {sent} students",
        reply_markup=nav_only_keyboard(),
    )
