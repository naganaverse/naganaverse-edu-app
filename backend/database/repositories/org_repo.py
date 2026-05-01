"""
database/repositories/org_repo.py
Institution CRUD + approval/freeze/delete operations.
"""
import uuid
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.org_model import Organization


class OrgRepository:

    async def create(self, org: Organization) -> Optional[Organization]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO organizations
                        (org_id, org_name, owner_name, phone, city,
                         referral_code, referred_by, status, plan_type)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    RETURNING *
                    """,
                    org.org_id, org.org_name, org.owner_name, org.phone,
                    org.city, org.referral_code, org.referred_by,
                    org.status, org.plan_type,
                )
                return Organization.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating organization {org.org_name}: {e}")
            return None

    async def get_by_org_id(self, org_id: str) -> Optional[Organization]:
        """
        FIX: Uses LOWER() on both sides for case-blind matching.
        Prevents org lookup failures when org_id casing differs between
        the FSM state (always lowercased in handler) and DB storage.
        """
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM organizations WHERE LOWER(org_id) = LOWER($1)",
                    org_id,
                )
                return Organization.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching org_id {org_id}: {e}")
            return None

    async def get_pending(self) -> List[Organization]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM organizations WHERE status = 'pending' ORDER BY created_at ASC"
                )
                return [Organization.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching pending organizations: {e}")
            return []

    async def get_all_active(self) -> List[Organization]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM organizations WHERE status IN ('active','approved') ORDER BY org_name"
                )
                return [Organization.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching active organizations: {e}")
            return []

    async def search_by_name(self, name: str) -> List[Organization]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM organizations WHERE org_name ILIKE $1 ORDER BY org_name",
                    f"%{name}%",
                )
                return [Organization.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error searching organizations by name '{name}': {e}")
            return []

    async def update_status(self, org_id: str, status: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE organizations SET status = $1 WHERE org_id = $2",
                    status, org_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error updating status to '{status}' for org_id {org_id}: {e}")
            return False

    async def approve(self, org_id: str) -> bool:
        return await self.update_status(org_id, "active")

    async def reject(self, org_id: str) -> bool:
        return await self.update_status(org_id, "rejected")

    async def freeze(self, org_id: str) -> bool:
        return await self.update_status(org_id, "suspended")

    async def delete_cascade(self, org_id: str) -> bool:
        """
        Permanently delete institution and ALL related data.
        CASCADE foreign keys handle child table cleanup.
        Requires double confirmation from caller before invoking.
        """
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM organizations WHERE org_id = $1", org_id
                )
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"DB Error cascading delete for org_id {org_id}: {e}")
            return False

    async def update_profile(self, org_id: str, **fields) -> bool:
        allowed = {"org_name", "phone", "city"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False

        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
                values = list(updates.values())
                result = await conn.execute(
                    f"UPDATE organizations SET {set_clause} WHERE org_id = $1",
                    org_id, *values,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error updating profile for org_id {org_id}: {e}")
            return False

    async def count_all_active(self) -> int:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM organizations WHERE status IN ('active','approved')"
                )
        except Exception as e:
            logger.error(f"DB Error counting active organizations: {e}")
            return 0
