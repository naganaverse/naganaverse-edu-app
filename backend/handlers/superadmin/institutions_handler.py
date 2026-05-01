"""
handlers/superadmin/institutions_handler.py
─────────────────────────────────────────────────────────────
Handles all institution management flows:

A) Approval Flow:
   Show pending list → Approve (toggle button) / Reject (reason)
   On approve: status=active, notify owner via Telegram + SMS stub
   On reject:  status=rejected, notify owner

B) Search & Manage:
   Search by name → show stats → Freeze (reason) / Delete (type DELETE)

C) View all active institutions

Delete requires admin to TYPE "DELETE" — double confirmation.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsSuperAdmin
from core.loader import bot
from services.superadmin_service import (
    get_pending_institutions,
    approve_institution,
    reject_institution,
    freeze_institution,
    delete_institution,
)
from keyboards.superadmin_kb import (
    institution_management_keyboard,
    pending_institution_keyboard,
    reject_reason_keyboard,
    institution_approved_keyboard,
    delete_confirm_keyboard,
)
from keyboards.common_kb import nav_only_keyboard, confirm_keyboard
from database.repositories.org_repo import OrgRepository
from database.repositories.student_repo import StudentRepository
from database.repositories.teacher_repo import TeacherRepository

router = Router()
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())

_org_repo     = OrgRepository()
_student_repo = StudentRepository()
_teacher_repo = TeacherRepository()


class InstitutionFSM(StatesGroup):
    search        = State()
    delete_confirm = State()
    freeze_reason  = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "sa:institutions")
async def cb_institutions_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "🏫 <b>Institution Management</b>",
        reply_markup=institution_management_keyboard(),
    )


# ── A) Approval Flow ──────────────────────────────────────

@router.callback_query(F.data == "sa:approve_list")
async def cb_approve_list(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    pending = await get_pending_institutions()

    if not pending:
        await callback.message.edit_text(
            "✅ No pending institution requests.",
            reply_markup=nav_only_keyboard(),
        )
        return

    await state.update_data(pending=pending, pending_index=0)
    await _show_pending(callback.message, pending, 0, edit=True)


async def _show_pending(message, pending: list, index: int, edit: bool = False) -> None:
    if index >= len(pending):
        text = "✅ All pending requests reviewed."
        kb   = nav_only_keyboard()
    else:
        p    = pending[index]
        text = (
            f"🏫 <b>Pending Institution Request</b>\n"
            f"({index + 1}/{len(pending)})\n\n"
            f"🏢 Name: <b>{p['org_name']}</b>\n"
            f"👤 Owner: {p['owner_name']}\n"
            f"📞 Phone: {p['phone'] or '—'}\n"
            f"🏙 City: {p['city'] or '—'}\n"
            f"🆔 Org ID: <code>{p['org_id']}</code>\n"
            f"📅 Applied: {p.get('created_at', '—')[:10]}"
        )
        kb = pending_institution_keyboard(p["org_id"], p["org_name"])

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
@router.callback_query(F.data.startswith("sa:set_status:"))
async def cb_change_status_prompt(callback: CallbackQuery) -> None:
    """Shows options to change status after searching an institution."""
    org_id = callback.data.split(":")[2]
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from keyboards.common_kb import nav_row
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Make Active", callback_data=f"sa:confirm_status:{org_id}:active")],
        [InlineKeyboardButton(text="⏳ Reset to Pending", callback_data=f"sa:confirm_status:{org_id}:pending")],
        [InlineKeyboardButton(text="❌ Reject", callback_data=f"sa:confirm_status:{org_id}:rejected")],
        nav_row()
    ])
    
    await callback.message.edit_text(
        f"⚙️ <b>Change Status: {org_id}</b>\n\nSelect the new status for this institution:",
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("sa:confirm_status:"))
async def cb_change_status_confirm(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    org_id, new_status = parts[2], parts[3]
    
    from services.superadmin_service import update_institution_status
    result = await update_institution_status(org_id, new_status, callback.from_user.id)
    
    await callback.answer(result["message"])
    await callback.message.edit_text(
        f"{result['message']}\n\nUse /start to refresh the menu.",
        reply_markup=nav_only_keyboard()
)
   

@router.callback_query(F.data == "sa:next_pending")
async def cb_next_pending(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data  = await state.get_data()
    index = data.get("pending_index", 0) + 1
    await state.update_data(pending_index=index)
    pending = data.get("pending", [])
    await _show_pending(callback.message, pending, index, edit=True)


@router.callback_query(F.data.startswith("sa:approve:"))
async def cb_approve_institution(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Approving...")
    org_id = callback.data.split(":", 2)[2]
    result = await approve_institution(org_id, callback.from_user.id)

    if result["success"]:
        # Toggle button to show approved state
        await callback.message.edit_reply_markup(
            reply_markup=institution_approved_keyboard(org_id)
        )
        await callback.message.answer(result["message"])

        # Notify owner via Telegram
        await _notify_owner_approval(org_id, approved=True)

        # Advance to next pending
        data  = await state.get_data()
        index = data.get("pending_index", 0) + 1
        await state.update_data(pending_index=index)
        pending = data.get("pending", [])
        if index < len(pending):
            await _show_pending(callback.message, pending, index, edit=False)
    else:
        await callback.message.answer(result["message"])


@router.callback_query(F.data.startswith("sa:reject:"))
async def cb_reject_prompt(callback: CallbackQuery) -> None:
    await callback.answer()
    org_id = callback.data.split(":", 2)[2]
    await callback.message.edit_text(
        "❌ <b>Reject Institution</b>\n\nSelect rejection reason:",
        reply_markup=reject_reason_keyboard(org_id),
    )


@router.callback_query(F.data.startswith("sa:reject_reason:"))
async def cb_reject_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Rejecting...")
    parts  = callback.data.split(":", 3)
    org_id = parts[2]
    reason = parts[3]

    reason_labels = {
        "spam":      "Spam Registration",
        "invalid":   "Invalid Institution",
        "duplicate": "Duplicate Request",
    }
    reason_text = reason_labels.get(reason, reason)
    result = await reject_institution(org_id, reason_text, callback.from_user.id)
    await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())

    # Notify owner via Telegram
    await _notify_owner_approval(org_id, approved=False, reason=reason_text)

    # Advance pending list
    data  = await state.get_data()
    index = data.get("pending_index", 0) + 1
    await state.update_data(pending_index=index)
    pending = data.get("pending", [])
    if index < len(pending):
        await _show_pending(callback.message, pending, index, edit=False)


async def _notify_owner_approval(org_id: str, approved: bool, reason: str = None) -> None:
    """
    Notify the institution owner via Telegram when approved or rejected.
    Queries users table (populated during registration) for telegram_id.
    SMS notification stub — integrate with SMS API (e.g. Twilio, MSG91).
    """
    from database.connection import get_pool
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.telegram_id, u.user_id, u.phone, org.org_name
            FROM users u
            JOIN organizations org ON org.org_id = u.org_id
            WHERE u.org_id = $1 AND u.role = 'owner'
            """,
            org_id,
        )

    if not row:
        return

    if approved:
        msg = (
            f"🎉 <b>Institution Approved!</b>\n\n"
            f"🏫 <b>{row['org_name']}</b> is now active on Naganaverse.\n\n"
            f"🆔 <b>Your Owner ID:</b> <code>{row['user_id']}</code>\n\n"
            f"To login:\n"
            f"1️⃣ Open the bot\n"
            f"2️⃣ Tap <b>Login as Owner</b>\n"
            f"3️⃣ Enter your Owner ID\n"
            f"4️⃣ You will be asked to set your password\n\n"
            f"Use /start to begin. 🚀"
        )
    else:
        msg = (
            f"❌ <b>Institution Not Approved</b>\n\n"
            f"🏫 {row['org_name']}\n"
            f"Reason: {reason or 'Not specified'}\n\n"
            f"For queries, contact Naganaverse support."
        )

    # Telegram notification (mandatory)
    if row["telegram_id"]:
        try:
            await bot.send_message(row["telegram_id"], msg)
        except Exception:
            pass

    # SMS stub (mandatory — integrate SMS API here)
    if row["phone"]:
        # TODO: integrate MSG91 / Twilio
        # await sms_service.send(row["phone"], msg)
        pass


