"""
handlers/owner/analytics_handler.py
Direct action — fetches aggregated coaching stats.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsOwner
from services.owner_service import get_analytics
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.callback_query.filter(IsOwner())


@router.callback_query(F.data == "owner:analytics")
async def cb_analytics(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    text = await get_analytics(user_session["org_id"])
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
