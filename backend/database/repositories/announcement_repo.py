"""
database/repositories/announcement_repo.py
"""
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.announcement_model import Announcement


class AnnouncementRepository:

    async def create(self, a: Announcement) -> Optional[Announcement]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO announcements (org_id, target_class, message, created_by)
                    VALUES ($1,$2,$3,$4)
                    RETURNING *
                    """,
                    a.org_id, a.target_class, a.message, a.created_by,
                )
                return Announcement.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating announcement for org {a.org_id}: {e}")
            return None

    async def get_recent(self, org_id: str, class_name: str = None, limit: int = 10) -> List[Announcement]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                if class_name:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM announcements
                        WHERE org_id = $1 AND (target_class = $2 OR target_class IS NULL)
                        ORDER BY created_at DESC LIMIT $3
                        """,
                        org_id, class_name, limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM announcements
                        WHERE org_id = $1
                        ORDER BY created_at DESC LIMIT $2
                        """,
                        org_id, limit,
                    )
                return [Announcement.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching recent announcements for org {org_id}: {e}")
            return []

    async def get_target_telegram_ids(self, org_id: str, class_name: str = None) -> List[int]:
        """Get all telegram_ids to broadcast announcement to."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                if class_name:
                    rows = await conn.fetch(
                        """
                        SELECT telegram_id FROM students
                        WHERE org_id = $1 AND class = $2 AND telegram_id IS NOT NULL
                        """,
                        org_id, class_name,
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT telegram_id FROM students WHERE org_id = $1 AND telegram_id IS NOT NULL",
                        org_id,
                    )
                return [r["telegram_id"] for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching target telegram IDs for org {org_id}: {e}")
            return []
                
