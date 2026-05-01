"""
handlers/owner/test_reports_handler.py
─────────────────────────────────────────────────────────────
Owner: View test results + send reports to parents
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.filters import IsOwner
from services.test_service import get_test_summary
from services.notification_service import send_test_results_to_parents
from keyboards.owner_kb import select_tests_keyboard, test_report_actions_keyboard
from keyboards.common_kb import nav_only_keyboard
from database.repositories.test_repo import TestRepository

router = Router()
router.callback_query.filter(IsOwner())

_test_repo = TestRepository()


@router.callback_query(F.data == "owner:test_reports")
async def cb_test_reports_menu(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    org_id = user_session["org_id"]

    from database.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT test_id, topic, test_name FROM tests WHERE org_id = $1 ORDER BY created_at DESC LIMIT 20",
            org_id,
        )

    if not rows:
        await callback.message.edit_text("📝 No tests found yet.", reply_markup=nav_only_keyboard())
        return

    tests = [{"test_id": str(r["test_id"]), "topic": r["topic"] or r["test_name"]} for r in rows]
    await callback.message.edit_text(
        "📝 <b>Test Reports</b>\n\nSelect a test:",
        reply_markup=select_tests_keyboard(tests),
    )


@router.callback_query(F.data.startswith("owner:test_report:"))
async def cb_test_report_view(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    test_id = callback.data.split(":", 2)[2]
    org_id  = user_session["org_id"]

    summary = await get_test_summary(test_id, org_id)
    if not summary["success"]:
        await callback.message.edit_text(summary["message"], reply_markup=nav_only_keyboard())
        return

    test = summary["test"]
    await callback.message.edit_text(
        summary["message"],
        reply_markup=test_report_actions_keyboard(test_id),
    )


@router.callback_query(F.data.startswith("owner:test_send_parents:"))
async def cb_send_test_to_parents(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer("Sending reports...")
    test_id = callback.data.split(":", 2)[2]
    org_id  = user_session["org_id"]

    test = await _test_repo.get_test_by_id(test_id, org_id)
    if not test:
        await callback.message.edit_text("❌ Test not found.", reply_markup=nav_only_keyboard())
        return

    result = await send_test_results_to_parents(
        org_id=org_id,
        test_id=test_id,
        class_name=test.class_name,
        triggered_by=user_session["user_id"],
    )
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())
