"""
keyboards/parent_kb.py
─────────────────────────────────────────────────────────────
All keyboards used in parent-facing screens.
─────────────────────────────────────────────────────────────
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.common_kb import nav_row


def parent_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main parent dashboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Attendance",      callback_data="parent:attendance"),
            InlineKeyboardButton(text="📝 Test Scores",     callback_data="parent:tests"),
        ],
        [
            InlineKeyboardButton(text="📢 Announcements",   callback_data="parent:announcements"),
        ],
        nav_row(),
    ])
