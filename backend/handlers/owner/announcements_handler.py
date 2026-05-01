"""
handlers/owner/announcements_handler.py
─────────────────────────────────────────────────────────────
FSM: OWNER_ANNOUNCE_TARGET → OWNER_ANNOUNCE_MESSAGE
Targets: All Students | Specific Class | Teachers
─────────────────────────────────────────────────────────────
"""

import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.filters import IsOwner
from core.loader import bot
from keyboards.teacher_kb import announcement_target_keyboard, class_select_keyboard
from keyboards.common_kb import nav_only_keyboard, nav_row
from database.models.announcement_model import Announcement
from database.repositories.announcement_repo import AnnouncementRepository
from database.repositories.teacher_repo import TeacherRepository

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_ann_repo = AnnouncementRepository()
_teacher_repo = TeacherRepository()


class OwnerAnnounceFSM(StatesGroup):
    select_target = State()
    select_class  = State()
    enter_message = State()


@router.callback_query(F.data == "owner:announcements")
async def cb_owner_announce_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(OwnerAnnounceFSM.select_target)
    await callback.message.edit_text(
        "📢 <b>Send Announcement</b>\n\nWho should receive this?",
        reply_markup=announcement_target_keyboard("owner"),
    )


@router.callback_query(OwnerAnnounceFSM.select_target, F.data.startswith("ann:"))
async def cb_owner_target(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    target = callback.data.split(":", 1)[1]

    if target == "class":
        from database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT class FROM students WHERE org_id = $1 ORDER BY class",
                user_session["org_id"],
            )
        classes = [r["class"] for r in rows]
        await state.update_data(target="class")
        await state.set_state(OwnerAnnounceFSM.select_class)
        await callback.message.edit_text(
            "📢 Select class:",
            reply_markup=class_select_keyboard(classes, "oann_class"),
        )
        return

    await state.update_data(target=target, target_class=None)
    await state.set_state(OwnerAnnounceFSM.enter_message)
    label = "All Students" if target == "all_students" else "Teachers"
    await callback.message.edit_text(
        f"📢 <b>Announcement → {label}</b>\n\nEnter your message:",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(OwnerAnnounceFSM.select_class, F.data.startswith("oann_class:"))
async def cb_owner_ann_class(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    await state.update_data(target_class=class_name)
    await state.set_state(OwnerAnnounceFSM.enter_message)
    await callback.message.edit_text(
        f"📢 <b>Announcement → {class_name}</b>\n\nEnter your message:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(OwnerAnnounceFSM.enter_message)
async def msg_owner_announce(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("❌ Message too short.", reply_markup=nav_only_keyboard())
        return

    data         = await state.get_data()
    org_id       = user_session["org_id"]
    owner_id     = user_session["user_id"]
    target       = data.get("target", "all_students")
    target_class = data.get("target_class")

    # Let the owner know the broadcast has started, as it might take a few seconds
    status_msg = await message.answer("⏳ <i>Broadcasting announcement...</i>")

    ann = Announcement(org_id=org_id, message=text, created_by=owner_id, target_class=target_class)
    await _ann_repo.create(ann)

    # Broadcast
    sent = 0
    broadcast_msg = f"📢 <b>Announcement</b>\n\n{text}"

    if target == "teachers":
        teachers = await _teacher_repo.get_all_by_org(org_id)
        tg_ids = [t.telegram_id for t in teachers if t.telegram_id]
    else:
        tg_ids = await _ann_repo.get_target_telegram_ids(org_id, target_class)

    # 🛡️ FIX FOR STRESS FAILURE: Rate limited broadcast loop
    for index, tg_id in enumerate(tg_ids):
        try:
            await bot.send_message(tg_id, broadcast_msg)
            sent += 1
        except Exception:
            # User might have blocked the bot or deleted their account
            pass
            
        # Sleep for 50ms between each message (20 msgs / sec)
        await asyncio.sleep(0.05)
        
        # Take a 1-second breather every 20 messages to strictly avoid hitting limits
        if (index + 1) % 20 == 0:
            await asyncio.sleep(1.0)

    await state.clear()
    label = target_class or ("Teachers" if target == "teachers" else "All Students")
    
    # Update the status message with the final count
    await status_msg.edit_text(
        f"✅ <b>Announcement Sent</b>\n\n"
        f"📢 Target: {label}\n"
        f"👥 Delivered to: {sent}",
        reply_markup=nav_only_keyboard(),
        )
        
