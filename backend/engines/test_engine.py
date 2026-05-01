"""
engines/test_engine.py
─────────────────────────────────────────────────────────────
Core Test Engine.

Differs from test_service:
  - Service handles bot UI, FSM, and per-question routing
  - Engine handles pure evaluation logic, analytics calculation,
    and offline feed processing

Exposed functions:
  evaluate_answers()          — auto-score test attempt
  generate_summary_analytics()— Highest/Lowest/Average per test
  process_offline_feed()      — bulk mark entry for pen-paper tests
  get_upcoming_tests()        — used by scheduler at 6 PM
─────────────────────────────────────────────────────────────
"""

from decimal import Decimal
from typing import Dict, List, Optional

from loguru import logger

from database.connection import get_pool
from database.models.test_model import TestResult
from database.repositories.test_repo import TestRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.user_repo_security import AuditLogRepository

_test_repo    = TestRepository()
_student_repo = StudentRepository()
_audit        = AuditLogRepository()


async def evaluate_answers(
    student_id: str,
    org_id: str,
    test_id: str,
    answers: Dict[str, str],   # {question_id: "A"|"B"|"C"|"D"}
) -> dict:
    """
    Compare student answers against correct_answer for each question.
    Save per-question attempts + final result.

    Returns:
        {
          "success": bool,
          "earned_marks": float,
          "total_marks": int,
          "percentage": float,
          "correct": int,
          "wrong": int,
          "rank": int,
        }
    """
    questions = await _test_repo.get_questions(test_id)
    if not questions:
        return {"success": False, "message": "Test has no questions."}

    total_marks  = 0
    earned_marks = Decimal("0")
    correct      = 0
    wrong        = 0

    for q in questions:
        student_ans = answers.get(str(q.id), "").upper().strip()

        # Save attempt record
        await _test_repo.save_attempt(
            student_id=student_id,
            question_id=str(q.id),
            test_id=test_id,
            answer=student_ans,
        )

        total_marks += q.marks
        if student_ans == q.correct_answer.upper():
            earned_marks += Decimal(str(q.marks))
            correct += 1
        else:
            wrong += 1

    # Save final result
    result_record = TestResult(
        org_id=org_id,
        test_id=test_id,
        student_id=student_id,
        marks=earned_marks,
    )
    await _test_repo.save_result(result_record)

    # Calculate rank
    rank = await _get_rank(test_id, student_id, org_id)
    pct  = round(float(earned_marks / total_marks * 100), 1) if total_marks > 0 else 0.0

    await _audit.log(
        "TEST_EVALUATED",
        user_id=student_id, role="student", org_id=org_id,
        details={
            "test_id": test_id, "marks": float(earned_marks),
            "total": total_marks, "percentage": pct, "rank": rank,
        },
    )

    logger.info(
        f"Test evaluated | student={student_id} | test={test_id[:8]} "
        f"| {earned_marks}/{total_marks} ({pct}%) | rank #{rank}"
    )

    return {
        "success":      True,
        "earned_marks": float(earned_marks),
        "total_marks":  total_marks,
        "percentage":   pct,
        "correct":      correct,
        "wrong":        wrong,
        "rank":         rank,
    }


async def generate_summary_analytics(
    test_id: str,
    org_id: str,
) -> dict:
    """
    Calculate Highest, Lowest, Average scores for a test.
    Used by teacher/owner reports.

    Returns:
        {
          "test_name": str,
          "highest": {"student_name": str, "marks": float},
          "lowest":  {"student_name": str, "marks": float},
          "average": float,
          "total_attempts": int,
          "class_name": str,
        }
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Aggregate stats
        stats = await conn.fetchrow(
            """
            SELECT
                MAX(tr.marks)   AS highest_marks,
                MIN(tr.marks)   AS lowest_marks,
                ROUND(AVG(tr.marks), 2) AS avg_marks,
                COUNT(*)        AS attempts
            FROM test_results tr
            WHERE tr.test_id = $1 AND tr.org_id = $2
            """,
            test_id, org_id,
        )

        # Student names for highest / lowest
        highest_row = await conn.fetchrow(
            """
            SELECT s.name, tr.marks
            FROM test_results tr
            JOIN students s ON s.student_id = tr.student_id
            WHERE tr.test_id = $1 AND tr.org_id = $2
            ORDER BY tr.marks DESC LIMIT 1
            """,
            test_id, org_id,
        )
        lowest_row = await conn.fetchrow(
            """
            SELECT s.name, tr.marks
            FROM test_results tr
            JOIN students s ON s.student_id = tr.student_id
            WHERE tr.test_id = $1 AND tr.org_id = $2
            ORDER BY tr.marks ASC LIMIT 1
            """,
            test_id, org_id,
        )

        test_row = await conn.fetchrow(
            "SELECT test_name, class_name, total_marks FROM tests WHERE test_id = $1",
            test_id,
        )

    if not stats or not stats["attempts"]:
        return {"success": False, "message": "No results found for this test."}

    return {
        "success":        True,
        "test_name":      test_row["test_name"] if test_row else "—",
        "class_name":     test_row["class_name"] if test_row else "—",
        "total_marks":    test_row["total_marks"] if test_row else 0,
        "highest":        {"name": highest_row["name"], "marks": float(highest_row["marks"])} if highest_row else None,
        "lowest":         {"name": lowest_row["name"],  "marks": float(lowest_row["marks"])}  if lowest_row  else None,
        "average":        float(stats["avg_marks"] or 0),
        "total_attempts": stats["attempts"],
    }


async def process_offline_feed(
    org_id: str,
    test_id: str,
    teacher_id: str,
    marks_data: List[dict],   # [{"student_id": str, "marks": float}]
) -> dict:
    """
    Handles custom external test data ingestion (pen-paper tests).
    Teacher enters marks manually from bot; engine saves in bulk.

    Returns:
        {"success": bool, "saved": int, "failed": List[str]}
    """
    saved  = 0
    failed = []

    for entry in marks_data:
        student_id = entry.get("student_id", "").upper()
        marks_val  = entry.get("marks", 0)

        try:
            record = TestResult(
                org_id=org_id,
                test_id=test_id,
                student_id=student_id,
                marks=Decimal(str(marks_val)),
            )
            await _test_repo.save_result(record)
            saved += 1
        except Exception as e:
            logger.warning(f"Offline feed save failed for {student_id}: {e}")
            failed.append(student_id)

    await _audit.log(
        "OFFLINE_TEST_FEED",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={"test_id": test_id, "saved": saved, "failed": len(failed)},
    )

    return {
        "success": saved > 0,
        "saved":   saved,
        "failed":  failed,
        "message": f"✅ Marks saved for {saved} students." + (f"\n⚠️ Failed: {', '.join(failed)}" if failed else ""),
    }


async def get_upcoming_tests(org_id: str) -> List[dict]:
    """
    Called by scheduler test_reminder_job() at 6 PM.
    Finds tests scheduled for tomorrow.

    Returns list of {test_id, test_name, class_name, subject_name, topic}.
    """
    records = await _test_repo.get_tests_tomorrow(org_id)
    return records


# ── Helper ─────────────────────────────────────────────────

async def _get_rank(test_id: str, student_id: str, org_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rank = await conn.fetchval(
            """
            SELECT COUNT(*) + 1
            FROM test_results
            WHERE test_id = $1 AND org_id = $2
              AND marks > (
                SELECT marks FROM test_results
                WHERE test_id = $1 AND student_id = $3
              )
            """,
            test_id, org_id, student_id,
        )
    return rank or 1
