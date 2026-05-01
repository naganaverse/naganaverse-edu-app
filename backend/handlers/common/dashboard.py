"""
handlers/common/dashboard.py
─────────────────────────────────────────────────────────────
Single source of truth for building role dashboards.

Both start.py and login.py import build_dashboard() from here.
Any future dashboard text/keyboard changes are made ONCE here.
─────────────────────────────────────────────────────────────
"""

from keyboards.parent_kb import parent_dashboard_keyboard
from keyboards.common_kb import nav_only_keyboard
from keyboards.student_kb import student_dashboard_keyboard
from keyboards.teacher_kb import teacher_dashboard_keyboard
from keyboards.owner_kb import owner_dashboard_keyboard
from keyboards.superadmin_kb import superadmin_dashboard_keyboard


def build_dashboard(session: dict) -> tuple:
    """
    Build (text, keyboard) for any role dashboard.

    Used by:
      - start.py  — auto-login render
      - login.py  — post-manual-login render

    Returns:
        (text: str, keyboard: InlineKeyboardMarkup)
    """
    role = session.get("role")

    if role == "student":
        text = (
            f"🎓 <b>Welcome to Naganaverse Education</b>\n"
            f"🏫 {session.get('org_name', session.get('org_id', ''))}\n\n"
            f"👤 Student: <b>{session.get('name')}</b>\n"
            f"📚 Class: {session.get('class_name', '—')}\n"
            f"🔢 Roll No: {session.get('roll_number', '—')}"
        )
        return text, student_dashboard_keyboard()

    elif role == "teacher":
        subjects = ", ".join(session.get("subjects", [])) or "—"
        text = (
            f"🎓 <b>Welcome to Naganaverse Education</b>\n"
            f"🏫 {session.get('org_name', session.get('org_id', ''))}\n\n"
            f"Logged in as:\n"
            f"👨‍🏫 Teacher — <b>{session.get('name')}</b>\n"
            f"📖 Subjects: {subjects}"
        )
        return text, teacher_dashboard_keyboard()

    elif role == "owner":
        text = (
            f"🎓 <b>Welcome to Naganaverse Education</b>\n"
            f"🏫 {session.get('org_name', session.get('org_id', ''))}\n\n"
            f"Logged in as:\n"
            f"🏢 Owner — <b>{session.get('name')}</b>\n"
            f"📦 Plan: {session.get('plan_type', 'starter').title()}"
        )
        return text, owner_dashboard_keyboard()

    elif role == "super_admin":
        text = (
            f"🛡 <b>Naganaverse Control Center</b>\n\n"
            f"Role: <b>Super Admin</b>\n"
            f"ID: {session.get('telegram_id')}"
        )
        return text, superadmin_dashboard_keyboard()

    elif role == "parent":
        student_name = session.get("student_name", "Your Child")
        text = (
            f"👨‍👩‍👧 <b>Parent Dashboard</b>\n"
            f"🏫 {session.get('org_name', session.get('org_id', ''))}\n\n"
            f"👤 Child: <b>{student_name}</b>\n"
            f"View attendance, test scores and announcements below."
        )
        return text, parent_dashboard_keyboard()

    return "Welcome to Naganaverse.", nav_only_keyboard()
