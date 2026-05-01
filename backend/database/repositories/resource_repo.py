"""
database/repositories/resource_repo.py
"""
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.resource_model import Resource


class ResourceRepository:

    async def create(self, r: Resource) -> Optional[Resource]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO resources
                        (org_id, class_name, subject_name, resource_type, file_name, file_url, file_type, uploaded_by)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                    RETURNING *
                    """,
                    r.org_id, r.class_name, r.subject_name, r.resource_type,
                    r.file_name, r.file_url, r.file_type, r.uploaded_by,
                )
                return Resource.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating resource for org {r.org_id}: {e}")
            return None

    async def get_by_class_subject_type(
        self, org_id: str, class_name: str, subject_name: str, resource_type: str
    ) -> List[Resource]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM resources
                    WHERE org_id = $1 AND class_name = $2
                      AND subject_name = $3 AND resource_type = $4
                    ORDER BY created_at DESC
                    """,
                    org_id, class_name, subject_name, resource_type,
                )
                return [Resource.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching resources for org {org_id}: {e}")
            return []

    async def get_by_teacher(self, org_id: str, teacher_id: str) -> List[Resource]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM resources
                    WHERE org_id = $1 AND uploaded_by = $2
                    ORDER BY created_at DESC
                    """,
                    org_id, teacher_id,
                )
                return [Resource.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching resources by teacher {teacher_id} for org {org_id}: {e}")
            return []

    async def delete(self, resource_id: str, org_id: str, uploaded_by: str) -> bool:
        """Teachers can only delete their own uploads."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM resources WHERE resource_id = $1 AND org_id = $2 AND uploaded_by = $3",
                    resource_id, org_id, uploaded_by,
                )
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"DB Error deleting resource {resource_id} for org {org_id}: {e}")
            return False
            
