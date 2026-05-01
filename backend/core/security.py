"""
core/security.py
─────────────────────────────────────────────────────────────
All cryptographic and authentication utilities:
  - Password hashing / verification (bcrypt)
  - JWT creation / decoding
  - Session management (Redis-backed JWT)
  - Brute-force protection (lockout logic)
─────────────────────────────────────────────────────────────
"""

import bcrypt
import jwt
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from loguru import logger

from config.config import settings
from core.loader import redis_client


# ── Password Hashing ──────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ── JWT Tokens ────────────────────────────────────────────

def create_access_token(payload: dict, expires_minutes: int = None) -> str:
    """
    Create a signed JWT token.
    payload should include at minimum: user_id, org_id, role.
    """
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    Returns payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


# ── Session Management (The Missing Logic) ────────────────

async def create_user_session(user_id: str, org_id: str, role: str, telegram_id: int = None) -> dict:
    """
    Creates a session payload. If telegram_id is provided, 
    persists it to Redis as a JWT to enable the 'Bouncer' Middleware.
    """
    payload = {
        "user_id": user_id,
        "org_id": org_id,
        "role": role,
        "name": "User" 
    }
    
    if telegram_id:
        token = create_access_token(payload)
        await save_session(telegram_id, token)
        logger.debug(f"Session persisted for tg={telegram_id}")
            
    return payload


async def save_session(telegram_id: int, token: str) -> None:
    """Persist session token in Redis."""
    key = session_key(telegram_id)
    await redis_client.setex(
        key,
        settings.JWT_EXPIRE_MINUTES * 60,
        token,
    )


async def get_session_token(telegram_id: int) -> Optional[str]:
    """Retrieve raw JWT token from Redis."""
    key = session_key(telegram_id)
    return await redis_client.get(key)


async def get_user_session(telegram_id: int) -> Optional[dict]:
    """
    Retrieve and validate a user's session payload.
    Used by AuthMiddleware to verify if the user is currently 'Active'.
    """
    token = await get_session_token(telegram_id)
    if not token:
        return None
    return decode_access_token(token)


async def delete_session(telegram_id: int) -> None:
    """Delete a session (logout)."""
    key = session_key(telegram_id)
    await redis_client.delete(key)
    logger.info(f"Session deleted for telegram_id={telegram_id}")


# ── Redis Keys & Brute-Force Protection ───────────────────

def session_key(telegram_id: int) -> str:
    return f"session:{telegram_id}"

def login_attempts_key(telegram_id: int) -> str:
    return f"login_attempts:{telegram_id}"

def lockout_key(telegram_id: int) -> str:
    return f"lockout:{telegram_id}"

async def is_locked_out(telegram_id: int) -> bool:
    key = lockout_key(telegram_id)
    result = await redis_client.get(key)
    return result is not None

async def record_failed_login(telegram_id: int) -> int:
    key = login_attempts_key(telegram_id)
    attempts = await redis_client.incr(key)
    if attempts == 1:
        await redis_client.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)
    if attempts >= settings.MAX_LOGIN_ATTEMPTS:
        await _apply_lockout(telegram_id)
    return attempts

async def _apply_lockout(telegram_id: int) -> None:
    key = lockout_key(telegram_id)
    await redis_client.setex(key, settings.LOGIN_LOCKOUT_MINUTES * 60, "locked")
    logger.warning(f"User {telegram_id} locked out.")

async def clear_login_attempts(telegram_id: int) -> None:
    await redis_client.delete(login_attempts_key(telegram_id))
    await redis_client.delete(lockout_key(telegram_id))
