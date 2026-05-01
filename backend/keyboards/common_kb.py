"""
keyboards/common_kb.py
─────────────────────────────────────────────────────────────
Landing screen keyboard (unauthenticated users).
Navigation row used across ALL role screens.
─────────────────────────────────────────────────────────────
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# ── Landing Screen ────────────────────────────────────────

def landing_keyboard() -> InlineKeyboardMarkup:
    """
    Shown to any user not logged in.
    /start → user not found → this keyboard.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Login as Student",  callback_data="login:student"),
            InlineKeyboardButton(text="👨‍🏫 Login as Teacher",  callback_data="login:teacher"),
        ],
        [
            InlineKeyboardButton(text="🏢 Login as Owner",    callback_data="login:owner"),
            InlineKeyboardButton(text="👨‍👩‍👧 Login as Parent",  callback_data="login:parent"),
        ],
        [
            InlineKeyboardButton(text="🏫 Register Institution", callback_data="register_institution"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ About Bot",          callback_data="about_bot"),
            InlineKeyboardButton(text="❓ Help",               callback_data="help"),
        ],
    ])


# ── Navigation Row ────────────────────────────────────────
# Appended to every deep-level screen

def nav_row() -> list:
    """Returns a single row of navigation buttons to append to any keyboard."""
    return [
        InlineKeyboardButton(text="⬅️ Back", callback_data="nav:back"),
        InlineKeyboardButton(text="🏠 Home", callback_data="nav:home"),
        InlineKeyboardButton(text="❓ Help", callback_data="nav:help"),
    ]


def add_nav(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Append navigation row to any existing inline keyboard."""
    keyboard.inline_keyboard.append(nav_row())
    return keyboard


def nav_only_keyboard() -> InlineKeyboardMarkup:
    """Standalone navigation keyboard — used on terminal screens."""
    return InlineKeyboardMarkup(inline_keyboard=[nav_row()])


# ── Confirm / Cancel ──────────────────────────────────────

def confirm_keyboard(confirm_data: str, cancel_data: str = "nav:home") -> InlineKeyboardMarkup:
    """Generic Yes / No confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, Confirm", callback_data=confirm_data),
            InlineKeyboardButton(text="❌ Cancel",        callback_data=cancel_data),
        ],
        nav_row(),
    ])


def back_keyboard(back_data: str = "nav:back") -> InlineKeyboardMarkup:
    """Single back button for simple screens."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data=back_data)],
    ])
