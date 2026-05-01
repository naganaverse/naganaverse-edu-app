"""
keyboards/owner_kb.py
─────────────────────────────────────────────────────────────
All keyboards used in owner-facing screens.
─────────────────────────────────────────────────────────────
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.common_kb import nav_row


def owner_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main owner dashboard — Updated with Fee Management."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Students",           callback_data="owner:students"),
            InlineKeyboardButton(text="💰 Fee Management",     callback_data="owner:fees"), # 👈 Priority 1
        ],
        [
            InlineKeyboardButton(text="👨‍🏫 Teachers",          callback_data="owner:teachers"),
            InlineKeyboardButton(text="📊 Attendance Reports", callback_data="owner:attendance_reports"),
        ],
        [
            InlineKeyboardButton(text="📝 Test Reports",       callback_data="owner:test_reports"),
            InlineKeyboardButton(text="📢 Announcements",      callback_data="owner:announcements"),
        ],
        [
            InlineKeyboardButton(text="🗂 Content Library",    callback_data="owner:content_library"),
            InlineKeyboardButton(text="📈 Analytics",          callback_data="owner:analytics"),
        ],
        [
            InlineKeyboardButton(text="🎁 Referrals",          callback_data="owner:referrals"),
            InlineKeyboardButton(text="⚙️ Settings",           callback_data="owner:settings"),
        ],
        nav_row(),
    ])


def fees_menu_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu for Fee Management actions."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Log Payment",      callback_data="fee:log_pay")],
        [InlineKeyboardButton(text="🔄 Generate Dues",    callback_data="fee:bulk_due")],
        [InlineKeyboardButton(text="📋 Defaulters List",  callback_data="fee:defaulters")],
        [InlineKeyboardButton(text="🔔 Send Reminders",   callback_data="fee:reminders")],
        nav_row(),
    ])


def students_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Student",    callback_data="owner:student_add")],
        [InlineKeyboardButton(text="👁 View Students",  callback_data="owner:student_view")],
        [InlineKeyboardButton(text="✏️ Edit Student",   callback_data="owner:student_edit")],
        [InlineKeyboardButton(text="🗑 Remove Student", callback_data="owner:student_remove")],
        nav_row(),
    ])


def teachers_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Teacher",    callback_data="owner:teacher_add")],
        [InlineKeyboardButton(text="👁 View Teachers",  callback_data="owner:teacher_view")],
        [InlineKeyboardButton(text="✏️ Edit Teacher",   callback_data="owner:teacher_edit")],
        [InlineKeyboardButton(text="🗑 Remove Teacher", callback_data="owner:teacher_remove")],
        nav_row(),
    ])


def class_select_keyboard(classes: list, prefix: str) -> InlineKeyboardMarkup:
    rows = []
    # Display classes in 2 columns
    for i in range(0, len(classes), 2):
        row = []
        for cls in classes[i:i+2]:
            row.append(InlineKeyboardButton(
                text=f"📚 {cls}",
                callback_data=f"{prefix}:{cls}"
            ))
        rows.append(row)
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def attendance_report_actions_keyboard(class_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📲 Send to Parents (WhatsApp)",
            callback_data=f"owner:att_send_parents:{class_name}"
        )],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="nav:home")],
        nav_row(),
    ])


def test_report_actions_keyboard(test_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📲 Send Reports to Parents",
            callback_data=f"owner:test_send_parents:{test_id}"
        )],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="nav:home")],
        nav_row(),
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit Coaching Profile",      callback_data="owner:edit_profile")],
        [InlineKeyboardButton(text="📋 Subscription Status",        callback_data="owner:subscription")],
        [InlineKeyboardButton(text="🔔 Parent Notification Settings", callback_data="owner:notif_settings")],
        [InlineKeyboardButton(text="🔑 Change Password",            callback_data="owner:change_password")],
        nav_row(),
    ])


def select_tests_keyboard(tests: list) -> InlineKeyboardMarkup:
    rows = []
    for t in tests:
        rows.append([InlineKeyboardButton(
            text=f"📝 {t['topic']} — {t['test_id'][:8]}",
            callback_data=f"owner:test_report:{t['test_id']}"
        )])
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
    
