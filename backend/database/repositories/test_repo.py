"""
database/repositories/test_repo.py
Test creation, questions, attempts, results.
"""
from typing import List, Optional
from decimal import Decimal
from loguru import logger

from database.connection import get_pool
from database.models.test_model import Test, TestQuestion, TestResult


class TestRepository:

    async def create_test(self, t: Test) -> Optional[Test]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO tests
                        (org_id, test_name, class_name, subject_name, topic, teacher_id, test_date, total_marks)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                    RETURNING *
                    """,
                    t.org_id, t.test_name, t.class_name, t.subject_name,
                    t.topic, t.teacher_id, t.test_date, t.total_marks,
                )
                return Test.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating test {t.test_name} for org {t.org_id}: {e}")
            return None

    async def add_question(self, q: TestQuestion) -> Optional[TestQuestion]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO test_questions
                        (test_id, question_text, option_a, option_b, option_c, option_d, correct_answer, marks)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                    RETURNING *
                    """,
                    q.test_id, q.question_text,
                    q.option_a, q.option_b, q.option_c, q.option_d,
                    q.correct_answer, q.marks,
                )
                return TestQuestion.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error adding question to test {q.test_id}: {e}")
            return None

    async def get_test_by_id(self, test_id: str, org_id: str) -> Optional[Test]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM tests WHERE test_id = $1 AND org_id = $2",
                    test_id, org_id,
                )
                return Test.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching test {test_id} for org {org_id}: {e}")
            return None

    async def get_tests_by_class(self, org_id: str, class_name: str) -> List[Test]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM tests
                    WHERE org_id = $1 AND class_name = $2
                    ORDER BY test_date DESC
                    """,
                    org_id, class_name,
                )
                return [Test.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching tests for class {class_name} in org {org_id}: {e}")
            return []

    async def get_questions(self, test_id: str) -> List[TestQuestion]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM test_questions WHERE test_id = $1",
                    test_id,
                )
                return [TestQuestion.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching questions for test {test_id}: {e}")
            return []

    async def save_attempt(self, student_id: str, question_id: str, test_id: str, answer: str) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO test_attempts (student_id, question_id, test_id, answer)
                    VALUES ($1,$2,$3,$4)
                    ON CONFLICT (student_id, question_id) DO UPDATE SET answer = EXCLUDED.answer
                    """,
                    student_id, question_id, test_id, answer,
                )
        except Exception as e:
            logger.error(f"DB Error saving attempt for student {student_id} on question {question_id}: {e}")

    async def save_result(self, result: TestResult) -> Optional[TestResult]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO test_results (org_id, test_id, student_id, marks)
                    VALUES ($1,$2,$3,$4)
                    ON CONFLICT (test_id, student_id)
                    DO UPDATE SET marks = EXCLUDED.marks, submitted_at = NOW()
                    RETURNING *
                    """,
                    result.org_id, result.test_id, result.student_id, result.marks,
                )
                return TestResult.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error saving test result for student {result.student_id}: {e}")
            return None

    async def get_student_results(self, student_id: str, org_id: str) -> List[dict]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT tr.marks, t.test_name, t.subject_name, t.total_marks, tr.submitted_at
                    FROM test_results tr
                    JOIN tests t ON t.test_id = tr.test_id
                    WHERE tr.student_id = $1 AND tr.org_id = $2
                    ORDER BY tr.submitted_at DESC
                    """,
                    student_id, org_id,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching student results for {student_id} in org {org_id}: {e}")
            return []

    async def get_test_summary(self, test_id: str, org_id: str) -> dict:
        """Returns highest, lowest, average score for a test."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        MAX(tr.marks) AS highest,
                        MIN(tr.marks) AS lowest,
                        ROUND(AVG(tr.marks), 2) AS average,
                        COUNT(*) AS total_attempts,
                        s_high.name AS highest_student,
                        s_low.name  AS lowest_student
                    FROM test_results tr
                    LEFT JOIN students s_high ON s_high.student_id = (
                        SELECT student_id FROM test_results
                        WHERE test_id = $1 ORDER BY marks DESC LIMIT 1
                    )
                    LEFT JOIN students s_low ON s_low.student_id = (
                        SELECT student_id FROM test_results
                        WHERE test_id = $1 ORDER BY marks ASC LIMIT 1
                    )
                    WHERE tr.test_id = $1 AND tr.org_id = $2
                    """,
                    test_id, org_id,
                )
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"DB Error fetching test summary for {test_id} in org {org_id}: {e}")
            return {}

    async def get_by_teacher(self, teacher_id: str, org_id: str, limit: int = 20) -> List[Test]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM tests WHERE teacher_id = $1 AND org_id = $2
                    ORDER BY test_date DESC LIMIT $3
                    """,
                    teacher_id, org_id, limit,
                )
                return [Test.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching tests by teacher {teacher_id} in org {org_id}: {e}")
            return []

    async def get_tests_tomorrow(self, org_id: str) -> List[dict]:
        """Used by scheduler for test reminders."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT test_id, test_name, class_name, subject_name, topic
                    FROM tests
                    WHERE org_id = $1 AND test_date = CURRENT_DATE + 1
                    """,
                    org_id,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching tomorrow's tests for org {org_id}: {e}")
            return []
                
