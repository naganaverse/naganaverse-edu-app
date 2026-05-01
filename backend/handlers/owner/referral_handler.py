"""
handlers/owner/referral_handler.py
Direct action — show referral code + stats.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsOwner
from services.referral_service import get_referral_info
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.callback_query.filter(IsOwner())


@router.callback_query(F.data == "owner:referrals")
async def cb_referrals(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    text = await get_referral_info(user_session["org_id"])
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
