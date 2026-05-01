"""
services/superadmin_service.py
─────────────────────────────────────────────────────────────
Super Admin — Platform Control Service.

Access: Telegram ID whitelist ONLY (no password required).
        whitelist defined in settings.super_admin_id_list

Capabilities:
  - Approve / Reject / Freeze / Delete institutions
  - Freeze / Unfreeze / Unbind any user account
  - Platform analytics (system-wide)
  - Emergency controls (pause registrations, disable bot)
  - Broadcast to all owners / teachers / students
  - View login attempts + audit logs

Business Rules:
  - When approving institution: auto-generate org_id, activate owner
  - Delete institution: cascade wipe + "DELETE" confirmation required (at handler level)
  - All actions logged to audit_logs
─────────────────────────────────────────────────────────────
"""
import json
from notion_client import AsyncClient
import re
import uuid
from typing import List, Optional

from loguru import logger

from config.config import settings
from core.loader import bot
from database.connection import get_pool
from database.repositories.org_repo import OrgRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.teacher_repo import TeacherRepository
from database.repositories.user_repo import UserRepository
from database.repositories.subscription_repo import SubscriptionRepository
from database.repositories.user_repo_security import (
    AuditLogRepository,
    LoginAttemptRepository,
    SystemSettingsRepository,
)

_org_repo = OrgRepository()
_student_repo = StudentRepository()
_teacher_repo = TeacherRepository()
_user_repo = UserRepository()
_subscription_repo = SubscriptionRepository()
_audit = AuditLogRepository()
_login_log = LoginAttemptRepository()
_settings_repo = SystemSettingsRepository()


def is_super_admin(telegram_id: int) -> bool:
    """Hard whitelist check — used by filters."""
    return telegram_id in settings.super_admin_id_list


# ── Institution Management ────────────────────────────────

async def get_pending_institutions() -> List[dict]:
    orgs = await _org_repo.get_pending()
    return [
        {
            "org_id": o.org_id,
            "org_name": o.org_name,
            "owner_name": o.owner_name,
            "phone": o.phone,
            "city": o.city,
            "created_at": str(o.created_at),
        }
        for o in orgs
    ]


async def approve_institution(org_id: str, admin_telegram_id: int) -> dict:
    """
    Approve pending institution:
    1. Generate clean org_id slug if needed
    2. Set status = active
    3. Activate owner account
    """
    org = await _org_repo.get_by_org_id(org_id)
    if not org:
        return {"success": False, "message": "❌ Institution not found."}

    if org.status not in ("pending",):
        return {"success": False, "message": f"❌ Institution status is already '{org.status}'."}

    await _org_repo.approve(org_id)

    # Activate owner user account
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET status = 'active' WHERE org_id = $1 AND role = 'owner'",
            org_id,
        )

    await _audit.log(
        "INSTITUTION_APPROVED",
        user_id=f"superadmin_{admin_telegram_id}",
        role="super_admin",
        org_id=org_id,
        details={"org_name": org.org_name},
    )

    logger.info(f"Institution approved | org={org_id} | admin={admin_telegram_id}")

    return {
        "success": True,
        "message": f"✅ <b>{org.org_name}</b> has been approved and is now active.",
    }


async def reject_institution(org_id: str, reason: str, admin_telegram_id: int) -> dict:
    org = await _org_repo.get_by_org_id(org_id)
    if not org:
        return {"success": False, "message": "❌ Institution not found."}

    await _org_repo.reject(org_id)

    await _audit.log(
        "INSTITUTION_REJECTED",
        user_id=f"superadmin_{admin_telegram_id}",
        role="super_admin",
        org_id=org_id,
        details={"org_name": org.org_name, "reason": reason},
    )

    return {
        "success": True,
        "message": f"❌ <b>{org.org_name}</b> has been rejected.\nReason: {reason}",
    }


async def freeze_institution(org_id: str, admin_telegram_id: int) -> dict:
    org = await _org_repo.get_by_org_id(org_id)
    if not org:
        return {"success": False, "message": "❌ Institution not found."}

    await _org_repo.freeze(org_id)

    await _audit.log(
        "INSTITUTION_FROZEN",
        user_id=f"superadmin_{admin_telegram_id}",
        role="super_admin",
        org_id=org_id,
        details={"org_name": org.org_name},
    )

    return {
        "success": True,
        "message": f"❄️ <b>{org.org_name}</b> has been suspended. All logins blocked.",
    }

