"""
handlers/owner/settings_handler.py
─────────────────────────────────────────────────────────────
Settings: Edit Coaching Profile | Subscription Status | Change Password
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.filters import IsOwner
from keyboards.owner_kb import settings_keyboard
from keyboards.common_kb import nav_only_keyboard, nav_row
from database.repositories.org_repo import OrgRepository
from database.repositories.subscription_repo import SubscriptionRepository
from database.repositories.user_repo import UserRepository
from core.security import hash_password, verify_password

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_org_repo  = OrgRepository()
_sub_repo  = SubscriptionRepository()
_user_repo = UserRepository()


class SettingsFSM(StatesGroup):
    edit_field = State()
    edit_value = State()

class ChangePasswordFSM(StatesGroup):
    old_password = State()
    new_password = State()


@router.callback_query(F.data == "owner:settings")
async def cb_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "⚙️ <b>Settings</b>",
        reply_markup=settings_keyboard(),
    )


# ── View / Edit Coaching Profile ──────────────────────────

@router.callback_query(F.data == "owner:edit_profile")
async def cb_edit_profile(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    org = await _org_repo.get_by_org_id(user_session["org_id"])
    if not org:
        await callback.message.edit_text("❌ Profile not found.", reply_markup=nav_only_keyboard())
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit Name",    callback_data="profile:org_name")],
        [InlineKeyboardButton(text="📞 Edit Phone",   callback_data="profile:phone")],
        [InlineKeyboardButton(text="🏙 Edit City",    callback_data="profile:city")],
        nav_row(),
    ])
    
    await callback.message.edit_text(
        f"🏫 <b>Coaching Profile</b>\n\n"
        f"📛 Name: {org.org_name}\n"
        f"👤 Owner: {org.owner_name}\n"
        f"📞 Phone: {org.phone or '—'}\n"
        f"🏙 City: {org.city or '—'}\n"
        f"📦 Plan: {org.plan_type.title()}\n\n"
        "Tap a field to edit:",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("profile:"))
async def cb_profile_field(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    field = callback.data.split(":", 1)[1]
    labels = {"org_name": "Coaching Name", "phone": "Phone Number", "city": "City"}
    await state.update_data(profile_field=field)
    await state.set_state(SettingsFSM.edit_value)
    await callback.message.edit_text(
        f"✏️ Enter new <b>{labels.get(field, field)}</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(SettingsFSM.edit_value)
async def msg_profile_value(message: Message, state: FSMContext, user_session: dict) -> None:
    value = message.text.strip()
    data  = await state.get_data()
    field = data.get("profile_field")
    await state.clear()

    updated = await _org_repo.update_profile(user_session["org_id"], **{field: value})
    await message.answer(
        "✅ Profile updated." if updated else "❌ Update failed.",
        reply_markup=nav_only_keyboard(),
    )


# ── Subscription Status ───────────────────────────────────

@router.callback_query(F.data == "owner:subscription")
async def cb_subscription(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    sub = await _sub_repo.get_by_org(user_session["org_id"])
    if not sub:
        await callback.message.edit_text(
            "📋 <b>Subscription</b>\n\nNo active subscription found.\nContact Naganaverse support.",
            reply_markup=nav_only_keyboard(),
        )
        return

    status_icon = "✅" if sub.status == "active" else "❌"
    expired_txt = " ⚠️ <b>EXPIRED</b>" if sub.is_expired else ""

    await callback.message.edit_text(
        f"📋 <b>Subscription Status</b>\n\n"
        f"📦 Plan: <b>{sub.plan.title()}</b>\n"
        f"📅 Start: {sub.start_date}\n"
        f"📅 Expiry: {sub.expiry_date}{expired_txt}\n"
        f"Status: {status_icon} {sub.status.title()}",
        reply_markup=nav_only_keyboard(),
    )


# ── Change Password ───────────────────────────────────────

@router.callback_query(F.data == "owner:change_password")
async def cb_change_password_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ChangePasswordFSM.old_password)
    await callback.message.edit_text(
        "🔐 Please enter your **CURRENT** password:",
        reply_markup=nav_only_keyboard()
    )


@router.message(ChangePasswordFSM.old_password)
async def process_old_password(message: Message, state: FSMContext, user_session: dict):
    user_id = user_session['user_id']
    
    # Fetch current owner record to get the hash
    user = await _user_repo.get_by_user_id(user_id)
    
    # Verify what they typed against the DB hash
    if not user or not verify_password(message.text, user.password_hash):
        await message.answer("❌ Incorrect current password. Password change cancelled.", reply_markup=nav_only_keyboard())
        await state.clear()
        return
        
    # If correct, move to the next state
    await state.set_state(ChangePasswordFSM.new_password)
    await message.answer(
        "✅ Correct. Now enter your **NEW** password (minimum 4 characters):",
        reply_markup=nav_only_keyboard()
    )


@router.message(ChangePasswordFSM.new_password)
async def msg_new_password(message: Message, state: FSMContext, user_session: dict) -> None:
    password = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass

    if len(password) < 4:
        await message.answer("❌ Password too short. Please try again.", reply_markup=nav_only_keyboard())
        return

    await state.clear()
    updated = await _user_repo.update_password(user_session["user_id"], hash_password(password))
    await message.answer(
        "✅ Password updated successfully." if updated else "❌ Update failed.",
        reply_markup=nav_only_keyboard(),
    )


# ── Notification Settings ─────────────────────────────────

@router.callback_query(F.data == "owner:notif_settings")
async def cb_notif_settings(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🔔 <b>Parent Notification Settings</b>\n\n"
        "WhatsApp notifications are sent automatically when:\n"
        "• 📊 You send attendance reports\n"
        "• 📝 Test results are submitted\n"
        "• ❌ A student is marked absent\n\n"
        "To configure your WhatsApp API, contact Naganaverse support email -: supportnaganaverse@gmail.com.",
        reply_markup=nav_only_keyboard(),
    )
    
