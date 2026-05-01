"""
services/test_service.py
─────────────────────────────────────────────────────────────
Test Engine.

Modes:
  1. Online test: questions sequentially → auto-score
  2. Custom/Offline test feed: teacher manually enters marks
  3. Test reports: summary for owner + parent notification

Auto-scoring: compares student answer to correct_answer, sums marks.
Analytics: Highest, Lowest, Average score per test.
─────────────────────────────────────────────────────────────
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from loguru import logger

from database.models.test_model import Test, TestQuestion, TestResult
from database.repositories.test_repo import TestRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.user_repo_security import AuditLogRepository

_test_repo = TestRepository()
_student_repo = StudentRepository()
_audit = AuditLogRepository()


# ── Test Creation ──────────────────────────────────────────

async def create_test(
    org_id: str,
    class_name: str,
    subject_name: str,
    teacher_id: str,
    test_name: str,
    topic: str = None,
    test_date: date = None,
    questions: List[dict] = None,
) -> dict:
    """
    Create a test with questions.

    Each question dict:
    {
        "question_text": str,
        "option_a": str, "option_b": str,
        "option_c": str, "option_d": str,
        "correct_answer": str,   # "A"|"B"|"C"|"D"
        "marks": int,            # default 1
    }
    """
    if test_date is None:
        test_date = date.today()

    total_marks = sum(q.get("marks", 1) for q in (questions or []))

    test = Test(
        org_id=org_id,
        test_name=test_name,
        class_name=class_name,
        subject_name=subject_name,
        topic=topic,
        teacher_id=teacher_id,
        test_date=test_date,
        total_marks=total_marks,
    )
    saved_test = await _test_repo.create_test(test)

    saved_questions = []
    for q in (questions or []):
        question = TestQuestion(
            test_id=saved_test.test_id,
            question_text=q["question_text"],
            option_a=q.get("option_a"),
            option_b=q.get("option_b"),
            option_c=q.get("option_c"),
            option_d=q.get("option_d"),
            correct_answer=q["correct_answer"].upper(),
            marks=q.get("marks", 1),
        )
        saved_q = await _test_repo.add_question(question)
        saved_questions.append(saved_q)

    await _audit.log(
        "TEST_CREATED",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={
            "test_name": test_name, "class": class_name,
            "subject": subject_name, "questions": len(saved_questions),
        },
    )

    logger.info(
        f"Test created | org={org_id} | '{test_name}' "
        f"| class={class_name} | {len(saved_questions)} questions"
    )

    return {
        "success": True,
        "test": saved_test,
        "questions": saved_questions,
        "message": (
            f"✅ <b>Test Created</b>\n\n"
            f"📝 {test_name}\n"
            f"📚 Class: {class_name} | 📖 {subject_name}\n"
            f"❓ Questions: {len(saved_questions)}\n"
            f"🎯 Total Marks: {total_marks}"
        ),
    }


# ── Test Attempt (Online Test) ─────────────────────────────

async def submit_test(
    student_id: str,
    org_id: str,
    test_id: str,
    answers: dict,    # {question_id: "A"|"B"|"C"|"D"}
) -> dict:
    """
    Auto-score a student's test submission.
    Saves individual attempts + final result.
    Returns score, rank, and result message.
    """
    questions = await _test_repo.get_questions(test_id)
    if not questions:
        return {"success": False, "message": "❌ Test not found."}

    total_marks = 0
    earned_marks = Decimal("0")

    for q in questions:
        student_answer = answers.get(str(q.id), "").upper()
        await _test_repo.save_attempt(student_id, str(q.id), test_id, student_answer)

        total_marks += q.marks
        if student_answer == q.correct_answer.upper():
            earned_marks += Decimal(str(q.marks))

    # Save final result
    result = TestResult(
        org_id=org_id,
        test_id=test_id,
        student_id=student_id,
        marks=earned_marks,
    )
    saved_result = await _test_repo.save_result(result)

    # Calculate rank
    rank = await _get_student_rank(test_id, student_id, org_id)

    percentage = round(float(earned_marks / total_marks * 100), 1) if total_marks > 0 else 0

    await _audit.log(
        "TEST_SUBMITTED",
        user_id=student_id, role="student", org_id=org_id,
        details={
            "test_id": test_id, "marks": float(earned_marks),
            "total": total_marks, "percentage": percentage,
        },
    )

    return {
        "success": True,
        "marks": float(earned_marks),
        "total_marks": total_marks,
        "percentage": percentage,
        "rank": rank,
        "message": (
            f"🎯 <b>Test Completed!</b>\n\n"
            f"✅ Score: <b>{earned_marks}/{total_marks}</b>\n"
            f"📊 Percentage: {percentage}%\n"
            f"🏆 Rank: #{rank}"
        ),
    }


async def save_manual_marks(
    org_id: str,
    test_id: str,
    teacher_id: str,
    marks_data: List[dict],   # [{"student_id": str, "marks": float}]
) -> dict:
    """
    Offline test feed — teacher manually enters marks for each student.
    Used for pen-paper tests.
    """
    saved = 0
    for entry in marks_data:
        result = TestResult(
            org_id=org_id,
            test_id=test_id,
            student_id=entry["student_id"],
            marks=Decimal(str(entry["marks"])),
        )
        await _test_repo.save_result(result)
        saved += 1

    await _audit.log(
        "TEST_MARKS_ENTERED",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={"test_id": test_id, "students": saved},
    )

    return {
        "success": True,
        "saved": saved,
        "message": f"✅ Marks saved for {saved} students.",
    }


# ── Analytics ──────────────────────────────────────────────

async def get_test_summary(test_id: str, org_id: str) -> dict:
    """
    Teacher / Owner: test performance summary.
    Returns highest, lowest, average + student names.
    """
    summary = await _test_repo.get_test_summary(test_id, org_id)
    test = await _test_repo.get_test_by_id(test_id, org_id)

    if not summary or not test:
        return {"success": False, "message": "❌ Test data not found."}

    return {
        "success": True,
        "test": test,
        "summary": summary,
        "message": (
            f"📊 <b>Test Report</b>\n\n"
            f"📝 {test.test_name}\n"
            f"📅 {test.test_date}\n\n"
            f"🏆 Highest: <b>{summary.get('highest_student','—')} — {summary.get('highest','—')}</b>\n"
            f"📉 Lowest:  <b>{summary.get('lowest_student','—')} — {summary.get('lowest','—')}</b>\n"
            f"📊 Average: <b>{summary.get('average','—')}</b>\n"
            f"👥 Attempts: {summary.get('total_attempts', 0)}"
        ),
    }


async def get_student_test_history(student_id: str, org_id: str) -> str:
    """Previous test results for a student."""
    results = await _test_repo.get_student_results(student_id, org_id)

    if not results:
        return "📋 No test results found yet."

    lines = ["📋 <b>My Test Results</b>\n"]
    for r in results:
        total = r.get("total_marks", 0)
        marks = r.get("marks", 0)
        pct = round(float(marks / total * 100), 1) if total > 0 else 0
        lines.append(
            f"📝 {r['test_name']} — {r['subject_name']}\n"
            f"   Score: <b>{marks}/{total}</b> ({pct}%)\n"
        )

    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────

async def _get_student_rank(test_id: str, student_id: str, org_id: str) -> int:
    """Calculate student's rank in a test (1 = highest)."""
    from database.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rank = await conn.fetchval(
            """
            SELECT COUNT(*) + 1 FROM test_results
            WHERE test_id = $1 AND org_id = $2 AND marks > (
                SELECT marks FROM test_results
                WHERE test_id = $1 AND student_id = $3
            )
            """,
            test_id, org_id, student_id,
        )
    return rank or 1
