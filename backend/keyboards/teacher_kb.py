"""
keyboards/teacher_kb.py
─────────────────────────────────────────────────────────────
All keyboards used in teacher-facing screens.
─────────────────────────────────────────────────────────────
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.common_kb import nav_row


def teacher_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main teacher dashboard — 9 menu buttons + nav row."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Attendance",        callback_data="teacher:attendance"),
            InlineKeyboardButton(text="📂 Manage Notes",      callback_data="teacher:manage_notes"),
        ],
        [
            InlineKeyboardButton(text="📌 Send Homework",     callback_data="teacher:send_homework"),
            InlineKeyboardButton(text="📝 Create Test",       callback_data="teacher:create_test"),
        ],
        [
            InlineKeyboardButton(text="✏️ Enter Test Marks",  callback_data="teacher:enter_marks"),
            InlineKeyboardButton(text="📢 Announcement",      callback_data="teacher:announcement"),
        ],
        [
            InlineKeyboardButton(text="🗂 Resource Library",  callback_data="teacher:resource_library"),
            InlineKeyboardButton(text="👥 Students",          callback_data="teacher:view_students"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings",          callback_data="teacher:settings"),
        ],
        nav_row(),
    ])


def class_select_keyboard(classes: list, prefix: str) -> InlineKeyboardMarkup:
    """Dynamic class buttons from teacher's assigned_classes."""
    rows = []
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


def subject_select_keyboard(subjects: list, prefix: str) -> InlineKeyboardMarkup:
    """Dynamic subject buttons."""
    rows = []
    for i in range(0, len(subjects), 2):
        row = []
        for subj in subjects[i:i+2]:
            row.append(InlineKeyboardButton(
                text=f"📖 {subj}",
                callback_data=f"{prefix}:{subj}"
            ))
        rows.append(row)
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def attendance_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Take Attendance",        callback_data="teacher:att_take")],
        [InlineKeyboardButton(text="📅 Manual Attendance Feed", callback_data="teacher:att_manual")],
        [InlineKeyboardButton(text="📊 Attendance History",     callback_data="teacher:att_history")],
        nav_row(),
    ])


def absent_students_keyboard(students: list, absent_ids: set) -> InlineKeyboardMarkup:
    """
    Tap-to-toggle absent student buttons.
    Absent = ❌ prefix, Present = ✅ prefix.
    """
    rows = []
    for i in range(0, len(students), 2):
        row = []
        for s in students[i:i+2]:
            is_absent = s.student_id in absent_ids
            label = f"❌ {s.name}" if is_absent else f"✅ {s.name}"
            row.append(InlineKeyboardButton(
                text=label,
                callback_data=f"att_toggle:{s.student_id}"
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="💾 Submit Attendance", callback_data="att_submit"),
    ])
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def paginated_attendance_keyboard(
    students: list,        # list of dicts: {student_id, name, roll_number}
    absent_ids: set,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """
    Paginated attendance keyboard — 10 students per page.
    Each student button toggles ✅/❌.
    Navigation: ⬅️ Back | 🟢 All Present | ➡️ Next
    Bottom: ✅ Submit
    """
    rows = []

    # Student buttons — 1 per row for clarity
    for s in students:
        sid     = s["student_id"]
        name    = s["name"]
        roll    = s.get("roll_number") or ""
        absent  = sid in absent_ids
        prefix  = "❌" if absent else "✅"
        label   = f"{prefix} {roll}. {name}" if roll else f"{prefix} {name}"
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"att_toggle:{sid}",
            )
        ])

    # Navigation row
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Back",  callback_data="att_page:prev"))
    nav.append(InlineKeyboardButton(text="🟢 All Present", callback_data="att_all_present"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️ Next",  callback_data="att_page:next"))
    rows.append(nav)

    # Submit button
    rows.append([
        InlineKeyboardButton(text="✅ Submit Attendance", callback_data="att_submit"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def manage_notes_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Upload Notes",       callback_data="notes:upload")],
        [InlineKeyboardButton(text="📋 View Uploads",        callback_data="notes:view")],
        [InlineKeyboardButton(text="🗑 Delete File",         callback_data="notes:delete")],
        nav_row(),
    ])


def resource_type_keyboard(prefix: str = "upload_type") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Notes",               callback_data=f"{prefix}:notes"),
            InlineKeyboardButton(text="📝 Worksheet",           callback_data=f"{prefix}:worksheet"),
        ],
        [
            InlineKeyboardButton(text="📋 Important Questions", callback_data=f"{prefix}:important_questions"),
            InlineKeyboardButton(text="📖 PYQ",                 callback_data=f"{prefix}:pyq"),
        ],
        [
            InlineKeyboardButton(text="🔖 Practice Sheet",      callback_data=f"{prefix}:practice_sheet"),
        ],
        nav_row(),
    ])


def homework_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send Homework",          callback_data="hw:send")],
        [InlineKeyboardButton(text="📅 Custom Homework Feed",   callback_data="hw:custom")],
        [InlineKeyboardButton(text="📚 Homework History",       callback_data="hw:history")],
        nav_row(),
    ])


def confirm_homework_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm & Send", callback_data="hw:confirm"),
            InlineKeyboardButton(text="✏️ Edit",           callback_data="hw:edit"),
        ],
        nav_row(),
    ])


def tests_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Create Test",          callback_data="test:create")],
        [InlineKeyboardButton(text="📊 Send Test Reports",    callback_data="test:send_reports")],
        [InlineKeyboardButton(text="📅 Custom Test Feed",     callback_data="test:custom_feed")],
        [InlineKeyboardButton(text="📋 Test History",         callback_data="test:history")],
        nav_row(),
    ])


def announcement_target_keyboard(role: str = "teacher") -> InlineKeyboardMarkup:
    if role == "owner":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 All Students",     callback_data="ann:all_students")],
            [InlineKeyboardButton(text="📚 Specific Class",   callback_data="ann:class")],
            [InlineKeyboardButton(text="👨‍🏫 Teachers",        callback_data="ann:teachers")],
            nav_row(),
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Specific Class",       callback_data="ann:class")],
        [InlineKeyboardButton(text="👥 All My Students",      callback_data="ann:all_students")],
        nav_row(),
    ])


def test_select_keyboard(tests: list) -> InlineKeyboardMarkup:
    rows = []
    for t in tests:
        rows.append([
            InlineKeyboardButton(
                text=f"📝 {t.test_name} — {t.subject_name}",
                callback_data=f"test:select:{t.test_id}"
            )
        ])
    rows.append(nav_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
