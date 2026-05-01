"""
handlers/superadmin/admin_users_handler.py
─────────────────────────────────────────────────────────────
User Management FSM:
  SEARCH_USER → show profile + action buttons
  Actions: Reset Password | Unbind Telegram | Freeze | Unfreeze

Broadcast FSM:
  SELECT_TARGET → ENTER_MESSAGE → send to all in target group
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.filters import IsSuperAdmin
from core.loader import bot
from core.security import hash_password
from services.superadmin_service import (
    freeze_user,
    unfreeze_user,
    unbind_telegram,
    broadcast_to_all_owners,
)
from keyboards.superadmin_kb import (
    user_management_keyboard,
    broadcast_target_keyboard,
)
from keyboards.common_kb import nav_only_keyboard, nav_row
from database.repositories.user_repo import UserRepository
from database.connection import get_pool

router = Router()
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())

_user_repo = UserRepository()


class UserMgmtFSM(StatesGroup):
    search         = State()
    reset_password = State()
    unbind_id      = State()
    freeze_id      = State()


class BroadcastFSM(StatesGroup):
    enter_message = State()



async def _find_user_across_tables(user_id: str) -> object | None:
    """
    Search for a user across users, students, and teachers tables.
    Returns a unified object with .user_id, .name, .role, .org_id,
    .telegram_id, .status, .failed_attempts attributes.
    """
    from database.repositories.student_repo import StudentRepository
    from database.repositories.teacher_repo import TeacherRepository

    uid = user_id.upper()

    # Check users table (owners + any role)
    user = await _user_repo.get_by_user_id(uid)
    if user:
        return user

    # Check students table
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT student_id AS user_id, name, 'student' AS role, org_id, "
            "telegram_id, account_status AS status, 0 AS failed_attempts "
            "FROM students WHERE student_id = $1", uid
        )
        if row:
            return type('User', (), dict(row))()

        # Check teachers table
        row = await conn.fetchrow(
            "SELECT teacher_id AS user_id, name, 'teacher' AS role, org_id, "
            "telegram_id, account_status AS status, 0 AS failed_attempts "
            "FROM teachers WHERE teacher_id = $1", uid
        )
        if row:
            return type('User', (), dict(row))()

    return None


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "sa:users")
async def cb_user_mgmt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "👤 <b>User Management</b>",
        reply_markup=user_management_keyboard(),
    )


# ── Menu Entry Handlers (ask for User ID first) ──────────────

@router.callback_query(F.data == "sa:reset_password")
async def cb_reset_pw_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(user_action="reset_pw")
    await state.set_state(UserMgmtFSM.search)
    await callback.message.edit_text(
        "🔑 <b>Reset Password</b>\n\nEnter the <b>User ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(F.data == "sa:unbind_telegram")
async def cb_unbind_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(user_action="unbind")
    await state.set_state(UserMgmtFSM.search)
    await callback.message.edit_text(
        "🔗 <b>Unbind Telegram ID</b>\n\nEnter the <b>User ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(F.data == "sa:freeze_account")
async def cb_freeze_acc_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(user_action="freeze")
    await state.set_state(UserMgmtFSM.search)
    await callback.message.edit_text(
        "🚫 <b>Freeze Account</b>\n\nEnter the <b>User ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.callback_query(F.data == "sa:unfreeze_account")
async def cb_unfreeze_acc_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(user_action="unfreeze")
    await state.set_state(UserMgmtFSM.search)
    await callback.message.edit_text(
        "✅ <b>Unfreeze Account</b>\n\nEnter the <b>User ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


# ── Search User ───────────────────────────────────────────

@router.callback_query(F.data == "sa:search_user")
async def cb_search_user_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(UserMgmtFSM.search)
    await callback.message.edit_text(
        "🔍 <b>Search User</b>\n\nEnter User ID:\n"
        "<i>Example: STD102, TCH203, OWN001</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(UserMgmtFSM.search)
async def msg_search_user(message: Message, state: FSMContext) -> None:
    user_id = message.text.strip().upper()
    data = await state.get_data()
    user_action = data.get("user_action", "manage")
    await state.clear()

    # Search across all 3 tables (users, students, teachers)
    user = await _find_user_across_tables(user_id)
    if not user:
        await message.answer(
            f"❌ User <code>{user_id}</code> not found.",
            reply_markup=nav_only_keyboard(),
        )
        return

    # If coming from a specific menu action, execute it directly
    if user_action == "reset_pw":
        await state.update_data(target_user_id=user_id)
        await state.set_state(UserMgmtFSM.reset_password)
        await message.answer(
            f"🔑 <b>Reset Password for {user.name}</b>\n\nEnter new password:",
            reply_markup=nav_only_keyboard(),
        )
        return
    elif user_action == "unbind":
        result = await unbind_telegram(user_id, message.from_user.id)
        await message.answer(result["message"], reply_markup=nav_only_keyboard())
        return
    elif user_action == "freeze":
        result = await freeze_user(user_id, message.from_user.id)
        if user.telegram_id:
            try:
                await bot.send_message(user.telegram_id,
                    "🚫 Your account has been temporarily restricted.\nContact Naganaverse support.")
            except Exception:
                pass
        await message.answer(result["message"], reply_markup=nav_only_keyboard())
        return
    elif user_action == "unfreeze":
        result = await unfreeze_user(user_id, message.from_user.id)
        if user.telegram_id:
            try:
                await bot.send_message(user.telegram_id,
                    "✅ Your account has been reactivated. Use /start to login.")
            except Exception:
                pass
        await message.answer(result["message"], reply_markup=nav_only_keyboard())
        return

    # Default: show full profile with all action buttons
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Reset Password",    callback_data=f"sa:reset_pw:{user_id}")],
        [InlineKeyboardButton(text="🔗 Unbind Telegram",   callback_data=f"sa:unbind:{user_id}")],
        [InlineKeyboardButton(text="🚫 Freeze Account",    callback_data=f"sa:freeze_usr:{user_id}")],
        [InlineKeyboardButton(text="✅ Unfreeze Account",  callback_data=f"sa:unfreeze_usr:{user_id}")],
        nav_row(),
    ])

    tg_status = f"✅ {user.telegram_id}" if user.telegram_id else "❌ Not bound"
    await message.answer(
        f"👤 <b>User Profile</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"📛 Name: {user.name}\n"
        f"🎭 Role: {user.role}\n"
        f"🏫 Org: {user.org_id or '—'}\n"
        f"📱 Telegram: {tg_status}\n"
        f"🔒 Status: {user.status}\n"
        f"🔑 Failed logins: {user.failed_attempts}",
        reply_markup=kb,
    )


# ── Reset Password ────────────────────────────────────────

@router.callback_query(F.data.startswith("sa:reset_pw:"))
async def cb_reset_pw_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    user_id = callback.data.split(":", 2)[2]
    await state.update_data(target_user_id=user_id)
    await state.set_state(UserMgmtFSM.reset_password)
    await callback.message.edit_text(
        f"🔑 <b>Reset Password</b>\n\n"
        f"User: <code>{user_id}</code>\n\n"
        "Enter the new password:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(UserMgmtFSM.reset_password)
async def msg_new_password(message: Message, state: FSMContext) -> None:
    new_password = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass

    if len(new_password) < 4:
        await message.answer("❌ Password too short.", reply_markup=nav_only_keyboard())
        return

    data    = await state.get_data()
    user_id = data["target_user_id"]
    await state.clear()

    updated = await _user_repo.update_password(user_id, hash_password(new_password))

    # Notify user their password was reset
    user = await _user_repo.get_by_user_id(user_id)
    if user and user.telegram_id:
        try:
            await bot.send_message(
                user.telegram_id,
                "🔑 <b>Password Reset</b>\n\n"
                "Your Naganaverse password has been reset by an administrator.\n"
                "Please login again with your new credentials.",
            )
        except Exception:
            pass

    await message.answer(
        "✅ Password reset successfully." if updated else "❌ Reset failed.",
        reply_markup=nav_only_keyboard(),
    )


# ── Unbind Telegram ───────────────────────────────────────

@router.callback_query(F.data.startswith("sa:unbind:"))
async def cb_unbind_telegram(callback: CallbackQuery) -> None:
    await callback.answer("Unbinding...")
    user_id = callback.data.split(":", 2)[2]
    result  = await unbind_telegram(user_id, callback.from_user.id)
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


# ── Freeze / Unfreeze User ────────────────────────────────

@router.callback_query(F.data.startswith("sa:freeze_usr:"))
async def cb_freeze_user(callback: CallbackQuery) -> None:
    await callback.answer("Freezing...")
    user_id = callback.data.split(":", 2)[2]
    result  = await freeze_user(user_id, callback.from_user.id)

    # Notify user
    user = await _user_repo.get_by_user_id(user_id)
    if user and user.telegram_id:
        try:
            await bot.send_message(
                user.telegram_id,
                "🚫 <b>Account Restricted</b>\n\n"
                "Your account has been temporarily restricted.\n"
                "Contact Naganaverse support for assistance.",
            )
        except Exception:
            pass

    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


@router.callback_query(F.data.startswith("sa:unfreeze_usr:"))
async def cb_unfreeze_user(callback: CallbackQuery) -> None:
    await callback.answer("Unfreezing...")
    user_id = callback.data.split(":", 2)[2]
    result  = await unfreeze_user(user_id, callback.from_user.id)

    user = await _user_repo.get_by_user_id(user_id)
    if user and user.telegram_id:
        try:
            await bot.send_message(
                user.telegram_id,
                "✅ <b>Account Reactivated</b>\n\n"
                "Your Naganaverse account has been reactivated.\n"
                "Use /start to login.",
            )
        except Exception:
            pass

    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


# ── Broadcast System ──────────────────────────────────────

@router.callback_query(F.data == "sa:broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📢 <b>Broadcast System</b>\n\nSelect target audience:",
        reply_markup=broadcast_target_keyboard(),
    )


@router.callback_query(F.data.startswith("sa:broadcast:"))
async def cb_broadcast_target(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    target = callback.data.split(":", 2)[2]
    await state.update_data(broadcast_target=target)
    await state.set_state(BroadcastFSM.enter_message)

    labels = {
        "owners":   "All Owners",
        "teachers": "All Teachers",
        "students": "All Students",
        "all":      "Everyone",
    }
    await callback.message.edit_text(
        f"📢 <b>Broadcast → {labels.get(target, target)}</b>\n\n"
        "Enter your message:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(BroadcastFSM.enter_message)
async def msg_broadcast_text(message: Message, state: FSMContext) -> None:
    text   = message.text.strip()
    data   = await state.get_data()
    target = data.get("broadcast_target", "owners")
    await state.clear()

    pool = await get_pool()
    broadcast_msg = f"📢 <b>Naganaverse Announcement</b>\n\n{text}"
    sent = 0

    async with pool.acquire() as conn:
        if target == "owners":
            rows = await conn.fetch(
                "SELECT telegram_id FROM users WHERE role = 'owner' AND telegram_id IS NOT NULL"
            )
        elif target == "teachers":
            rows = await conn.fetch(
                "SELECT telegram_id FROM teachers WHERE telegram_id IS NOT NULL"
            )
        elif target == "students":
            rows = await conn.fetch(
                "SELECT telegram_id FROM students WHERE telegram_id IS NOT NULL"
            )
        else:  # all
            rows = await conn.fetch(
                "SELECT telegram_id FROM users WHERE telegram_id IS NOT NULL"
            )

    for r in rows:
        try:
            await bot.send_message(r["telegram_id"], broadcast_msg)
            sent += 1
        except Exception:
            pass

    from database.repositories.user_repo_security import AuditLogRepository
    await AuditLogRepository().log(
        "BROADCAST_SENT",
        user_id=f"superadmin_{message.from_user.id}",
        role="super_admin",
        details={"target": target, "sent": sent, "message": text[:100]},
    )

    await message.answer(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"📢 Target: {target}\n"
        f"👥 Delivered to: <b>{sent}</b> users",
        reply_markup=nav_only_keyboard(),
    )
