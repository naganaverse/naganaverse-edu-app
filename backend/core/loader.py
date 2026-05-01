"""
core/loader.py
─────────────────────────────────────────────────────────────
Single source of truth for bot, dispatcher, and redis instances.
All other modules import from here — never re-create these objects.
─────────────────────────────────────────────────────────────
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config.config import settings

# ── Redis client ──────────────────────────────────────────
redis_client: Redis = Redis.from_url(
    settings.REDIS_URL,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True,
    encoding="utf-8",
)

# ── FSM Storage (Redis-backed) ────────────────────────────
storage = RedisStorage(redis=redis_client)

# ── Bot instance ──────────────────────────────────────────
bot: Bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# ── Dispatcher ────────────────────────────────────────────
dp: Dispatcher = Dispatcher(storage=storage)
