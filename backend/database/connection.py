"""
database/connection.py
─────────────────────────────────────────────────────────────
asyncpg connection pool management.
Single pool shared across the entire application.

Usage anywhere:
    from database.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT ...")
─────────────────────────────────────────────────────────────
"""

import asyncio
import asyncpg
from typing import Optional
from loguru import logger

from config.config import settings

# Module-level pool singleton
_pool: Optional[asyncpg.Pool] = None


async def init_pool(retries: int = 3) -> asyncpg.Pool:
    """
    Create the asyncpg connection pool with retry logic for cold starts.
    """
    global _pool

    if _pool is not None:
        return _pool

    for attempt in range(retries):
        try:
            logger.info(f"Connecting to DB... (Attempt {attempt + 1}/{retries})")
            
            _pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=2,
                max_size=settings.DATABASE_POOL_SIZE,
                max_inactive_connection_lifetime=300.0,
                command_timeout=30.0,
                server_settings={
                    "application_name": "naganaverse_bot",
                    "timezone": "Asia/Kolkata",
                },
            )
            
            logger.info(f"✅ DB Connected. min=2 max={settings.DATABASE_POOL_SIZE}")
            return _pool
            
        except Exception as e:
            logger.error(f"DB connection failed (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)

    raise Exception("❌ Could not connect to database after multiple attempts")


async def get_pool() -> asyncpg.Pool:
    """
    Return the active pool.
    Auto-initialises if the pool was not ready (fixes Railway cold-start crashes).
    """
    global _pool
    
    if _pool is None:
        _pool = await init_pool()
        
    return _pool


async def close_pool() -> None:
    """Gracefully close all pool connections. Called at shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed.")


async def check_db_health() -> bool:
    """
    Verify database connectivity.
    Returns True if healthy, False otherwise.
    Called by the scheduler every 30 minutes.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
        
