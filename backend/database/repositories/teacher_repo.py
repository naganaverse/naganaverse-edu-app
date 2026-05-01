"""
database/repositories/teacher_repo.py
Teacher CRUD — all queries scoped to org_id.
"""
import json
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.teacher_model import Teacher


class TeacherRepository:

    async def create(self, t: Teacher) -> Optional[Teacher]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO teachers
                        (org_id, teacher_id, name, subjects, assigned_classes, password_hash, phone)
                    VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6,$7)
                    RETURNING *
                    """,
                    t.org_id, t.teacher_id, t.name,
                    json.dumps(t.subjects), json.dumps(t.assigned_classes),
                    t.password_hash, t.phone,
                )
                return Teacher.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating teacher {t.teacher_id} in org {t.org_id}: {e}")
            return None

    async def get_by_teacher_id(self, teacher_id: str, org_id: str) -> Optional[Teacher]:
        """
        FIX: Uses UPPER()/LOWER() on both columns for case-blind matching.
        Prevents "ID Not Found" errors caused by casing mismatches between
        user input (always uppercased in handler) and DB storage.
        """
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM teachers
                    WHERE UPPER(teacher_id) = UPPER($1)
                      AND LOWER(org_id)     = LOWER($2)
                    """,
                    teacher_id, org_id,
                )
                return Teacher.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching teacher {teacher_id} for org {org_id}: {e}")
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Teacher]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM teachers WHERE telegram_id = $1", telegram_id
                )
                return Teacher.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching teacher by telegram_id {telegram_id}: {e}")
            return None

    async def get_all_by_org(self, org_id: str) -> List[Teacher]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM teachers WHERE org_id = $1 ORDER BY name", org_id
                )
                return [Teacher.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching all teachers for org {org_id}: {e}")
            return []

    async def bind_telegram_id(self, teacher_id: str, telegram_id: int, org_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE teachers SET telegram_id = $1 WHERE teacher_id = $2 AND org_id = $3",
                    telegram_id, teacher_id, org_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error binding telegram_id for teacher {teacher_id}: {e}")
            return False

    async def update_subjects_classes(
        self, teacher_id: str, org_id: str,
        subjects: List[str], assigned_classes: List[str]
    ) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE teachers
                    SET subjects = $3::jsonb, assigned_classes = $4::jsonb
                    WHERE teacher_id = $1 AND org_id = $2
                    """,
                    teacher_id, org_id,
                    json.dumps(subjects), json.dumps(assigned_classes),
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error updating subjects/classes for teacher {teacher_id}: {e}")
            return False

    async def delete(self, teacher_id: str, org_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM teachers WHERE teacher_id = $1 AND org_id = $2",
                    teacher_id, org_id,
                )
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"DB Error deleting teacher {teacher_id} in org {org_id}: {e}")
            return False

    async def count_by_org(self, org_id: str) -> int:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM teachers WHERE org_id = $1", org_id
                )
        except Exception as e:
            logger.error(f"DB Error counting teachers for org {org_id}: {e}")
            return 0