# ── B) Search & Manage ────────────────────────────────────

@router.callback_query(F.data == "sa:search_inst")
async def cb_search_inst_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(InstitutionFSM.search)
    await callback.message.edit_text(
        "🔍 <b>Search Institution</b>\n\nEnter institution name or org_id:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(InstitutionFSM.search)
async def msg_search_inst(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    query = message.text.strip()
    
    # Get the intent BEFORE clearing the state
    data = await state.get_data()
    search_intent = data.get("search_intent", "manage")
    await state.clear()

    orgs = await _org_repo.search_by_name(query)
    if not orgs:
        # Try exact org_id fallback
        org = await _org_repo.get_by_org_id(query.lower().replace(" ", "_"))
        orgs = [org] if org else []

    if not orgs:
        await message.answer(
            f"❌ No institution found for '<b>{query}</b>'.",
            reply_markup=nav_only_keyboard(),
        )
        return

    for org in orgs[:3]:
        student_count = await _student_repo.count_by_org(org.org_id)
        teacher_count = await _teacher_repo.count_by_org(org.org_id)

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from keyboards.common_kb import nav_row

        # ── Updated Action Button Logic ──
        if search_intent == "freeze":
            action_buttons = [[InlineKeyboardButton(
                text="❄️ Freeze This Institution",
                callback_data=f"sa:freeze_inst:{org.org_id}"
            )]]
        elif search_intent == "delete":
            action_buttons = [[InlineKeyboardButton(
                text="🗑 Delete This Institution",
                callback_data=f"sa:delete_inst:{org.org_id}"
            )]]
        else:
            # Default 'manage' intent - includes the new Status Override button
            action_buttons = [
                [
                    InlineKeyboardButton(text="❄️ Freeze",  callback_data=f"sa:freeze_inst:{org.org_id}"),
                    InlineKeyboardButton(text="🗑 Delete",  callback_data=f"sa:delete_inst:{org.org_id}"),
                ],
                [
                    InlineKeyboardButton(text="⚙️ Change Status", callback_data=f"sa:set_status:{org.org_id}")
                ]
            ]

        kb = InlineKeyboardMarkup(inline_keyboard=action_buttons + [nav_row()])
        
        await message.answer(
            f"🏫 <b>{org.org_name}</b>\n"
            f"🆔 <code>{org.org_id}</code>\n"
            f"👤 Owner: {org.owner_name}\n"
            f"📞 {org.phone or '—'} | 🏙 {org.city or '—'}\n"
            f"📦 Plan: {org.plan_type} | <b>Status: {org.status.upper()}</b>\n"
            f"👥 Students: {student_count} | 👨‍🏫 Teachers: {teacher_count}",
            reply_markup=kb,
            )
       



# ── Menu Entry: Freeze (asks for org_id first) ───────────────

@router.callback_query(F.data == "sa:freeze_inst")
async def cb_freeze_inst_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry from institution management menu — asks for org_id."""
    await callback.answer()
    await state.set_state(InstitutionFSM.search)
    await state.update_data(search_intent="freeze")
    await callback.message.edit_text(
        "❄️ <b>Freeze Institution</b>\n\n"
        "Enter the <b>Institution Name or Org ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


# ── Menu Entry: Delete (asks for org_id first) ───────────────

@router.callback_query(F.data == "sa:delete_inst")
async def cb_delete_inst_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry from institution management menu — asks for org_id."""
    await callback.answer()
    await state.set_state(InstitutionFSM.search)
    await state.update_data(search_intent="delete")
    await callback.message.edit_text(
        "🗑 <b>Delete Institution</b>\n\n"
        "Enter the <b>Institution Name or Org ID</b>:",
        reply_markup=nav_only_keyboard(),
    )


# ── Freeze Institution ────────────────────────────────────

@router.callback_query(F.data.startswith("sa:freeze_inst:"))
async def cb_freeze_inst_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    org_id = callback.data.split(":", 2)[2]
    await state.update_data(freeze_org_id=org_id)
    await state.set_state(InstitutionFSM.freeze_reason)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from keyboards.common_kb import nav_row
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Spam Activity",      callback_data=f"sa:freeze_confirm:{org_id}:spam")],
        [InlineKeyboardButton(text="💳 Payment Issue",       callback_data=f"sa:freeze_confirm:{org_id}:payment")],
        [InlineKeyboardButton(text="🔐 Security Violation", callback_data=f"sa:freeze_confirm:{org_id}:security")],
        nav_row(),
    ])
    await callback.message.edit_text(
        f"❄️ <b>Freeze Institution</b>\n\n"
        f"<code>{org_id}</code>\n\n"
        "Select reason:",
        reply_markup=kb,
    )


