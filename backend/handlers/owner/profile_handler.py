"""
handlers/owner/profile_handler.py
Owner profile view — redirects to settings.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from core.filters import IsOwner
from keyboards.owner_kb import settings_keyboard

router = Router()
router.callback_query.filter(IsOwner())


@router.callback_query(F.data == "owner:profile")
async def cb_owner_profile(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    await callback.message.edit_text(
        f"🏢 <b>Owner Profile</b>\n\n"
        f"👤 Name: {user_session.get('name')}\n"
        f"🆔 ID: {user_session.get('user_id')}\n"
        f"🏫 Org: {user_session.get('org_id')}\n"
        f"📦 Plan: {user_session.get('plan_type', 'starter').title()}",
        reply_markup=settings_keyboard(),
    )
