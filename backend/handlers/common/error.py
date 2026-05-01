"""
handlers/common/error.py
─────────────────────────────────────────────────────────────
Global error handler — catches ALL unhandled exceptions.

Handles:
  - Unexpected crashes in any handler
  - Telegram API errors (message too old to edit, etc.)
  - Database connection failures
  - Notifies super admins of critical errors in production
─────────────────────────────────────────────────────────────
"""

import traceback

from aiogram import Router
from aiogram.types import ErrorEvent, Update
from loguru import logger

from config.config import settings
from core.loader import bot
from keyboards.common_kb import nav_only_keyboard

router = Router()


@router.error()
async def global_error_handler(event: ErrorEvent) -> bool:
    """
    Catches all unhandled errors from any handler.
    Returns True to mark the error as handled.
    """
    exception = event.exception
    update: Update = event.update

    # Build traceback string
    tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

    logger.error(
        f"Unhandled exception in handler\n"
        f"Exception: {type(exception).__name__}: {exception}\n"
        f"Traceback:\n{tb}"
    )

    # Attempt to notify the user something went wrong
    telegram_id = _extract_telegram_id(update)
    if telegram_id:
        try:
            await bot.send_message(
                telegram_id,
                "⚠️ <b>Something went wrong.</b>\n\n"
                "An unexpected error occurred. Please try again.\n"
                "Tap 🏠 Home to return to your dashboard.",
                reply_markup=nav_only_keyboard(),
            )
        except Exception as send_err:
            logger.error(f"Failed to send error message to user {telegram_id}: {send_err}")

    # Notify super admins in production
    if settings.is_production:
        await _notify_super_admins(exception, tb, update)

    return True


async def _notify_super_admins(exception: Exception, tb: str, update: Update) -> None:
    """Send error report to all super admins."""
    short_tb = tb[-800:] if len(tb) > 800 else tb
    msg = (
        f"🚨 <b>Bot Error (Production)</b>\n\n"
        f"Type: <code>{type(exception).__name__}</code>\n"
        f"Message: <code>{str(exception)[:200]}</code>\n\n"
        f"<pre>{short_tb}</pre>"
    )

    for admin_id in settings.super_admin_id_list:
        try:
            await bot.send_message(admin_id, msg)
        except Exception as e:
            logger.error(f"Failed to notify super admin {admin_id} of error: {e}")


def _extract_telegram_id(update: Update) -> int | None:
    if update.message and update.message.from_user:
        return update.message.from_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    return None
