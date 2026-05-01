"""
core/middlewares/rate_limit_middleware.py
─────────────────────────────────────────────────────────────
Rate limiting middleware — runs FIRST on every update.

Strategy: Sliding window counter in Redis.
  - Max 10 commands per minute per Telegram user (from config).
  - Exceeding the limit silently drops the update and warns the user.
  - Super admins bypass rate limiting entirely.

Redis key format:  ratelimit:{telegram_id}
─────────────────────────────────────────────────────────────
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger

from config.config import settings
from core.loader import redis_client


# How many seconds to wait before warning the user again
_WARN_COOLDOWN_SECONDS = 30
_WARN_KEY_PREFIX = "ratelimit_warned:"


class RateLimitMiddleware(BaseMiddleware):
    """
    Sliding window rate limiter.
    10 requests per 60 seconds per user (configurable via .env).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        telegram_id = self._extract_telegram_id(event)

        if telegram_id is None:
            # Cannot identify user — allow through
            return await handler(event, data)

        # Super admins bypass rate limiting
        if telegram_id in settings.super_admin_id_list:
            return await handler(event, data)

        # Check and increment rate limit counter
        is_limited = await self._check_rate_limit(telegram_id)

        if is_limited:
            await self._send_warning(event, telegram_id)
            return  # Drop the update — do NOT call handler

        return await handler(event, data)

    async def _check_rate_limit(self, telegram_id: int) -> bool:
        """
        Increment request counter. Returns True if rate limit exceeded.
        Uses INCR + EXPIRE for atomic sliding window.
        """
        key = f"ratelimit:{telegram_id}"
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
        results = await pipe.execute()
        count = results[0]

        if count > settings.RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded | tg={telegram_id} | count={count}")
            return True

        return False

    async def _send_warning(self, event: TelegramObject, telegram_id: int) -> None:
        """
        Warn the user once per cooldown window.
        Avoids spamming them with warning messages.
        """
        warn_key = f"{_WARN_KEY_PREFIX}{telegram_id}"
        already_warned = await redis_client.get(warn_key)

        if already_warned:
            return

        # Mark as warned
        await redis_client.setex(warn_key, _WARN_COOLDOWN_SECONDS, "1")

        # Send warning message
        update: Update = event
        try:
            text = (
                "⚠️ <b>Slow down!</b>\n\n"
                f"You're sending commands too fast.\n"
                f"Limit: <b>{settings.RATE_LIMIT_MAX_REQUESTS} requests "
                f"per {settings.RATE_LIMIT_WINDOW_SECONDS} seconds.</b>\n\n"
                "Please wait a moment before continuing."
            )

            if update.message:
                await update.message.answer(text)
            elif update.callback_query:
                await update.callback_query.answer(
                    "⚠️ Too many requests. Please slow down.", show_alert=True
                )
        except Exception as e:
            logger.error(f"Failed to send rate limit warning to {telegram_id}: {e}")

    @staticmethod
    def _extract_telegram_id(event: TelegramObject) -> int | None:
        """Extract Telegram user ID from any update type."""
        update: Update = event

        if update.message and update.message.from_user:
            return update.message.from_user.id
        if update.callback_query and update.callback_query.from_user:
            return update.callback_query.from_user.id
        if update.inline_query and update.inline_query.from_user:
            return update.inline_query.from_user.id
        if update.edited_message and update.edited_message.from_user:
            return update.edited_message.from_user.id

        return None
