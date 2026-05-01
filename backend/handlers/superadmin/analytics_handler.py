"""
handlers/superadmin/analytics_handler.py
─────────────────────────────────────────────────────────────
Platform-wide analytics — direct action, no FSM.
Aggregates across all orgs.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsSuperAdmin
from services.superadmin_service import get_platform_analytics
from keyboards.common_kb import nav_only_keyboard
from database.connection import get_pool

router = Router()
router.callback_query.filter(IsSuperAdmin())


@router.callback_query(F.data == "sa:analytics")
async def cb_platform_analytics(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await get_platform_analytics()

    # Add commands today count
    pool = await get_pool()
    async with pool.acquire() as conn:
        commands_today = await conn.fetchval(
            "SELECT COUNT(*) FROM bot_activity WHERE timestamp::date = CURRENT_DATE"
        )

    text += f"\n⚡ Commands Today: <b>{commands_today:,}</b>"
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
