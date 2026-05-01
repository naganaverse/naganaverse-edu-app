"""
handlers/superadmin/emergency_handler.py
─────────────────────────────────────────────────────────────
Platform Controls + Emergency actions:
  - Pause / Resume registrations
  - Enable / Disable maintenance mode
  - Security center (login attempts, blocked users)
  - Unblock users

When maintenance mode is ON:
  - Any non-superadmin user gets: "Under maintenance" message
  - Enforced in AuthMiddleware via system_settings check
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.filters import IsSuperAdmin
from core.loader import bot
from services.superadmin_service import (
    pause_registrations,
    resume_registrations,
    enable_maintenance_mode,
    disable_maintenance_mode,
    freeze_user,
    unfreeze_user,
)
from keyboards.superadmin_kb import (
    platform_controls_keyboard,
    security_center_keyboard,
)
from keyboards.common_kb import nav_only_keyboard, nav_row
from database.repositories.user_repo_security import (
    LoginAttemptRepository,
    AuditLogRepository,
    SystemSettingsRepository,
)
from database.connection import get_pool

router = Router()
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())

_login_log    = LoginAttemptRepository()
_audit        = AuditLogRepository()
_settings     = SystemSettingsRepository()


class EmergencyFSM(StatesGroup):
    unblock_user = State()


# ── Platform Controls ─────────────────────────────────────

@router.callback_query(F.data == "sa:platform_controls")
async def cb_platform_controls(callback: CallbackQuery) -> None:
    await callback.answer()

    maint_on  = await _settings.get_maintenance_mode()
    reg_paused = await _settings.get_registrations_paused()

    status_text = (
        f"Current Status:\n"
        f"🔧 Maintenance Mode: {'🔴 ON' if maint_on else '🟢 OFF'}\n"
        f"📝 Registrations: {'⏸ Paused' if reg_paused else '▶️ Active'}"
    )

    await callback.message.edit_text(
        f"⚙️ <b>Platform Controls</b>\n\n{status_text}",
        reply_markup=platform_controls_keyboard(),
    )


@router.callback_query(F.data == "sa:pause_reg")
async def cb_pause_reg(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await pause_registrations(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "sa:resume_reg")
async def cb_resume_reg(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await resume_registrations(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "sa:maint_on")
async def cb_maintenance_on(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await enable_maintenance_mode(callback.from_user.id)

    # Broadcast maintenance notice to all active users
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT telegram_id FROM users WHERE telegram_id IS NOT NULL AND status = 'active'"
        )

    notice = (
        "🔧 <b>Naganaverse Maintenance</b>\n\n"
        "The platform is currently under scheduled maintenance.\n"
        "Please try again in a while. We apologize for the inconvenience."
    )
    sent = 0
    for r in rows[:500]:  # Limit broadcast to avoid rate limits
        try:
            await bot.send_message(r["telegram_id"], notice)
            sent += 1
        except Exception:
            pass

    await callback.message.edit_text(
        text + f"\n\n📢 Maintenance notice sent to {sent} users.",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(F.data == "sa:maint_off")
async def cb_maintenance_off(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await disable_maintenance_mode(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())


# ── Security Center ───────────────────────────────────────

@router.callback_query(F.data == "sa:security")
async def cb_security_center(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🔐 <b>Security Center</b>",
        reply_markup=security_center_keyboard(),
    )


@router.callback_query(F.data == "sa:login_attempts")
async def cb_login_attempts(callback: CallbackQuery) -> None:
    await callback.answer()
    attempts = await _login_log.get_recent(limit=20)

    if not attempts:
        await callback.message.edit_text("🔐 No login attempts recorded.", reply_markup=nav_only_keyboard())
        return

    lines = ["🔐 <b>Recent Login Attempts</b>\n"]
    for a in attempts:
        ts     = str(a.get("attempt_time", ""))[:16]
        status = "✅" if a.get("status") == "success" else "❌"
        user   = a.get("user_id", "—")
        ip     = a.get("ip_address", "—")
        lines.append(f"{status} <code>{ts}</code> | <b>{user}</b> | {ip}")

    await callback.message.edit_text("\n".join(lines), reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "sa:blocked_users")
async def cb_blocked_users(callback: CallbackQuery) -> None:
    await callback.answer()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, role, org_id, reason, suspended_until
            FROM suspended_accounts
            ORDER BY created_at DESC LIMIT 20
            """
        )

    if not rows:
        await callback.message.edit_text(
            "✅ No blocked users.", reply_markup=nav_only_keyboard()
        )
        return

    lines = ["🚫 <b>Blocked Users</b>\n"]
    for r in rows:
        until = str(r["suspended_until"])[:16] if r["suspended_until"] else "Indefinite"
        lines.append(
            f"👤 <b>{r['user_id']}</b> ({r['role']})\n"
            f"   🏫 {r['org_id'] or 'platform'}\n"
            f"   📋 {r['reason'] or '—'}\n"
            f"   ⏰ Until: {until}\n"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Unblock a User", callback_data="sa:unblock_user_start")],
        nav_row(),
    ])
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data == "sa:unblock_user_start")
async def cb_unblock_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(EmergencyFSM.unblock_user)
    await callback.message.edit_text(
        "✅ <b>Unblock User</b>\n\nEnter the <b>User ID</b> to unblock:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(EmergencyFSM.unblock_user)
async def msg_unblock_user(message: Message, state: FSMContext) -> None:
    user_id = message.text.strip().upper()
    await state.clear()
    result = await unfreeze_user(user_id, message.from_user.id)

    # Remove from suspended_accounts
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM suspended_accounts WHERE user_id = $1", user_id
        )

    # Notify the user they are unblocked
    from database.connection import get_pool as gp
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT telegram_id FROM users WHERE user_id = $1", user_id
        )
    if row and row["telegram_id"]:
        try:
            await bot.send_message(
                row["telegram_id"],
                "✅ Your Naganaverse account has been reactivated.\nUse /start to login.",
            )
        except Exception:
            pass

    await message.answer(result["message"], reply_markup=nav_only_keyboard())


@router.callback_query(F.data == "sa:spam_activity")
async def cb_spam_activity(callback: CallbackQuery) -> None:
    await callback.answer()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, COUNT(*) as cnt
            FROM bot_activity
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY user_id
            HAVING COUNT(*) > 30
            ORDER BY cnt DESC LIMIT 15
            """
        )

    if not rows:
        await callback.message.edit_text(
            "✅ No spam activity detected in the last hour.",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = ["⚠️ <b>Spam Activity (Last 1 hour)</b>\n"]
    for r in rows:
        lines.append(f"👤 <b>{r['user_id']}</b> — {r['cnt']} commands")

    kb = InlineKeyboardMarkup(inline_keyboard=[nav_row()])
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
