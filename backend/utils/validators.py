"""
utils/validators.py
─────────────────────────────────────────────────────────────
All validation and protection logic across the security layer.

Functions:
  check_rate_limit()        — 10 commands/minute per user
  validate_abuse_patterns() — 30 commands/30s → 30min auto-block
  check_login_attempts()    — 5 failures → 30min lockout
  validate_platform_limits()— org-level capacity limits
  validate_phone/user_id/text/roll/marks/date — input sanitisation
─────────────────────────────────────────────────────────────
"""

import re
from typing import Tuple

from loguru import logger

from config.config import settings
from core.loader import redis_client
from database.repositories.user_repo_security import AuditLogRepository

_audit = AuditLogRepository()


async def check_rate_limit(user_id) -> Tuple[bool, str]:
    """Max 10 commands/minute. Returns (is_limited, message)."""
    key     = f"ratelimit:{user_id}"
    pipe    = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
    results = await pipe.execute()
    count   = results[0]

    if count > settings.RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded | user={user_id} | count={count}")
        return True, (
            f"⚠️ Too many requests. Limit: {settings.RATE_LIMIT_MAX_REQUESTS} "
            f"per {settings.RATE_LIMIT_WINDOW_SECONDS}s. Please wait."
        )
    return False, ""


async def validate_abuse_patterns(user_id) -> Tuple[bool, str]:
    """30 commands/30s → 30min auto-block. Returns (is_abusive, message)."""
    block_key = f"abuse_block:{user_id}"
    if await redis_client.get(block_key):
        ttl = await redis_client.ttl(block_key)
        return True, f"🚫 Temporarily blocked. Auto-unblock in {ttl//60}m {ttl%60}s."

    abuse_key  = f"abuse_count:{user_id}"
    pipe       = redis_client.pipeline()
    pipe.incr(abuse_key)
    pipe.expire(abuse_key, 30)
    count      = (await pipe.execute())[0]

    if count >= 30:
        await redis_client.setex(block_key, 1800, "1")
        await redis_client.delete(abuse_key)
        logger.warning(f"ABUSE DETECTED | user={user_id} | {count} commands/30s")
        await _audit.log("BOT_ABUSE_DETECTED", user_id=str(user_id),
                         details={"commands": count, "action": "BLOCKED_30_MIN"})
        await _alert_admins_abuse(str(user_id), count)
        return True, "🚫 Suspicious activity detected. Blocked for 30 minutes."

    return False, ""


async def _alert_admins_abuse(user_id: str, count: int) -> None:
    from core.loader import bot
    msg = (f"🚨 <b>Bot Abuse</b>\n👤 {user_id}\n⚡ {count} commands/30s\n🔒 Blocked 30 min")
    for admin_id in settings.super_admin_id_list:
        try:
            await bot.send_message(admin_id, msg)
        except Exception:
            pass


async def check_login_attempts(telegram_id: int) -> Tuple[bool, str, int]:
    """Returns (is_locked, message, attempts_remaining)."""
    from core.security import is_locked_out
    if await is_locked_out(telegram_id):
        ttl = await redis_client.ttl(f"lockout:{telegram_id}")
        return True, f"🔒 Locked. Try in {ttl//60}m {ttl%60}s.", 0

    count = await redis_client.get(f"login_attempts:{telegram_id}")
    count = int(count) if count else 0
    remaining = max(0, settings.MAX_LOGIN_ATTEMPTS - count)
    return False, "", remaining


async def validate_platform_limits(org_id: str, resource_type: str) -> Tuple[bool, str]:
    """Check org capacity. Returns (limit_reached, message)."""
    from database.connection import get_pool
    pool = await get_pool()

    LIMITS = {
        "student": (1000, "SELECT COUNT(*) FROM students WHERE org_id = $1"),
        "teacher": (50,   "SELECT COUNT(*) FROM teachers WHERE org_id = $1"),
        "file":    (100,  "SELECT COUNT(*) FROM resources WHERE org_id = $1 AND created_at::date = CURRENT_DATE"),
    }
    if resource_type not in LIMITS:
        return False, ""

    max_count, query = LIMITS[resource_type]
    async with pool.acquire() as conn:
        current = await conn.fetchval(query, org_id)

    if current >= max_count:
        return True, f"❌ {resource_type.title()} limit reached (max {max_count}). Contact Naganaverse support."
    return False, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    cleaned = re.sub(r"[\s\-\+\(\)]", "", phone)
    if not cleaned.isdigit() or not (10 <= len(cleaned) <= 15):
        return False, "Invalid phone number."
    return True, cleaned


def validate_user_id(user_id: str, prefix: str = None) -> Tuple[bool, str]:
    cleaned = user_id.strip().upper()
    if len(cleaned) < 3 or len(cleaned) > 20:
        return False, "ID must be 3–20 characters."
    if not re.match(r"^[A-Z0-9_-]+$", cleaned):
        return False, "ID can only contain letters, numbers, underscores, hyphens."
    if prefix and not cleaned.startswith(prefix):
        return False, f"ID must start with {prefix} (e.g. {prefix}001)."
    return True, cleaned


def validate_text_input(text: str, min_len: int = 2, max_len: int = 500) -> Tuple[bool, str]:
    cleaned = text.strip()
    if len(cleaned) < min_len:
        return False, f"Too short. Min {min_len} characters."
    if len(cleaned) > max_len:
        return False, f"Too long. Max {max_len} characters."
    return True, cleaned


def validate_roll_number(roll: str) -> Tuple[bool, int]:
    if not roll.strip().isdigit():
        return False, 0
    num = int(roll.strip())
    return (1 <= num <= 9999, num)


def validate_marks(marks_str: str, total_marks: int) -> Tuple[bool, float]:
    try:
        marks = float(marks_str.strip())
        return (0 <= marks <= total_marks, marks)
    except ValueError:
        return False, 0.0


def validate_date_format(date_str: str) -> Tuple[bool, str]:
    from datetime import datetime
    try:
        parsed = datetime.strptime(date_str.strip(), "%d-%m-%Y")
        return True, str(parsed.date())
    except ValueError:
        return False, "Use DD-MM-YYYY format."