async def update_institution_status(org_id: str, new_status: str, admin_tg_id: int) -> dict:
    """Force updates an institution's status to a specific value."""
    from database.connection import get_pool
    from database.repositories.user_repo_security import AuditLogRepository
    
    _audit = AuditLogRepository()
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            # Update the organization status
            result = await conn.execute(
                "UPDATE organizations SET status = $1 WHERE org_id = $2",
                new_status, org_id
            )
            
            if result == "UPDATE 1":
                # If moving to active, we must also ensure the owner user is 'active'
                if new_status == 'active':
                    await conn.execute(
                        "UPDATE users SET status = 'active' WHERE org_id = $1 AND role = 'owner'",
                        org_id
                    )
                
                await _audit.log(
                    "INSTITUTION_STATUS_OVERRIDE", 
                    details={"org_id": org_id, "new_status": new_status, "admin": admin_tg_id}
                )
                return {"success": True, "message": f"✅ Status for {org_id} changed to {new_status}."}
            
            return {"success": False, "message": "❌ Institution not found."}
    except Exception as e:
        return {"success": False, "message": f"❌ DB Error: {e}"}
            

async def delete_institution(org_id: str, admin_telegram_id: int) -> dict:
    """
    PERMANENT cascade delete.
    Caller MUST have already received 'DELETE' confirmation from admin.
    """
    org = await _org_repo.get_by_org_id(org_id)
    if not org:
        return {"success": False, "message": "❌ Institution not found."}

    org_name = org.org_name
    deleted = await _org_repo.delete_cascade(org_id)

    await _audit.log(
        "INSTITUTION_DELETED",
        user_id=f"superadmin_{admin_telegram_id}",
        role="super_admin",
        details={"org_id": org_id, "org_name": org_name},
    )

    logger.warning(f"INSTITUTION DELETED | org={org_id} | admin={admin_telegram_id}")

    return {
        "success": deleted,
        "message": f"🗑 <b>{org_name}</b> has been permanently deleted.",
    }


# ── User Management ───────────────────────────────────────

async def _update_across_tables(user_id: str, sql_users: str, sql_students: str, sql_teachers: str) -> bool:
    """
    Apply an UPDATE to whichever table the user_id belongs to.
    Returns True if any table was updated.
    """
    pool = await get_pool()
    uid = user_id.upper()
    async with pool.acquire() as conn:
        # Try users table (owners)
        r = await conn.execute(sql_users, uid)
        if r == "UPDATE 1":
            return True
        # Try students table
        r = await conn.execute(sql_students, uid)
        if r == "UPDATE 1":
            return True
        # Try teachers table
        r = await conn.execute(sql_teachers, uid)
        if r == "UPDATE 1":
            return True
    return False


async def freeze_user(user_id: str, admin_telegram_id: int) -> dict:
    result = await _update_across_tables(
        user_id,
        "UPDATE users    SET status = 'frozen' WHERE user_id     = $1",
        "UPDATE students SET account_status = 'frozen' WHERE student_id = $1",
        "UPDATE teachers SET account_status = 'frozen' WHERE teacher_id = $1",
    )
    if result:
        await _audit.log("USER_FROZEN", user_id=f"superadmin_{admin_telegram_id}",
                         role="super_admin", details={"target_user": user_id})
    return {
        "success": result,
        "message": f"🚫 User <b>{user_id}</b> frozen." if result else "❌ User not found.",
    }


async def unfreeze_user(user_id: str, admin_telegram_id: int) -> dict:
    result = await _update_across_tables(
        user_id,
        "UPDATE users    SET status = 'active' WHERE user_id     = $1",
        "UPDATE students SET account_status = 'active' WHERE student_id = $1",
        "UPDATE teachers SET account_status = 'active' WHERE teacher_id = $1",
    )
    if result:
        await _audit.log("USER_UNFROZEN", user_id=f"superadmin_{admin_telegram_id}",
                         role="super_admin", details={"target_user": user_id})
    return {
        "success": result,
        "message": f"✅ User <b>{user_id}</b> unfrozen." if result else "❌ User not found.",
    }


async def unbind_telegram(user_id: str, admin_telegram_id: int) -> dict:
    """Fix login issues — student/teacher changed phone."""
    result = await _update_across_tables(
        user_id,
        "UPDATE users    SET telegram_id = NULL WHERE user_id     = $1",
        "UPDATE students SET telegram_id = NULL WHERE student_id = $1",
        "UPDATE teachers SET telegram_id = NULL WHERE teacher_id = $1",
    )
    if result:
        await _audit.log("TELEGRAM_UNBOUND", user_id=f"superadmin_{admin_telegram_id}",
                         role="super_admin", details={"target_user": user_id})
    return {
        "success": result,
        "message": (
            f"🔗 Telegram ID unbound for <b>{user_id}</b>.\n"
            "User can now login again from a new device."
        ) if result else "❌ User not found.",
    }


# ── Platform Analytics ────────────────────────────────────

