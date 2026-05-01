"""
keyboards/student_kb.py
─────────────────────────────────────────────────────────────
All keyboards used in student-facing screens.
─────────────────────────────────────────────────────────────
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.common_kb import nav_row, add_nav


def student_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main student dashboard — 7 menu buttons + nav row."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Resources",       callback_data="student:resources"),
            InlineKeyboardButton(text="📌 Today Homework",  callback_data="student:homework_today"),
        ],
        [
            InlineKeyboardButton(text="📝 Tests",           callback_data="student:tests"),
            InlineKeyboardButton(text="📊 My Attendance",   callback_data="student:attendance"),
        ],
        [
            InlineKeyboardButton(text="📢 Announcements",   callback_data="student:announcements"),
            InlineKeyboardButton(text="🗂 Resource Library", callback_data="student:resource_library"),
        ],
        [
            InlineKeyboardButton(text="👤 My Profile",      callback_data="student:profile"),
        ],
        nav_row(),
    ])


def subject_select_keyboard(subjects: list, prefix: str) -> InlineKeyboardMarkup:
    """Dynamic subject selection buttons."""
    rows = []
    for i in range(0, len(subjects), 2):
        row = []
        for subj in subjects[i:i+2]:
            row.append(InlineKeyboardButton(
                text=subj,
                callback_data=f"{prefix}:{subj}"
            ))
        rows.append(row)
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def resource_type_keyboard() -> InlineKeyboardMarkup:
    """Resource type selection for students."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Notes",               callback_data="restype:notes"),
            InlineKeyboardButton(text="📝 Worksheets",           callback_data="restype:worksheet"),
        ],
        [
            InlineKeyboardButton(text="📋 Important Questions",  callback_data="restype:important_questions"),
            InlineKeyboardButton(text="📖 PYQ",                  callback_data="restype:pyq"),
        ],
        [
            InlineKeyboardButton(text="🔖 Practice Sheet",       callback_data="restype:practice_sheet"),
        ],
        nav_row(),
    ])


def homework_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📌 Today's Homework",  callback_data="student:homework_today"),
            InlineKeyboardButton(text="📚 Previous Homework", callback_data="student:homework_history"),
        ],
        nav_row(),
    ])


def tests_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Available Tests",   callback_data="student:tests_available"),
            InlineKeyboardButton(text="📊 Previous Results",  callback_data="student:tests_results"),
        ],
        nav_row(),
    ])


def available_tests_keyboard(tests: list) -> InlineKeyboardMarkup:
    """Dynamic list of available tests."""
    rows = []
    for test in tests:
        rows.append([
            InlineKeyboardButton(
                text=f"📝 {test['test_name']} — {test['subject_name']}",
                callback_data=f"student:start_test:{test['test_id']}"
            )
        ])
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_test_keyboard(test_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Start Test", callback_data=f"student:begin_test:{test_id}")],
        nav_row(),
    ])


def answer_keyboard(question_id: str) -> InlineKeyboardMarkup:
    """MCQ answer buttons for a single test question."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A", callback_data=f"ans:{question_id}:A"),
            InlineKeyboardButton(text="B", callback_data=f"ans:{question_id}:B"),
            InlineKeyboardButton(text="C", callback_data=f"ans:{question_id}:C"),
            InlineKeyboardButton(text="D", callback_data=f"ans:{question_id}:D"),
        ],
    ])
