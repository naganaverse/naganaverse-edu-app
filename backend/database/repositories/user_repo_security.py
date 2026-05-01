"""
database/repositories/user_repo_security.py
Login attempts, audit logs, suspended accounts, system settings.
"""
import json
from typing import Any, Dict, List, Optional
from loguru import logger

from database.connection import get_pool
from database.models.security_model import AuditLog, LoginAttempt, SuspendedAccount


class LoginAttemptRepository:

    async def log(self, attempt: LoginAttempt) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO login_attempts (user_id, role, org_id, ip_address, status)
                    VALUES ($1,$2,$3,$4,$5)
                    """,
                    attempt.user_id, attempt.role, attempt.org_id,
                    attempt.ip_address, attempt.status,
                )
        except Exception as e:
            logger.error(f"DB Error logging login attempt for {attempt.user_id}: {e}")

    async def get_recent(self, limit: int = 50) -> List[dict]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM login_attempts ORDER BY attempt_time DESC LIMIT $1",
                    limit,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching recent login attempts: {e}")
            return []

    async def get_failed_by_user(self, user_id: str, hours: int = 1) -> int:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                val = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM login_attempts
                    WHERE user_id = $1 AND status = 'failed'
                      AND attempt_time > NOW() - ($2 || ' hours')::INTERVAL
                    """,
                    user_id, str(hours),
                )
                return val if val is not None else 0
        except Exception as e:
            logger.error(f"DB Error fetching failed attempts for {user_id}: {e}")
            return 0

    async def log_attempt(
        self,
        user_id: str,
        role: str,
        org_id: str,
        status: str,
        ip_address: str = None,
    ) -> None:
        """
        Convenience method used by auth_service.
        Wraps .log() so callers don't need to build a LoginAttempt object.
        status: 'success' | 'failed'
        """
        attempt = LoginAttempt(
            user_id=user_id,
            role=role,
            org_id=org_id,
            ip_address=ip_address,
            status=status,
        )
        await self.log(attempt)


class AuditLogRepository:

    async def log(
        self,
        event_type: str,
        user_id: str = None,
        role: str = None,
        org_id: str = None,
        details: Dict[str, Any] = None,
    ) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_logs (event_type, user_id, role, org_id, details)
                    VALUES ($1,$2,$3,$4,$5::jsonb)
                    """,
                    event_type, user_id, role, org_id,
                    json.dumps(details) if details else None,
                )
        except Exception as e:
            logger.error(f"DB Error logging audit event {event_type} for org {org_id}: {e}")

    async def get_recent(self, org_id: str = None, limit: int = 50) -> List[dict]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                if org_id:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM audit_logs WHERE org_id = $1
                        ORDER BY timestamp DESC LIMIT $2
                        """,
                        org_id, limit,
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT $1",
                        limit,
                    )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching recent audit logs: {e}")
            return []


class SystemSettingsRepository:

    async def get(self, setting_name: str, org_id: str = None) -> Optional[str]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT setting_value FROM system_settings
                    WHERE setting_name = $1
                      AND (org_id = $2 OR (org_id IS NULL AND $2 IS NULL))
                    """,
                    setting_name, org_id,
                )
                return row["setting_value"] if row else None
        except Exception as e:
            logger.error(f"DB Error fetching system setting {setting_name}: {e}")
            return None

    async def set(self, setting_name: str, setting_value: str, org_id: str = None) -> None:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO system_settings (org_id, setting_name, setting_value)
                    VALUES ($1,$2,$3)
                    ON CONFLICT (org_id, setting_name)
                    DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = NOW()
                    """,
                    org_id, setting_name, setting_value,
                )
        except Exception as e:
            logger.error(f"DB Error setting system setting {setting_name}: {e}")

    async def get_maintenance_mode(self) -> bool:
        val = await self.get("maintenance_mode")
        return val == "true"

    async def get_registrations_paused(self) -> bool:
        val = await self.get("registrations_paused")
        return val == "true"

    async def pause_registrations(self) -> None:
        await self.set("registrations_paused", "true")

    async def resume_registrations(self) -> None:
        await self.set("registrations_paused", "false")

    async def enable_maintenance(self) -> None:
        await self.set("maintenance_mode", "true")

    async def disable_maintenance(self) -> None:
        await self.set("maintenance_mode", "false")
            
