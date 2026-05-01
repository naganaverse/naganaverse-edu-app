"""
database/repositories/notification_repo.py
Parent notification logging.
"""
from typing import List
from loguru import logger

from database.connection import get_pool
from database.models.notification_model import ParentNotification


class NotificationRepository:

    async def log(self, n: ParentNotification) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO parent_notifications
                        (org_id, student_id, parent_phone, notification_type, message)
                    VALUES ($1,$2,$3,$4,$5)
                    """,
                    n.org_id, n.student_id, n.parent_phone,
                    n.notification_type, n.message,
                )
        except Exception as e:
            logger.error(f"DB Error logging notification for student {n.student_id} in org {n.org_id}: {e}")

    async def get_by_student(self, student_id: str, org_id: str, limit: int = 20) -> List[dict]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM parent_notifications
                    WHERE student_id = $1 AND org_id = $2
                    ORDER BY sent_at DESC LIMIT $3
                    """,
                    student_id, org_id, limit,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching notifications for student {student_id} in org {org_id}: {e}")
            return []
            
