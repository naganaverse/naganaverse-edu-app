"""
utils/logger.py
─────────────────────────────────────────────────────────────
Structured logging setup using Loguru.
Call setup_logger() once at startup from bot.py.
─────────────────────────────────────────────────────────────
"""

import sys
import os
from loguru import logger

from config.config import settings


def setup_logger() -> None:
    """Configure Loguru with console and rotating file output."""

    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # Rotating file handler
    os.makedirs("logs", exist_ok=True)
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} — {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=settings.DEBUG,
        enqueue=True,
    )

    logger.info("Logger initialised.")
