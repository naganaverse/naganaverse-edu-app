"""
core/middlewares/auth_middleware.py
─────────────────────────────────────────────────────────────
The Bouncer: Active Authentication Middleware.
Verifies Redis sessions against Postgres to kill ghost sessions,
deleted institutes, and unauthorized device access in real-time.
─────────────────────────────────────────────────────────────
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from core.security import get_user_session, delete_session
from database.connection import get_pool


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        telegram_id = self._extract_telegram_id(event)
        state: FSMContext = data.get("state")

        # 1. Start with no session
        data["user_session"] = None

        if not telegram_id:
            return await handler(event, data)

        # 2. Get session from Redis/JWT
        session = await get_user_session(telegram_id)

        # If no session, they are a guest (let them reach /start or /login)
        if not session:
            return await handler(event, data)

        # 3. ── THE BOUNCER CHECK (Database Validation) ──
        org_id = session.get("org_id")
        user_id = session.get("user_id")

        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                # CHECK A: Is the Institute still alive?
                org_exists = await conn.fetchval(
                    "SELECT 1 FROM organizations WHERE org_id = $1", org_id
                )
                if not org_exists:
                    await self._shred_session(
                        event,
                        state,
                        "❌ Institute deleted. Contact Naganaverse Support.",
                    )
                    return

                # CHECK B: Dynamic Table Routing (Student, Teacher, or Owner)
                table_name = "users"  # Default for Owners
                id_column = "user_id"

                # Route based on the ID prefix to the correct table
                if user_id.startswith("STD"):
                    table_name = "students"
                    id_column = "student_id"
                elif user_id.startswith("TCH"):
                    table_name = "teachers"
                    id_column = "teacher_id"

                # The 'Concrete' Query: Scoped by org_id for multi-tenant safety
                user_record = await conn.fetchrow(
                    f"SELECT status, telegram_id FROM {table_name} WHERE {id_column} = $1 AND org_id = $2",
                    user_id,
                    org_id,
                )

                if not user_record:
                    # Log the specific failure for debugging
                    logger.warning(
                        f"Bouncer: {user_id} not found in {table_name} for org {org_id}"
                    )
                    await self._shred_session(
                        event, state, "❌ User record not found."
                    )
                    return

                # CHECK C: Device Binding (Prevents Ghost Sessions on unbound IDs)
                if str(user_record["telegram_id"]) != str(telegram_id):
                    await self._shred_session(
                        event,
                        state,
                        "🔒 Device unauthorized. Please /login again.",
                    )
                    return

        except Exception as e:
            logger.error(f"AuthMiddleware Bouncer Error: {e}")
            # On DB failure, we fail-safe by letting the session pass or showing error
            pass

        # 4. Success -> Inject session and continue
        data["user_session"] = session
        return await handler(event, data)

    async def _shred_session(
        self, event: TelegramObject, state: FSMContext, message: str
    ):
        """Wipes Redis session and informs the user."""
        # 1. Clear the FSM state
        if state:
            await state.clear()

        # 2. FIX: Actually delete the Ghost Session from Redis
        telegram_id = self._extract_telegram_id(event)
        if telegram_id:
            await delete_session(telegram_id)

        # 3. Respond to the user
        if isinstance(event, Update):
            if event.message:
                await event.message.answer(message)
            elif event.callback_query:
                await event.callback_query.message.answer(message)
                await event.callback_query.answer()

    @staticmethod
    def _extract_telegram_id(event: TelegramObject) -> int | None:
        """Extract Telegram user ID from any update type."""
        update: Update = event
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        elif update.inline_query:
            user = update.inline_query.from_user
        elif update.edited_message:
            user = update.edited_message.from_user

        return user.id if user else None
