"""
keyboards/superadmin_kb.py
─────────────────────────────────────────────────────────────
All keyboards used in super admin screens.
─────────────────────────────────────────────────────────────
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.common_kb import nav_row


def superadmin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Super Admin main menu — 7 sections."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏫 Institution Management", callback_data="sa:institutions"),
            InlineKeyboardButton(text="👤 User Management",        callback_data="sa:users"),
        ],
        [
            InlineKeyboardButton(text="📊 Platform Analytics",     callback_data="sa:analytics"),
            InlineKeyboardButton(text="🔐 Security Center",        callback_data="sa:security"),
        ],
        [
            InlineKeyboardButton(text="📜 Audit Logs",             callback_data="sa:audit_logs"),
            InlineKeyboardButton(text="⚙️ Platform Controls",      callback_data="sa:platform_controls"),
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast System",       callback_data="sa:broadcast"),
        ],
        nav_row(),
    ])


def institution_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏫 Approve Institutions",  callback_data="sa:approve_list")],
        [InlineKeyboardButton(text="🔍 Search Institution",    callback_data="sa:search_inst")],
        [InlineKeyboardButton(text="❄️ Freeze Institution",    callback_data="sa:freeze_inst")],
        [InlineKeyboardButton(text="🗑 Delete Institution",    callback_data="sa:delete_inst")],
        nav_row(),
    ])


def pending_institution_keyboard(org_id: str, org_name: str) -> InlineKeyboardMarkup:
    """Approval card for a single pending institution."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve",   callback_data=f"sa:approve:{org_id}"),
            InlineKeyboardButton(text="❌ Reject",    callback_data=f"sa:reject:{org_id}"),
        ],
        [
            InlineKeyboardButton(text="⏭ Next",      callback_data="sa:next_pending"),
        ],
        nav_row(),
    ])


def reject_reason_keyboard(org_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Spam Registration",  callback_data=f"sa:reject_reason:{org_id}:spam")],
        [InlineKeyboardButton(text="❓ Invalid Institution", callback_data=f"sa:reject_reason:{org_id}:invalid")],
        [InlineKeyboardButton(text="📋 Duplicate Request",  callback_data=f"sa:reject_reason:{org_id}:duplicate")],
        nav_row(),
    ])


def institution_approved_keyboard(org_id: str) -> InlineKeyboardMarkup:
    """Replaces approval card after admin approves — button toggles to approved state."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Institution Approved", callback_data=f"sa:approved_done:{org_id}")],
        nav_row(),
    ])


def user_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Search User",         callback_data="sa:search_user")],
        [InlineKeyboardButton(text="🔑 Reset Password",      callback_data="sa:reset_password")],
        [InlineKeyboardButton(text="🔗 Unbind Telegram ID",  callback_data="sa:unbind_telegram")],
        [InlineKeyboardButton(text="🚫 Freeze Account",      callback_data="sa:freeze_account")],
        [InlineKeyboardButton(text="✅ Unfreeze Account",    callback_data="sa:unfreeze_account")],
        nav_row(),
    ])


def platform_controls_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏸ Pause Registrations",   callback_data="sa:pause_reg")],
        [InlineKeyboardButton(text="▶️ Resume Registrations",  callback_data="sa:resume_reg")],
        [InlineKeyboardButton(text="🔧 Enable Maintenance",    callback_data="sa:maint_on")],
        [InlineKeyboardButton(text="✅ Disable Maintenance",   callback_data="sa:maint_off")],
        nav_row(),
    ])


def broadcast_target_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 All Owners",     callback_data="sa:broadcast:owners")],
        [InlineKeyboardButton(text="👨‍🏫 All Teachers",  callback_data="sa:broadcast:teachers")],
        [InlineKeyboardButton(text="🎓 All Students",   callback_data="sa:broadcast:students")],
        [InlineKeyboardButton(text="📢 Everyone",       callback_data="sa:broadcast:all")],
        nav_row(),
    ])


def security_center_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Login Attempts",   callback_data="sa:login_attempts")],
        [InlineKeyboardButton(text="🚫 Blocked Users",    callback_data="sa:blocked_users")],
        [InlineKeyboardButton(text="⚠️ Spam Activity",    callback_data="sa:spam_activity")],
        nav_row(),
    ])


def delete_confirm_keyboard(org_id: str) -> InlineKeyboardMarkup:
    """
    Double-confirmation for institution deletion.
    Requires admin to type DELETE separately (handled in handler).
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗑 Yes, Delete Permanently",
            callback_data=f"sa:confirm_delete:{org_id}"
        )],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="sa:institutions")],
    ])
