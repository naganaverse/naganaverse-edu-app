"""
database/repositories/subscription_repo.py
"""
from typing import List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.subscription_model import Subscription


class SubscriptionRepository:

    async def create(self, s: Subscription) -> Optional[Subscription]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO subscriptions (org_id, plan, start_date, expiry_date, status)
                    VALUES ($1,$2,$3,$4,$5)
                    RETURNING *
                    """,
                    s.org_id, s.plan, s.start_date, s.expiry_date, s.status,
                )
                return Subscription.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating subscription for org {s.org_id}: {e}")
            return None

    async def get_by_org(self, org_id: str) -> Optional[Subscription]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM subscriptions WHERE org_id = $1 ORDER BY created_at DESC LIMIT 1",
                    org_id,
                )
                return Subscription.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching subscription for org {org_id}: {e}")
            return None

    async def get_expiring_soon(self, days: int = 3) -> List[dict]:
        """Used by scheduler for subscription alerts."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT s.org_id, s.plan, s.expiry_date, o.org_name,
                           ow.telegram_id as owner_telegram_id
                    FROM subscriptions s
                    JOIN organizations o ON o.org_id = s.org_id
                    LEFT JOIN owners ow ON ow.org_id = s.org_id
                    WHERE s.expiry_date <= CURRENT_DATE + $1
                      AND s.expiry_date >= CURRENT_DATE
                      AND s.status = 'active'
                    """,
                    days,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching expiring subscriptions: {e}")
            return []
            
