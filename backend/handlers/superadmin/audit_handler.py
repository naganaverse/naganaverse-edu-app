"""
handlers/superadmin/audit_handler.py
─────────────────────────────────────────────────────────────
Audit logs viewer — direct action.
Shows last 50 events across all orgs.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsSuperAdmin
from keyboards.common_kb import nav_only_keyboard
from database.repositories.user_repo_security import AuditLogRepository

router = Router()
router.callback_query.filter(IsSuperAdmin())

_audit = AuditLogRepository()


@router.callback_query(F.data == "sa:audit_logs")
async def cb_audit_logs(callback: CallbackQuery) -> None:
    await callback.answer()
    logs = await _audit.get_recent(org_id=None, limit=25)

    if not logs:
        await callback.message.edit_text(
            "📜 No audit logs found.", reply_markup=nav_only_keyboard()
        )
        return

    lines = ["📜 <b>Audit Logs</b> (last 25)\n"]
    for log in logs:
        ts       = str(log.get("timestamp", ""))[:16]
        event    = log.get("event_type", "—")
        user     = log.get("user_id", "—")
        org      = log.get("org_id", "—") or "platform"
        lines.append(f"<code>{ts}</code> | <b>{event}</b>\n  👤 {user} | 🏫 {org}\n")

    text = "\n".join(lines)
    # Telegram message length guard
    if len(text) > 3800:
        text = text[:3800] + "\n<i>...truncated. More in DB.</i>"

    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
