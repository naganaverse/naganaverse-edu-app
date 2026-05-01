"""
database/repositories/student_repo.py
Student CRUD — all queries scoped to org_id.
"""
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.student_model import Student


class StudentRepository:

    async def create(self, s: Student) -> Optional[Student]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                import json
                row = await conn.fetchrow(
                    """
                    INSERT INTO students
                        (org_id, student_id, name, class, roll_number, subjects,
                         father_name, mother_name, parent_phone, password_hash,
                         agreed_fee, current_due)
                    VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11,$12)
                    RETURNING *
                    """,
                    s.org_id, s.student_id, s.name, s.class_name, s.roll_number,
                    json.dumps(s.subjects), s.father_name, s.mother_name,
                    s.parent_phone, s.password_hash, s.agreed_fee, s.current_due,
                )
                return Student.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating student {s.student_id} in org {s.org_id}: {e}")
            return None

    async def get_by_student_id(self, student_id: str, org_id: str) -> Optional[Student]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM students
                    WHERE UPPER(student_id) = UPPER($1)
                      AND LOWER(org_id)     = LOWER($2)
                    """,
                    student_id, org_id,
                )
                return Student.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching student {student_id} for org {org_id}: {e}")
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Student]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM students WHERE telegram_id = $1", telegram_id
                )
                return Student.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching student by telegram_id {telegram_id}: {e}")
            return None

    async def get_student_profile(self, telegram_id: int) -> dict | None:
        """Fetches detailed student profile for the Mini App dashboard."""
        query = """
            SELECT name, class, subjects, roll_number, org_id
            FROM students
            WHERE telegram_id = $1 AND account_status = 'active'
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            record = await conn.fetchrow(query, telegram_id)
            return dict(record) if record else None

    async def get_by_class(self, org_id: str, class_name: str) -> List[Student]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM students WHERE org_id = $1 AND class = $2 ORDER BY roll_number",
                    org_id, class_name,
                )
                return [Student.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching students for class {class_name} in org {org_id}: {e}")
            return []

    async def get_all_by_org(self, org_id: str) -> List[Student]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM students WHERE org_id = $1 ORDER BY class, roll_number",
                    org_id,
                )
                return [Student.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching all students for org {org_id}: {e}")
            return []

    async def bind_telegram_id(self, student_id: str, telegram_id: int, org_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE students SET telegram_id = $1 WHERE student_id = $2 AND org_id = $3",
                    telegram_id, student_id, org_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error binding telegram_id for student {student_id}: {e}")
            return False

    async def update(self, student_id: str, org_id: str, **fields) -> bool:
        allowed = {"name", "class", "roll_number", "father_name", "mother_name", "parent_phone"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False

        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                set_clause = ", ".join(f"{k} = ${i+3}" for i, k in enumerate(updates))
                result = await conn.execute(
                    f"UPDATE students SET {set_clause} WHERE student_id = $1 AND org_id = $2",
                    student_id, org_id, *updates.values(),
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error updating student {student_id} in org {org_id}: {e}")
            return False

    async def delete(self, student_id: str, org_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM students WHERE student_id = $1 AND org_id = $2",
                    student_id, org_id,
                )
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"DB Error deleting student {student_id} in org {org_id}: {e}")
            return False

    async def count_by_org(self, org_id: str) -> int:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM students WHERE org_id = $1", org_id
                )
        except Exception as e:
            logger.error(f"DB Error counting students for org {org_id}: {e}")
            return 0

    async def get_parent_phones_by_class(self, org_id: str, class_name: str) -> List[dict]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT student_id, name, parent_phone
                    FROM students
                    WHERE org_id = $1 AND class = $2 AND parent_phone IS NOT NULL
                    """,
                    org_id, class_name,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching parent phones for class {class_name} in org {org_id}: {e}")
            return []
                
