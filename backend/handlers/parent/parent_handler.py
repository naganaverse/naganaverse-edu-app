"""
handlers/parent/parent_handler.py
─────────────────────────────────────────────────────────────
Parent Dashboard — view child's data only.

Features:
  - Attendance history + percentage
  - Test scores + history
  - Announcements (from teacher, owner, superadmin)

Security:
  - IsParent filter on all handlers
  - All queries scoped to org_id + student_id from session
  - Parent can only see THEIR child's data
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from core.filters import IsParent
from keyboards.parent_kb import parent_dashboard_keyboard
from keyboards.common_kb import nav_only_keyboard
from database.connection import get_pool

router = Router()
router.callback_query.filter(IsParent())


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "parent:home")
async def cb_parent_home(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    student_name = user_session.get("student_name", "Your Child")
    org_name     = user_session.get("org_name", user_session.get("org_id", ""))
    await callback.message.edit_text(
        f"👨‍👩‍👧 <b>Parent Dashboard</b>\n"
        f"🏫 {org_name}\n\n"
        f"👤 Child: <b>{student_name}</b>\n\n"
        "Select what you want to view:",
        reply_markup=parent_dashboard_keyboard(),
    )


# ── Attendance ────────────────────────────────────────────

@router.callback_query(F.data == "parent:attendance")
async def cb_parent_attendance(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    org_id     = user_session["org_id"]
    student_id = user_session["student_id"]
    student_name = user_session.get("student_name", "")

    rows = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    a.subject_name,
                    COUNT(*) AS total_classes,
                    SUM(CASE WHEN ad.status = 'present' THEN 1 ELSE 0 END) AS present_count
                FROM attendance_details ad
                JOIN attendance a ON a.attendance_id = ad.attendance_id
                WHERE ad.student_id = $1 AND a.org_id = $2
                GROUP BY a.subject_name
                ORDER BY a.subject_name
                """,
                student_id, org_id,
            )
    except Exception as e:
        logger.error(f"DB Error fetching parent attendance for student {student_id}: {e}")

    if not rows:
        await callback.message.edit_text(
            f"📊 <b>Attendance — {student_name}</b>\n\n"
            "No attendance records yet.",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = [f"📊 <b>Attendance Report</b>\n👤 {student_name}\n"]
    overall_total   = 0
    overall_present = 0

    for r in rows:
        total   = r["total_classes"] or 0
        present = r["present_count"] or 0
        absent  = total - present
        pct     = round((present / total * 100), 1) if total > 0 else 0.0

        overall_total   += total
        overall_present += present

        emoji = "✅" if pct >= 75 else "⚠️" if pct >= 60 else "❌"
        lines.append(
            f"{emoji} <b>{r['subject_name']}</b>\n"
            f"   {present}/{total} classes  ({pct}%)\n"
            f"   Absent: {absent}\n"
        )

    overall_pct = round((overall_present / overall_total * 100), 1) if overall_total > 0 else 0.0
    lines.append(
        f"\n📈 <b>Overall: {overall_pct}%</b>\n"
        f"   {overall_present}/{overall_total} classes attended"
    )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=nav_only_keyboard(),
    )


# ── Test Scores ───────────────────────────────────────────

@router.callback_query(F.data == "parent:tests")
async def cb_parent_tests(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    org_id       = user_session["org_id"]
    student_id   = user_session["student_id"]
    student_name = user_session.get("student_name", "")

    rows = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.test_name, t.subject_name, t.total_marks,
                       tr.marks, tr.rank, t.date
                FROM test_results tr
                JOIN tests t ON t.test_id = tr.test_id
                WHERE tr.student_id = $1 AND tr.org_id = $2
                ORDER BY t.date DESC
                LIMIT 20
                """,
                student_id, org_id,
            )
    except Exception as e:
        logger.error(f"DB Error fetching parent tests for student {student_id}: {e}")

    if not rows:
        await callback.message.edit_text(
            f"📝 <b>Test Scores — {student_name}</b>\n\n"
            "No test results yet.",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = [f"📝 <b>Test Scores</b>\n👤 {student_name}\n"]
    for r in rows:
        total  = r["total_marks"] or 1
        marks  = r["marks"] or 0
        pct    = round((marks / total * 100), 1)
        emoji  = "🏆" if pct >= 75 else "✅" if pct >= 50 else "⚠️"
        rank   = f" | Rank: #{r['rank']}" if r.get("rank") else ""
        date   = str(r["date"])[:10] if r.get("date") else ""
        lines.append(
            f"{emoji} <b>{r['test_name']}</b>\n"
            f"   📖 {r['subject_name']}  |  📅 {date}\n"
            f"   Score: {marks}/{total} ({pct}%){rank}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=nav_only_keyboard(),
    )


# ── Announcements ─────────────────────────────────────────

@router.callback_query(F.data == "parent:announcements")
async def cb_parent_announcements(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    org_id = user_session["org_id"]

    rows = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # 🛡️ FIX FOR ISSUE #8: Fetching 'message' and using COALESCE for safety
            rows = await conn.fetch(
                """
                SELECT COALESCE(message, 'No Content') as message, created_at
                FROM announcements
                WHERE org_id = $1
                ORDER BY created_at DESC
                LIMIT 10
                """,
                org_id,
            )
    except Exception as e:
        logger.error(f"DB Error fetching parent announcements for org {org_id}: {e}")

    if not rows:
        await callback.message.edit_text(
            "📢 <b>Announcements</b>\n\nNo announcements yet.",
            reply_markup=nav_only_keyboard(),
        )
        return

    lines = ["📢 <b>Recent Announcements</b>\n"]
    for r in rows:
        date = str(r["created_at"])[:10]
        # Use safe extraction
        content = r.get("message", "No Content")
        
        # We don't have a title field, so we use the first 20 characters of the message as a pseudo-title
        title = content[:20] + "..." if len(content) > 20 else content
        
        lines.append(
            f"📌 <b>{title}</b>  <i>({date})</i>\n"
            f"{content}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=nav_only_keyboard(),
  )
  