async def get_platform_analytics() -> str:
    pool = await get_pool()

    async with pool.acquire() as conn:
        total_orgs = await conn.fetchval(
            "SELECT COUNT(*) FROM organizations WHERE status IN ('active','approved')"
        )
        total_students = await conn.fetchval("SELECT COUNT(*) FROM students")
        total_teachers = await conn.fetchval("SELECT COUNT(*) FROM teachers")
        total_pending = await conn.fetchval(
            "SELECT COUNT(*) FROM organizations WHERE status = 'pending'"
        )
        today_logins = await conn.fetchval(
            "SELECT COUNT(*) FROM login_attempts WHERE status = 'success' AND attempt_time::date = CURRENT_DATE"
        )

    return (
        f"📊 <b>Naganaverse Platform Analytics</b>\n\n"
        f"🏫 Active Institutions: <b>{total_orgs}</b>\n"
        f"⏳ Pending Approvals: <b>{total_pending}</b>\n"
        f"👥 Total Students: <b>{total_students}</b>\n"
        f"👨‍🏫 Total Teachers: <b>{total_teachers}</b>\n"
        f"🔐 Logins Today: <b>{today_logins}</b>"
    )


# ── Emergency Controls ────────────────────────────────────

async def pause_registrations(admin_telegram_id: int) -> str:
    await _settings_repo.pause_registrations()
    await _audit.log("REGISTRATIONS_PAUSED", user_id=f"superadmin_{admin_telegram_id}",
                     role="super_admin")
    return "⏸ New institution registrations have been <b>paused</b>."


async def resume_registrations(admin_telegram_id: int) -> str:
    await _settings_repo.resume_registrations()
    await _audit.log("REGISTRATIONS_RESUMED", user_id=f"superadmin_{admin_telegram_id}",
                     role="super_admin")
    return "▶️ New institution registrations have been <b>resumed</b>."


async def enable_maintenance_mode(admin_telegram_id: int) -> str:
    await _settings_repo.enable_maintenance()
    await _audit.log("MAINTENANCE_MODE_ENABLED", user_id=f"superadmin_{admin_telegram_id}",
                     role="super_admin")
    return "🔧 <b>Maintenance mode enabled.</b> Bot is now restricted."


async def disable_maintenance_mode(admin_telegram_id: int) -> str:
    await _settings_repo.disable_maintenance()
    await _audit.log("MAINTENANCE_MODE_DISABLED", user_id=f"superadmin_{admin_telegram_id}",
                     role="super_admin")
    return "✅ <b>Maintenance mode disabled.</b> Bot is fully operational."



async def push_to_notion(payload_json: str, admin_telegram_id: int) -> dict:
    """Parses JSON from Gemini and pushes it to the Notion Database."""
    try:
        # 1. Parse the JSON sent by Gemini
        data = json.loads(payload_json)
        topic = data.get("topic", "Untitled Concept")
        folder = data.get("folder", "Inbox")
        prompt = data.get("prompt", "")
        content = data.get("content", "")

        # 2. Initialize Async Notion Client
        notion = AsyncClient(auth=settings.NOTION_TOKEN)

        # 3. Create the Page in the Database
        await notion.pages.create(
            parent={"database_id": settings.NOTION_DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": topic}}]},
                "Folder": {"select": {"name": folder}},
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": f"AI Prompt: {prompt}"}}]}
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]}
                }
            ]
        )

        # 4. Log it in your existing Audit system
        await _audit.log(
            "NOTION_SYNC_SUCCESS", 
            user_id=f"superadmin_{admin_telegram_id}", 
            role="super_admin",
            details={"topic": topic}
        )
        
        return {"success": True, "message": f"✅ Successfully synced <b>{topic}</b> to Notion!"}

    except json.JSONDecodeError:
        return {"success": False, "message": "❌ Invalid JSON format. Please copy the block exactly."}
    except Exception as e:
        logger.error(f"Notion sync failed: {e}")
        return {"success": False, "message": f"❌ Failed to sync: {str(e)}"}
            
# ── Broadcast ─────────────────────────────────────────────

async def broadcast_to_all_owners(message: str, admin_telegram_id: int) -> dict:
    """Send platform message to all active institution owners."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT o.telegram_id FROM owners o
            JOIN organizations org ON org.org_id = o.org_id
            WHERE org.status IN ('active','approved') AND o.telegram_id IS NOT NULL
            """
        )

    telegram_ids = [r["telegram_id"] for r in rows]
    sent = await _broadcast(telegram_ids, message)

    await _audit.log(
        "BROADCAST_OWNERS",
        user_id=f"superadmin_{admin_telegram_id}",
        role="super_admin",
        details={"sent": sent, "total": len(telegram_ids)},
    )

    return {
        "success": True,
        "sent": sent,
        "message": f"📢 Broadcast sent to {sent}/{len(telegram_ids)} owners.",
    }


async def _broadcast(telegram_ids: List[int], message: str) -> int:
    """Broadcast a message to a list of Telegram IDs."""
    sent = 0
    for tg_id in telegram_ids:
        try:
            await bot.send_message(tg_id, message, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for tg={tg_id}: {e}")
    return sent
