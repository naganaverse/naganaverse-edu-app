"""
database/repositories/homework_repo.py
"""
from datetime import date
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.homework_model import Homework


class HomeworkRepository:

    async def create(self, hw: Homework) -> Optional[Homework]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO homework
                        (org_id, class_name, subject_name, teacher_id, description, date)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    RETURNING *
                    """,
                    hw.org_id, hw.class_name, hw.subject_name,
                    hw.teacher_id, hw.description, hw.date,
                )
                return Homework.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating homework for org {hw.org_id}: {e}")
            return None

    async def get_today(self, org_id: str, class_name: str) -> List[Homework]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM homework
                    WHERE org_id = $1 AND class_name = $2 AND date = CURRENT_DATE
                    ORDER BY subject_name
                    """,
                    org_id, class_name,
                )
                return [Homework.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching today's homework for class {class_name} in org {org_id}: {e}")
            return []

    async def get_history(self, org_id: str, class_name: str, limit: int = 10) -> List[Homework]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM homework
                    WHERE org_id = $1 AND class_name = $2
                    ORDER BY date DESC LIMIT $3
                    """,
                    org_id, class_name, limit,
                )
                return [Homework.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching homework history for class {class_name} in org {org_id}: {e}")
            return []

    async def get_by_teacher(self, teacher_id: str, org_id: str, limit: int = 20) -> List[Homework]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM homework
                    WHERE teacher_id = $1 AND org_id = $2
                    ORDER BY date DESC LIMIT $3
                    """,
                    teacher_id, org_id, limit,
                )
                return [Homework.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching homework by teacher {teacher_id} in org {org_id}: {e}")
            return []

    async def get_classes_with_homework_today(self, org_id: str) -> List[dict]:
        """Used by scheduler for student homework reminders."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT class_name, subject_name, description
                    FROM homework
                    WHERE org_id = $1 AND date = CURRENT_DATE
                    """,
                    org_id,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching classes with homework today for org {org_id}: {e}")
            return []
            
