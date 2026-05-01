"""
handlers/common/help.py
─────────────────────────────────────────────────────────────
Role-aware /help command.
Shows different help content based on user's role.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.common_kb import nav_only_keyboard

router = Router()

_HELP_TEXT = {
    "student": (
        "❓ <b>Student Help Guide</b>\n\n"
        "📚 <b>Resources</b>\n"
        "Tap Resources → Select Subject → Choose type (Notes/PYQ etc.) → Download PDF\n\n"
        "📌 <b>Homework</b>\n"
        "Tap Today Homework to see today's assignments\n"
        "Tap Previous Homework for past homework archive\n\n"
        "📝 <b>Tests</b>\n"
        "Tap Tests → Select test → Start → Answer questions → Get score\n\n"
        "📊 <b>Attendance</b>\n"
        "Tap My Attendance to see subject-wise attendance percentage\n\n"
        "📢 <b>Announcements</b>\n"
        "Latest coaching announcements appear here\n\n"
        "📞 <b>Need help?</b>\n"
        "Contact your coaching administrator."
    ),

    "teacher": (
        "❓ <b>Teacher Help Guide</b>\n\n"
        "📋 <b>Attendance</b>\n"
        "Tap Attendance → Select Class → Select Subject → Tap absent students → Submit\n\n"
        "📂 <b>Upload Notes</b>\n"
        "Tap Manage Notes → Upload → Select Class & Subject → Send PDF\n\n"
        "📌 <b>Homework</b>\n"
        "Tap Send Homework → Select Class → Select Subject → Type homework → Confirm\n\n"
        "📝 <b>Create Test</b>\n"
        "Tap Create Test → Fill details → Add questions with options & correct answers\n\n"
        "✏️ <b>Enter Marks</b>\n"
        "Tap Enter Test Marks → Select Test → Enter marks for each student\n\n"
        "📢 <b>Announcements</b>\n"
        "Tap Announcement → Select target class → Type message → Send"
    ),

    "owner": (
        "❓ <b>Owner Help Guide</b>\n\n"
        "👥 <b>Add Students</b>\n"
        "Tap Students → Add Student → Fill all 7 fields → Create ID & Password\n\n"
        "👨‍🏫 <b>Add Teachers</b>\n"
        "Tap Teachers → Add Teacher → Fill details → Assign classes & subjects\n\n"
        "📊 <b>Attendance Reports</b>\n"
        "Tap Attendance Reports → Select Class → View summary → Send to Parents\n\n"
        "📝 <b>Test Reports</b>\n"
        "Tap Test Reports → Select Test → View results → Send to Parents\n\n"
        "🎁 <b>Referral Program</b>\n"
        "Share your referral code with other coaching owners\n"
        "Each successful referral = 5% subscription discount\n\n"
        "📞 <b>Support?</b>\n"
        "Contact Naganaverse support via Settings."
    ),

    "super_admin": (
        "❓ <b>Super Admin Help Guide</b>\n\n"
        "🏫 <b>Institution Management</b>\n"
        "Approve, freeze, or delete coaching institutions\n\n"
        "🔗 <b>Unbind Telegram</b>\n"
        "Use User Management → Unbind Telegram ID to fix login issues\n\n"
        "🚨 <b>Emergency Controls</b>\n"
        "Platform Controls → Pause registrations or enable maintenance mode\n\n"
        "📜 <b>Audit Logs</b>\n"
        "Full trail of all system actions with timestamps\n\n"
        "📢 <b>Broadcast</b>\n"
        "Broadcast System → Select target → Type message → Send to all"
    ),

    "default": (
        "❓ <b>Naganaverse Help</b>\n\n"
        "Welcome to Naganaverse Education Bot.\n\n"
        "To get started:\n"
        "• Tap <b>Login</b> and enter your User ID + Password\n"
        "• First-time users: tap <b>Register Institution</b>\n\n"
        "For support, contact your institution administrator."
    ),
}


@router.message(Command("help"))
async def cmd_help(message: Message, user_session: dict = None) -> None:
    role = user_session.get("role", "default") if user_session else "default"
    text = _HELP_TEXT.get(role, _HELP_TEXT["default"])
    await message.answer(text, reply_markup=nav_only_keyboard())


@router.callback_query(F.data.in_({"help", "nav:help"}))
async def cb_help(callback: CallbackQuery, user_session: dict = None) -> None:
    await callback.answer()
    role = user_session.get("role", "default") if user_session else "default"
    text = _HELP_TEXT.get(role, _HELP_TEXT["default"])
    try:
        await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=nav_only_keyboard())
