"""
bot.py
─────────────────────────────────────────────────────────────
Naganaverse Education Bot — Application Entry Point

Startup sequence:
  1. Setup structured logging
  2. Initialise database (create tables if needed)
  3. Verify Redis connection
  4. Register all routers and middlewares onto Dispatcher
  5. Setup APScheduler (background jobs)
  6. Start Prometheus metrics server (if production)
  7. Start FastAPI Bridge concurrently with Bot polling

Run: python bot.py
─────────────────────────────────────────────────────────────
"""

import asyncio
import sys
import uvicorn

from loguru import logger

from config.config import settings
from core.loader import bot, dp, redis_client
from core.dispatcher import setup_dispatcher
from core.scheduler import setup_scheduler
from utils.logger import setup_logger
from database.connection import init_pool

# Import the FastAPI app
from api.main import app as fastapi_app


async def wait_for_db() -> None:
    """Block until the database is fully connected and responsive."""
    logger.info("Checking database readiness...")
    while True:
        try:
            pool = await init_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            logger.info("✅ Database is up and responsive.")
            break
        except Exception as e:
            logger.warning("Waiting for DB... retrying in 2s")
            await asyncio.sleep(2)


async def on_startup() -> None:
    """All pre-polling initialisation steps."""

    # 1. Logger
    setup_logger()
    logger.info("=" * 55)
    logger.info("  NAGANAVERSE EDUCATION BOT — STARTING UP")
    logger.info(f"  Environment : {settings.ENVIRONMENT.upper()}")
    logger.info(f"  Debug mode  : {settings.DEBUG}")
    logger.info("=" * 55)

    # 2. Database
    from database.init_db import initialise_tables
    await wait_for_db()
    await initialise_tables()
    logger.info("✅ Database tables initialised.")

    # 3. Redis
    try:
        await redis_client.ping()
        logger.info("✅ Redis connected.")
    except Exception as e:
        logger.critical(f"❌ Redis connection failed: {e}")
        sys.exit(1)

    # 4. Dispatcher (routers + middlewares)
    setup_dispatcher(dp)
    logger.info("✅ Dispatcher configured.")

    # 5. Bot info
    bot_info = await bot.get_me()
    logger.info(f"✅ Bot identity: @{bot_info.username} (id={bot_info.id})")

    # 6. Prometheus (production only)
    if settings.is_production:
        try:
            from prometheus_client import start_http_server
            start_http_server(settings.PROMETHEUS_PORT)
            logger.info(f"✅ Prometheus metrics on port {settings.PROMETHEUS_PORT}.")
        except Exception as e:
            logger.warning(f"Prometheus failed to start: {e}")


async def on_shutdown() -> None:
    """Graceful shutdown cleanup."""
    logger.info("Shutting down Naganaverse Bot...")
    await redis_client.aclose()
    await bot.session.close()
    from database.connection import close_pool
    await close_pool()
    logger.info("✅ Shutdown complete. Goodbye.")


async def start_api():
    """Runs the FastAPI server concurrently."""
    config = uvicorn.Config(
        app=fastapi_app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    # Startup
    await on_startup()

    # Scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("✅ Scheduler started.")

    logger.info("🚀 Starting Naganaverse Bot & FastAPI Bridge...")

    try:
        # Run Bot Polling AND FastAPI concurrently using asyncio.gather
        await asyncio.gather(
            dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True,  # Ignore queued updates from downtime
            ),
            start_api()
        )
    finally:
        scheduler.shutdown(wait=False)
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)
          
