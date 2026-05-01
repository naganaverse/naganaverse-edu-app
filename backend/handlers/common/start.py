"""
handlers/common/start.py
─────────────────────────────────────────────────────────────
Main Entry Point for Naganaverse Education Bot.
Handles:
  1. Smart Auto-Login (/start): Recognizes bound devices.
  2. Home Navigation (/home): Resets state to dashboard.
  3. Institution Registration: Multi-step FSM with Pause Guard.
  4. Multi-tenant Isolation: Binds Telegram IDs on registration.
─────────────────────────────────────────────────────────────
"""

import re
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from config.config import settings
from core.loader import bot
from core.security import create_user_session
from database.connection import get_pool
from database.repositories.org_repo import OrgRepository
from database.repositories.user_repo_security import AuditLogRepository, SystemSettingsRepository
from services.referral_service import validate_and_apply_referral, generate_referral_code
from keyboards.common_kb import landing_keyboard, nav_only_keyboard, back_keyboard
from handlers.common.dashboard import build_dashboard

router = Router()
_org_repo = OrgRepository()
_audit = AuditLogRepository()
_settings_repo = SystemSettingsRepository()


# ─────────────────────────────────────────────
# FSM: Register Institution
# ─────────────────────────────────────────────

class RegisterInstitution(StatesGroup):
    institution_name = State()
    owner_name       = State()
    phone            = State()
    city             = State()
    referral_code    = State()


# ─────────────────────────────────────────────
# /start and /home (SMART LOGIC)
# ─────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user_session: dict = None) -> None:
    """Entry point. Clears state and attempts Auto-Login."""
    await state.clear()
    await _handle_start(message, user_session=user_session)


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext, user_session: dict = None) -> None:
    """Reset to home dashboard."""
    await state.clear()
    await _handle_start(message, user_session=user_session)


@router.callback_query(F.data == "nav:home")
async def cb_home(callback: CallbackQuery, state: FSMContext, user_session: dict = None) -> None:
    """Home button callback."""
    await state.clear()
    await callback.answer()
    await _handle_start(callback.message, edit=True, user_session=user_session)


