"""
handlers/teacher/tests_handler.py
─────────────────────────────────────────────────────────────
FSM Flows:

A) Create Test:
   TEST_SELECT_CLASS → TEST_SELECT_SUBJECT → TEST_ENTER_NAME
   → TEST_ADD_QUESTIONS (loop) → done

B) Enter Manual Marks:
   MARKS_SELECT_TEST → MARKS_ENTER_DATA → saved

C) Send Test Reports to parents
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsTeacher
from services.test_service import (
    create_test, save_manual_marks, get_test_summary, get_student_test_history
)
from services.notification_service import send_test_results_to_parents
from services.teacher_service import get_assigned_classes, get_assigned_subjects
from keyboards.teacher_kb import (
    class_select_keyboard, subject_select_keyboard,
    tests_menu_keyboard, test_select_keyboard,
)
from keyboards.common_kb import nav_only_keyboard, confirm_keyboard
from database.repositories.test_repo import TestRepository
from database.repositories.student_repo import StudentRepository

router = Router()
router.message.filter(IsTeacher())
router.callback_query.filter(IsTeacher())

_test_repo = TestRepository()
_student_repo = StudentRepository()


# ── FSM States ────────────────────────────────────────────

class CreateTestFSM(StatesGroup):
    select_class   = State()
    select_subject = State()
    enter_name     = State()
    add_questions  = State()


class MarksFSM(StatesGroup):
    select_test  = State()
    enter_data   = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "teacher:create_test")
async def cb_tests_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📝 <b>Tests</b>\n\nChoose an option:",
        reply_markup=tests_menu_keyboard(),
    )


# ── A) Create Test ────────────────────────────────────────

@router.callback_query(F.data == "test:create")
async def cb_create_test_start(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    classes = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if not classes:
        await callback.message.edit_text("❌ No classes assigned.", reply_markup=nav_only_keyboard())
        return
    await state.set_state(CreateTestFSM.select_class)
    await callback.message.edit_text(
        "📝 <b>Create Test</b>\n\nStep 1 — Select Class:",
        reply_markup=class_select_keyboard(classes, "ct_class"),
    )


@router.callback_query(CreateTestFSM.select_class, F.data.startswith("ct_class:"))
async def cb_ct_class(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    assigned = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if class_name not in assigned:
        await callback.message.edit_text("❌ Not your class.", reply_markup=nav_only_keyboard())
        await state.clear()
        return
    subjects = await get_assigned_subjects(user_session["user_id"], user_session["org_id"])
    await state.update_data(class_name=class_name)
    await state.set_state(CreateTestFSM.select_subject)
    await callback.message.edit_text(
        f"📝 <b>Create Test</b>\n📚 {class_name}\n\nStep 2 — Select Subject:",
        reply_markup=subject_select_keyboard(subjects, "ct_subject"),
    )


@router.callback_query(CreateTestFSM.select_subject, F.data.startswith("ct_subject:"))
async def cb_ct_subject(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    subject_name = callback.data.split(":", 1)[1]
    await state.update_data(subject_name=subject_name, questions=[])
    await state.set_state(CreateTestFSM.enter_name)
    data = await state.get_data()
    await callback.message.edit_text(
        f"📝 <b>Create Test</b>\n📚 {data['class_name']} | 📖 {subject_name}\n\n"
        "Step 3 — Enter Test Name:\n<i>Example: Unit Test 1</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(CreateTestFSM.enter_name)
async def msg_ct_name(message: Message, state: FSMContext) -> None:
    test_name = message.text.strip()
    if len(test_name) < 3:
        await message.answer("❌ Name too short.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(test_name=test_name, questions=[], q_count=0)
    await state.set_state(CreateTestFSM.add_questions)
    await message.answer(
        f"📝 <b>Test: {test_name}</b>\n\n"
        "Step 4 — Add Questions.\n\n"
        "Send each question in this format:\n\n"
        "<code>Question: What is Newton's First Law?\n"
        "A: Object at rest stays at rest\n"
        "B: Force equals mass times acceleration\n"
        "C: Every action has equal reaction\n"
        "D: None of above\n"
        "Answer: A\n"
        "Marks: 1</code>\n\n"
        "Send <b>DONE</b> when finished.",
        reply_markup=nav_only_keyboard(),
    )


@router.message(CreateTestFSM.add_questions)
async def msg_ct_question(message: Message, state: FSMContext, user_session: dict) -> None:
    text = message.text.strip()

    if text.upper() == "DONE":
        data = await state.get_data()
        questions = data.get("questions", [])
        if not questions:
            await message.answer("❌ Add at least one question before finishing.")
            return
        await _save_test(message, state, user_session, data)
        return

    # Parse question block
    parsed = _parse_question(text)
    if not parsed:
        await message.answer(
            "❌ Wrong format. Please follow the template.\n"
            "Send <b>DONE</b> to finish.",
            reply_markup=nav_only_keyboard(),
        )
        return

    data = await state.get_data()
    questions = data.get("questions", [])
    questions.append(parsed)
    q_count = len(questions)
    await state.update_data(questions=questions, q_count=q_count)

    await message.answer(
        f"✅ Question {q_count} added.\n\n"
        "Send next question or type <b>DONE</b> to finish.",
        reply_markup=nav_only_keyboard(),
    )


async def _save_test(message: Message, state: FSMContext, user_session: dict, data: dict) -> None:
    from datetime import date
    result = await create_test(
        org_id=user_session["org_id"],
        class_name=data["class_name"],
        subject_name=data["subject_name"],
        teacher_id=user_session["user_id"],
        test_name=data["test_name"],
        test_date=date.today(),
        questions=data["questions"],
    )
    await state.clear()
    await message.answer(result["message"], reply_markup=nav_only_keyboard())


def _parse_question(text: str) -> dict | None:
    """Parse teacher-formatted question block into dict."""
    try:
        lines = {
            line.split(":", 1)[0].strip().lower(): line.split(":", 1)[1].strip()
            for line in text.strip().splitlines()
            if ":" in line
        }
        return {
            "question_text": lines.get("question", ""),
            "option_a":      lines.get("a", ""),
            "option_b":      lines.get("b", ""),
            "option_c":      lines.get("c", ""),
            "option_d":      lines.get("d", ""),
            "correct_answer": lines.get("answer", "A").upper(),
            "marks":          int(lines.get("marks", 1)),
        }
    except Exception:
        return None


# ── B) Enter Manual Marks ─────────────────────────────────

@router.callback_query(F.data.in_({"teacher:enter_marks", "test:custom_feed"}))
async def cb_marks_start(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    tests = await _test_repo.get_by_teacher(user_session["user_id"], user_session["org_id"])
    if not tests:
        await callback.message.edit_text(
            "❌ No tests found. Create a test first.", reply_markup=nav_only_keyboard()
        )
        return
    await state.set_state(MarksFSM.select_test)
    await callback.message.edit_text(
        "✏️ <b>Enter Test Marks</b>\n\nSelect a test:",
        reply_markup=test_select_keyboard(tests),
    )


@router.callback_query(MarksFSM.select_test, F.data.startswith("test:select:"))
async def cb_marks_test_selected(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    test_id = callback.data.split(":", 2)[2]
    org_id  = user_session["org_id"]

    test = await _test_repo.get_test_by_id(test_id, org_id)
    if not test:
        await callback.message.edit_text("❌ Test not found.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    students = await _student_repo.get_by_class(org_id, test.class_name)
    if not students:
        await callback.message.edit_text("❌ No students found.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    student_list = "\n".join(f"{i+1}. {s.name} ({s.student_id})" for i, s in enumerate(students))
    await state.update_data(
        test_id=test_id,
        class_name=test.class_name,
        students={s.student_id: s.name for s in students},
    )
    await state.set_state(MarksFSM.enter_data)

    await callback.message.edit_text(
        f"✏️ <b>Enter Marks — {test.test_name}</b>\n"
        f"📚 {test.class_name} | 📖 {test.subject_name}\n"
        f"🎯 Total Marks: {test.total_marks}\n\n"
        f"<b>Students:</b>\n{student_list}\n\n"
        "Enter marks in this format:\n"
        "<code>STD001:18\nSTD002:15\nSTD003:20</code>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(MarksFSM.enter_data)
async def msg_marks_entry(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    raw = message.text.strip()
    marks_data = []
    errors = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            errors.append(f"Invalid: {line}")
            continue
        parts = line.split(":", 1)
        student_id = parts[0].strip().upper()
        try:
            marks = float(parts[1].strip())
            marks_data.append({"student_id": student_id, "marks": marks})
        except ValueError:
            errors.append(f"Invalid marks for {student_id}")

    if not marks_data:
        await message.answer(
            "❌ Could not parse any marks. Format:\n<code>STD001:18\nSTD002:15</code>",
            reply_markup=nav_only_keyboard(),
        )
        return

    data = await state.get_data()
    result = await save_manual_marks(
        org_id=user_session["org_id"],
        test_id=data["test_id"],
        teacher_id=user_session["user_id"],
        marks_data=marks_data,
    )
    await state.clear()

    extra = f"\n⚠️ Skipped: {', '.join(errors)}" if errors else ""
    await message.answer(
        result["message"] + extra,
        reply_markup=nav_only_keyboard(),
    )


# ── C) Send Test Reports ──────────────────────────────────

@router.callback_query(F.data == "test:send_reports")
async def cb_send_reports_start(
    callback: CallbackQuery, user_session: dict
) -> None:
    await callback.answer()
    tests = await _test_repo.get_by_teacher(user_session["user_id"], user_session["org_id"])
    if not tests:
        await callback.message.edit_text("❌ No tests found.", reply_markup=nav_only_keyboard())
        return
    await callback.message.edit_text(
        "📊 <b>Send Test Reports</b>\n\nSelect a test:",
        reply_markup=test_select_keyboard(tests),
    )


@router.callback_query(F.data.startswith("test:send_report:"))
async def cb_send_report_selected(
    callback: CallbackQuery, user_session: dict
) -> None:
    await callback.answer("Sending reports...")
    test_id    = callback.data.split(":", 2)[2]
    org_id     = user_session["org_id"]
    teacher_id = user_session["user_id"]

    test = await _test_repo.get_test_by_id(test_id, org_id)
    if not test:
        await callback.message.edit_text("❌ Test not found.", reply_markup=nav_only_keyboard())
        return

    summary = await get_test_summary(test_id, org_id)
    await callback.message.edit_text(
        summary["message"] + "\n\n📲 Sending reports to parents...",
        reply_markup=nav_only_keyboard(),
    )

    result = await send_test_results_to_parents(
        org_id=org_id,
        test_id=test_id,
        class_name=test.class_name,
        triggered_by=teacher_id,
    )
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


# ── Test History ──────────────────────────────────────────

@router.callback_query(F.data == "test:history")
async def cb_test_history(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    tests = await _test_repo.get_by_teacher(user_session["user_id"], user_session["org_id"])
    if not tests:
        await callback.message.edit_text("📋 No tests yet.", reply_markup=nav_only_keyboard())
        return
    lines = ["📋 <b>Test History</b>\n"]
    for t in tests:
        lines.append(
            f"📝 {t.test_name} | 📖 {t.subject_name}\n"
            f"   📚 {t.class_name} | 📅 {t.test_date} | 🎯 {t.total_marks} marks\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=nav_only_keyboard())