@router.callback_query(InstitutionFSM.freeze_reason, F.data.startswith("sa:freeze_confirm:"))
async def cb_freeze_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Freezing...")
    parts  = callback.data.split(":", 3)
    org_id = parts[2]
    reason = parts[3]
    await state.clear()

    result = await freeze_institution(org_id, callback.from_user.id)

    # Notify users of the frozen org
    await _notify_org_frozen(org_id)

    await callback.message.edit_text(
        result["message"] + f"\nReason: {reason}",
        reply_markup=nav_only_keyboard(),
    )


async def _notify_org_frozen(org_id: str) -> None:
    """
    When institution is frozen, users hitting the bot
    will be blocked by AuthMiddleware (org status check).
    Active sessions are not forcibly killed — they expire naturally.
    """
    pass  # Handled via org status check in auth_service.check_user()


# ── Delete Institution ────────────────────────────────────

@router.callback_query(F.data.startswith("sa:delete_inst:"))
async def cb_delete_inst_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    org_id = callback.data.split(":", 2)[2]
    org    = await _org_repo.get_by_org_id(org_id)
    if not org:
        await callback.message.edit_text("❌ Institution not found.", reply_markup=nav_only_keyboard())
        return

    await state.update_data(delete_org_id=org_id, delete_org_name=org.org_name)
    await state.set_state(InstitutionFSM.delete_confirm)

    await callback.message.edit_text(
        f"🗑 <b>Delete Institution — PERMANENT</b>\n\n"
        f"🏫 <b>{org.org_name}</b>\n"
        f"🆔 <code>{org_id}</code>\n\n"
        f"⚠️ This will permanently delete:\n"
        f"• All students, teachers, attendance\n"
        f"• All tests, results, homework, resources\n"
        f"• All announcements and notifications\n\n"
        f"To confirm, type <b>DELETE</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(InstitutionFSM.delete_confirm)
async def msg_delete_confirm(
    message: Message, state: FSMContext
) -> None:
    if message.text.strip() != "DELETE":
        await message.answer(
            "❌ Incorrect confirmation. Type exactly <b>DELETE</b> to proceed, "
            "or tap 🏠 Home to cancel.",
            reply_markup=nav_only_keyboard(),
        )
        return

    data   = await state.get_data()
    org_id = data["delete_org_id"]
    name   = data.get("delete_org_name", org_id)
    await state.clear()

    result = await delete_institution(org_id, message.from_user.id)
    await message.answer(result["message"], reply_markup=nav_only_keyboard())