async def _handle_start(message: Message, edit: bool = False, user_session: dict = None) -> None:
    """
    The Bouncer-integrated Start Logic:
    1. Use existing Middleware session if available.
    2. Fallback: Search Database for bound telegram_id.
    3. Final: Show Landing Screen (Login/Register).
    """
    telegram_id = message.chat.id

    # 1. Check if Middleware already found a session
    if user_session:
        return await _render_dashboard(message, user_session, edit=edit)

    # 2. Database Lookup for Auto-Login
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT u.user_id, u.org_id, u.role, u.status, o.org_name 
                FROM users u
                JOIN organizations o ON u.org_id = o.org_id
                WHERE u.telegram_id = $1 AND u.status = 'active' AND o.status = 'active'
                """,
                telegram_id
            )

            if user:
                # Create session in Redis and render
                session = await create_user_session(
    user_id=user['user_id'],
    org_id=user['org_id'],
    role=user['role'],
    telegram_id=telegram_id 
                )
              
    
                  
                
                logger.info(f"Auto-Login Success | tg={telegram_id} | org={user['org_id']}")
                await message.answer(f"👋 Welcome back to <b>{user['org_name']}</b>!")
                return await _render_dashboard(message, session, edit=edit)

    except Exception as e:
        logger.error(f"Auto-Login failure for {telegram_id}: {e}")

    # 3. If no binding found, show landing
    await _render_landing(message, edit=edit)


# ─────────────────────────────────────────────
# Renderers
# ─────────────────────────────────────────────

async def _render_dashboard(message: Message, session: dict, edit: bool = False) -> None:
    """Render the correct dashboard based on role."""
    text, keyboard = build_dashboard(session)
    try:
        if edit:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)
    except Exception:
        await message.answer(text, reply_markup=keyboard)


async def _render_landing(message: Message, edit: bool = False) -> None:
    """Landing screen for guests."""
    text = (
        "🎓 <b>Welcome to Naganaverse Education</b>\n\n"
        "The smart coaching management platform.\n\n"
        "🔐 Login Required — choose an option below:"
    )
    try:
        if edit:
            await message.edit_text(text, reply_markup=landing_keyboard())
            return
    except Exception:
        pass
    await message.answer(text, reply_markup=landing_keyboard())


@router.callback_query(F.data == "about_bot")
async def cb_about_bot(callback: CallbackQuery) -> None:
    await callback.answer()
    text = (
        "ℹ️ <b>About Naganaverse Education Bot</b>\n\n"
        "Naganaverse is a Multi-Tenant SaaS platform providing intelligent "
        "automation and management for coaching institutes.\n\n"
        "<b>Features:</b>\n"
        "📚 Resource Distribution | 📌 Homework\n"
        "📋 Attendance Tracking | 📝 Tests\n"
        "📊 Analytics | 📲 WhatsApp Alerts\n\n"
        "<i>Powering the future of education.</i>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard("nav:home"))


# ─────────────────────────────────────────────
# Register Institution FSM (WITH PAUSE GUARD)
# ─────────────────────────────────────────────

@router.callback_query(F.data == "register_institution")
async def cb_register_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()

    # 🛡️ THE BOUNCER: Registration Pause Check
    try:
        if await _settings_repo.get_registrations_paused():
            await callback.message.edit_text(
                "⏸ <b>Registrations are currently paused.</b>\n"
                "Please try again later or contact Naganaverse support.",
                reply_markup=nav_only_keyboard(),
            )
            return
    except Exception as e:
        logger.error(f"Registration setting check failed: {e}")

    await state.set_state(RegisterInstitution.institution_name)
    await callback.message.edit_text(
        "🏫 <b>Register Your Institution</b>\n\nStep 1/5\n\n"
        "Enter your <b>Institution Name</b>:\n"
        "<i>Example: Mukesh Classes</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(RegisterInstitution.institution_name)
async def reg_institution_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Name too short. Please enter at least 3 characters.")
        return
    await state.update_data(institution_name=name)
    await state.set_state(RegisterInstitution.owner_name)
    await message.answer(f"✅ Institution: <b>{name}</b>\n\nStep 2/5\n\nEnter the <b>Owner Name</b>:")


@router.message(RegisterInstitution.owner_name)
async def reg_owner_name(message: Message, state: FSMContext) -> None:
    await state.update_data(owner_name=message.text.strip())
    await state.set_state(RegisterInstitution.phone)
    await message.answer("Step 3/5\n\nEnter your <b>Contact Number</b>:")


@router.message(RegisterInstitution.phone)
async def reg_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "")
    if not phone.lstrip("+").isdigit() or len(phone) < 10:
        await message.answer("❌ Invalid phone number.")
        return
    await state.update_data(phone=phone)
    await state.set_state(RegisterInstitution.city)
    await message.answer("Step 4/5\n\nEnter your <b>City</b>:")


@router.message(RegisterInstitution.city)
async def reg_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=message.text.strip())
    await state.set_state(RegisterInstitution.referral_code)
    
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Skip", callback_data="reg:skip_referral")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="nav:home")]
    ])
    await message.answer("Step 5/5 (Optional)\n\nEnter a <b>Referral Code</b> or tap Skip:", reply_markup=skip_kb)


@router.callback_query(F.data == "reg:skip_referral")
async def reg_skip_referral(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    
    # 1. Immediately remove the inline keyboard to prevent double-clicks!
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
        
    await state.update_data(referral_code=None)
    await _complete_registration(callback.message, state)




# ─────────────────────────────────────────────
# Finalization & Database Storage
# ─────────────────────────────────────────────

async def _complete_registration(message: Message, state: FSMContext) -> None:
    """Saves to DB with 'pending' status and binds the Telegram ID."""
    data = await state.get_data()
    
    # Anti-Double-Click Guard
    org_name = data.get("institution_name")
    if not org_name:
        return  

    await state.clear()

    owner_name = data.get("owner_name")
    phone = data.get("phone")
    city = data.get("city")
    referral_code = data.get("referral_code")
    registrant_tg_id = message.chat.id

    slug = _slugify(org_name)

    try:
        from database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # 1. Slug collision check FIRST
                exists = await conn.fetchval("SELECT 1 FROM organizations WHERE org_id = $1", slug)
                if exists: 
                    # Append last 4 digits of phone to make it unique
                    slug = f"{slug}_{phone[-4:]}"

                # 🛡️ FIX: Generate owner_id AFTER we are 100% sure the slug is unique!
                owner_id = f"OWN_{slug[:45].upper()}"

                # 2. Create Organization (Pending)
                from services.referral_service import generate_referral_code
                new_ref = generate_referral_code(org_name)
                await conn.execute(
                    """
                    INSERT INTO organizations (org_id, org_name, owner_name, phone, city, referral_code, referred_by, status, plan_type)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', 'starter')
                    """,
                    slug, org_name, owner_name, phone, city, new_ref, referral_code
                )

                # 3. Create User (Locked - Waiting for Approval)
                await conn.execute(
                    """
                    INSERT INTO users (user_id, org_id, name, role, phone, telegram_id, password_hash, status)
                    VALUES ($1, $2, $3, 'owner', $4, $5, '', 'locked')
                    """,
                    owner_id, slug, owner_name, phone, registrant_tg_id
                )

        from database.repositories.user_repo_security import AuditLogRepository
        _audit = AuditLogRepository()
        await _audit.log("INSTITUTION_REGISTERED", details={"org_id": slug, "owner": owner_name})
        
        from keyboards.common_kb import nav_only_keyboard
        await message.answer(
            f"🏫 <b>Registration Submitted!</b>\n\n"
            f"Institution: <b>{org_name}</b>\n"
            f"🆔 Your Owner ID: <code>{owner_id}</code>\n\n"
            f"⏳ <b>Status: Under Review</b>\n"
            f"You will be notified once approved by Naganaverse Admin.",
            reply_markup=nav_only_keyboard()
        )

        # Notify Super Admins
        from config.config import settings
        from core.loader import bot
        for admin_id in settings.super_admin_id_list:
            try:
                from keyboards.superadmin_kb import pending_institution_keyboard
                await bot.send_message(
                    admin_id, 
                    f"🔔 <b>New Request: {org_name}</b>\nOwner: {owner_name}\nID: <code>{slug}</code>",
                    reply_markup=pending_institution_keyboard(slug, org_name)
                )
            except Exception: pass

    except Exception as e:
        from loguru import logger
        logger.error(f"Registration DB Error: {e}")
        await message.answer("❌ Registration failed. Please try again.")
  
def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:50]


@router.callback_query(F.data == "nav:back")
async def cb_nav_back(callback: CallbackQuery, state: FSMContext, user_session: dict = None) -> None:
    await callback.answer()
    await state.clear()
    await _handle_start(callback.message, edit=True, user_session=user_session)
