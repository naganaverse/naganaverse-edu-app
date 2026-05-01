"""
handlers/student/announcements_handler.py
─────────────────────────────────────────────────────────────
Direct action — no FSM needed.
Fetches latest 10 announcements for student's org + class.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsStudent
from keyboards.common_kb import nav_only_keyboard
from database.repositories.announcement_repo import AnnouncementRepository

router = Router()
router.callback_query.filter(IsStudent())

_ann_repo = AnnouncementRepository()


@router.callback_query(F.data == "student:announcements")
async def cb_announcements(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    await callback.answer()
    org_id     = user_session["org_id"]
    class_name = user_session.get("class_name", "")

    announcements = await _ann_repo.get_recent(org_id, class_name, limit=10)

    if not announcements:
        await callback.message.edit_text(
            "📢 No announcements yet.\nCheck back later!",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = ["📢 <b>Announcements</b>\n"]
    for ann in announcements:
        date_str = ann.created_at.strftime("%d %b %Y") if ann.created_at else ""
        target   = f"📚 {ann.target_class}" if ann.target_class else "📣 All"
        lines.append(
            f"📅 {date_str} | {target}\n"
            f"{ann.message}\n"
            f"{'─' * 30}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=nav_only_keyboard(),
    )
