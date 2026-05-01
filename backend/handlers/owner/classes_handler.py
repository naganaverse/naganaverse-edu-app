"""
handlers/owner/classes_handler.py
Owner: View class and content library overview.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsOwner
from keyboards.common_kb import nav_only_keyboard
from database.connection import get_pool

router = Router()
router.callback_query.filter(IsOwner())


@router.callback_query(F.data == "owner:content_library")
async def cb_content_library(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    org_id = user_session["org_id"]
    pool   = await get_pool()

    async with pool.acquire() as conn:
        resource_count = await conn.fetchval(
            "SELECT COUNT(*) FROM resources WHERE org_id = $1", org_id
        )
        homework_count = await conn.fetchval(
            "SELECT COUNT(*) FROM homework WHERE org_id = $1", org_id
        )
        test_count = await conn.fetchval(
            "SELECT COUNT(*) FROM tests WHERE org_id = $1", org_id
        )
        rows = await conn.fetch(
            """
            SELECT resource_type, COUNT(*) as cnt
            FROM resources WHERE org_id = $1
            GROUP BY resource_type ORDER BY cnt DESC
            """,
            org_id,
        )

    breakdown = "\n".join(
        f"  • {r['resource_type'].replace('_', ' ').title()}: {r['cnt']}"
        for r in rows
    ) or "  No files yet."

    await callback.message.edit_text(
        f"🗂 <b>Content Library</b>\n\n"
        f"📄 Total Resources: {resource_count}\n"
        f"📌 Total Homework: {homework_count}\n"
        f"📝 Total Tests: {test_count}\n\n"
        f"<b>Resources by Type:</b>\n{breakdown}",
        reply_markup=nav_only_keyboard(),
    )
