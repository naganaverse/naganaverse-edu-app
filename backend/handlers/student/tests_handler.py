"""
handlers/student/tests_handler.py
─────────────────────────────────────────────────────────────
FSM States:
  TEST_SELECT            → show available tests for student's class
  TEST_START             → show test details, await "Start Test"
  TEST_ANSWER_QUESTIONS  → questions sent one at a time, answers stored
  TEST_SUBMIT_RESULTS    → auto-score, show marks + rank

Business Logic:
  - Each question shown sequentially with A/B/C/D buttons
  - Answers stored in FSM dict: {question_id: answer}
  - On final question: call test_service.submit_test()
  - Result shows: marks, total, percentage, rank

Security:
  - IsStudent filter
  - org_id + class_name on every query
  - student cannot re-attempt same test (ON CONFLICT in repo)
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from core.filters import IsStudent
from services.test_service import submit_test, get_student_test_history
from keyboards.student_kb import (
    available_tests_keyboard,
    start_test_keyboard,
    answer_keyboard,
    tests_menu_keyboard,
)
from keyboards.common_kb import nav_only_keyboard
from database.repositories.test_repo import TestRepository

router = Router()
router.callback_query.filter(IsStudent())

_test_repo = TestRepository()


class TestFSM(StatesGroup):
    select_test      = State()
    start_test       = State()
    answer_questions = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "student:tests")
async def cb_tests_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📝 <b>Tests</b>\n\nChoose an option:",
        reply_markup=tests_menu_keyboard(),
    )


@router.callback_query(F.data == "student:tests_available")
async def cb_tests_available(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    await callback.answer()
    org_id     = user_session["org_id"]
    class_name = user_session.get("class_name", "")

    tests = await _test_repo.get_tests_by_class(org_id, class_name)
    if not tests:
        await callback.message.edit_text(
            "📝 No tests available right now.\nCheck back later!",
            reply_markup=nav_only_keyboard(),
        )
        return

    # Convert to list of dicts for keyboard
    tests_data = [
        {"test_id": str(t.test_id), "test_name": t.test_name, "subject_name": t.subject_name}
        for t in tests
    ]
    await state.set_state(TestFSM.select_test)
    await callback.message.edit_text(
        f"📝 <b>Available Tests</b>\n"
        f"📚 {class_name}\n\n"
        "Select a test to attempt:",
        reply_markup=available_tests_keyboard(tests_data),
    )


# ── State 1: Test selected ────────────────────────────────

@router.callback_query(TestFSM.select_test, F.data.startswith("student:start_test:"))
async def cb_test_selected(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    await callback.answer()
    test_id = callback.data.split(":", 2)[2]
    org_id  = user_session["org_id"]

    test = await _test_repo.get_test_by_id(test_id, org_id)
    if not test:
        await callback.message.edit_text(
            "❌ Test not found.", reply_markup=nav_only_keyboard()
        )
        await state.clear()
        return

    questions = await _test_repo.get_questions(test_id)
    if not questions:
        await callback.message.edit_text(
            "❌ This test has no questions yet.", reply_markup=nav_only_keyboard()
        )
        await state.clear()
        return

    await state.update_data(
        test_id=test_id,
        test_name=test.test_name,
        total_marks=test.total_marks,
        questions=[
            {
                "id": str(q.id),
                "text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "marks": q.marks,
            }
            for q in questions
        ],
        current_q=0,
        answers={},
    )
    await state.set_state(TestFSM.start_test)

    await callback.message.edit_text(
        f"📝 <b>{test.test_name}</b>\n\n"
        f"📖 Subject: {test.subject_name}\n"
        f"📚 Class: {test.class_name}\n"
        f"❓ Questions: {len(questions)}\n"
        f"🎯 Total Marks: {test.total_marks}\n\n"
        "Tap <b>Start Test</b> when ready.",
        reply_markup=start_test_keyboard(test_id),
    )


# ── State 2: Start Test ───────────────────────────────────

@router.callback_query(TestFSM.start_test, F.data.startswith("student:begin_test:"))
async def cb_begin_test(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer("Starting test...")
    await state.set_state(TestFSM.answer_questions)
    await _send_question(callback.message, state, edit=True)


# ── State 3: Answer Questions ─────────────────────────────

@router.callback_query(TestFSM.answer_questions, F.data.startswith("ans:"))
async def cb_answer(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    await callback.answer()
    parts       = callback.data.split(":")   # ans:question_id:ANSWER
    question_id = parts[1]
    answer      = parts[2].upper()

    data    = await state.get_data()
    answers = data.get("answers", {})
    answers[question_id] = answer

    current_q = data.get("current_q", 0) + 1
    questions = data.get("questions", [])

    await state.update_data(answers=answers, current_q=current_q)

    if current_q >= len(questions):
        # All questions answered — submit
        await _submit_test(callback, state, user_session)
        return

    await _send_question(callback.message, state, edit=True)


async def _send_question(message, state: FSMContext, edit: bool = False) -> None:
    """Send the current question as inline MCQ."""
    data      = await state.get_data()
    questions = data.get("questions", [])
    current_q = data.get("current_q", 0)

    if current_q >= len(questions):
        return

    q     = questions[current_q]
    total = len(questions)
    text  = (
        f"📝 <b>Question {current_q + 1} / {total}</b>\n\n"
        f"{q['text']}\n\n"
        f"A: {q.get('option_a', '—')}\n"
        f"B: {q.get('option_b', '—')}\n"
        f"C: {q.get('option_c', '—')}\n"
        f"D: {q.get('option_d', '—')}\n\n"
        f"🎯 Marks: {q.get('marks', 1)}"
    )
    kb = answer_keyboard(q["id"])

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def _submit_test(
    callback: CallbackQuery,
    state: FSMContext,
    user_session: dict,
) -> None:
    """Auto-score and display result."""
    data       = await state.get_data()
    test_id    = data["test_id"]
    answers    = data.get("answers", {})
    org_id     = user_session["org_id"]
    student_id = user_session["user_id"]

    await callback.message.edit_text("⏳ Calculating your score...")

    result = await submit_test(
        student_id=student_id,
        org_id=org_id,
        test_id=test_id,
        answers=answers,
    )
    await state.clear()
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())


# ── Previous Results ──────────────────────────────────────

@router.callback_query(F.data == "student:tests_results")
async def cb_test_results(
    callback: CallbackQuery,
    user_session: dict,
) -> None:
    await callback.answer()
    text = await get_student_test_history(
        user_session["user_id"], user_session["org_id"]
    )
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())
