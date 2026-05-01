"""
database/repositories/user_repo.py
Central user authentication repository.
"""
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from database.connection import get_pool
from database.models.user_model import User


class UserRepository:

    async def get_by_user_id(self, user_id: str, org_id: str) -> Optional[User]:
        """
        Fetches user by ID within a specific organization.

        FIX: Accepts org_id as a required second argument.
        Uses UPPER()/LOWER() on both columns and both parameters for
        fully case-blind matching — prevents login failures caused by
        casing mismatches between FSM input and DB storage.
        """
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM users
                    WHERE UPPER(user_id) = UPPER($1)
                      AND LOWER(org_id)  = LOWER($2)
                    """,
                    user_id, org_id,
                )
                return User.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching user {user_id} in org {org_id}: {e}")
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE telegram_id = $1", telegram_id
                )
                return User.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching user by telegram_id {telegram_id}: {e}")
            return None

    @staticmethod
    async def get_tma_auth_profile(telegram_id: int) -> dict | None:
        """
        Fetches the complete user profile and institute tier required 
        for Telegram Mini App (TMA) Authentication.
        """
        try:
            query = """
                SELECT u.user_id, u.org_id, u.role, u.status, u.name, 
                       o.org_name, o.plan_type 
                FROM users u
                JOIN organizations o ON u.org_id = o.org_id
                WHERE u.telegram_id = $1 AND u.status = 'active' AND o.status = 'active'
            """
            pool = await get_pool()
            async with pool.acquire() as conn:
                record = await conn.fetchrow(query, telegram_id)
                return dict(record) if record else None
        except Exception as e:
            logger.error(f"DB Error fetching TMA auth profile for telegram_id {telegram_id}: {e}")
            return None

    async def bind_telegram_id(self, user_id: str, telegram_id: int) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET telegram_id = $1 WHERE user_id = $2",
                    telegram_id, user_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error binding telegram_id for user {user_id}: {e}")
            return False

    async def unbind_telegram_id(self, user_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET telegram_id = NULL WHERE user_id = $1",
                    user_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error unbinding telegram_id for user {user_id}: {e}")
            return False

    async def increment_failed_attempts(self, user_id: str) -> int:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    UPDATE users
                    SET failed_attempts = failed_attempts + 1,
                        last_failed_attempt = NOW()
                    WHERE user_id = $1
                    RETURNING failed_attempts
                    """,
                    user_id,
                )
                return row["failed_attempts"] if row else 0
        except Exception as e:
            logger.error(f"DB Error incrementing failed attempts for {user_id}: {e}")
            return 0

    async def lock_account(self, user_id: str, until: datetime) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE users
                    SET account_locked_until = $1, status = 'locked'
                    WHERE user_id = $2
                    """,
                    until, user_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error locking account for {user_id}: {e}")
            return False

    async def clear_failed_attempts(self, user_id: str) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE users
                    SET failed_attempts = 0,
                        last_failed_attempt = NULL,
                        account_locked_until = NULL,
                        status = 'active'
                    WHERE user_id = $1
                    """,
                    user_id,
                )
        except Exception as e:
            logger.error(f"DB Error clearing failed attempts for {user_id}: {e}")

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET password_hash = $1 WHERE user_id = $2",
                    password_hash, user_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error updating password for {user_id}: {e}")
            return False

    async def freeze_account(self, user_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET status = 'frozen' WHERE user_id = $1",
                    user_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error freezing account for {user_id}: {e}")
            return False

    async def unfreeze_account(self, user_id: str) -> bool:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET status = 'active' WHERE user_id = $1",
                    user_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error unfreezing account for {user_id}: {e}")
            return False

    async def logout(self, telegram_id: int) -> bool:
        """Set telegram_id = NULL on logout."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET telegram_id = NULL WHERE telegram_id = $1",
                    telegram_id,
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"DB Error logging out telegram_id {telegram_id}: {e}")
            return False
            
