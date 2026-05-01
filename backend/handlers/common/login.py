"""
handlers/common/login.py
─────────────────────────────────────────────────────────────
FSM Login flow: Institute Code -> User ID -> Password
Fixed: Prevents Global ID collisions and missing org_id errors.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from loguru import logger

from services.auth_service import login, logout, check_if_needs_password, set_initial_password, parent_login
from keyboards.common_kb import landing_keyboard, nav_only_keyboard
from handlers.common.dashboard import build_dashboard

router = Router()

class LoginFlow(StatesGroup):
    enter_org_id     = State()   # NEW: First step for security
    enter_user_id    = State()
    enter_password   = State()
    set_new_password = State()   # First-time setup


# ── Step 1: Entry — Ask for Institute Code ────────────────

@router.callback_query(F.data.startswith("login:"))
async def cb_login_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    role = callback.data.split(":")[1]

    await state.set_state(LoginFlow.enter_org_id)
    await state.update_data(login_role=role)

    await callback.message.edit_text(
        f"🔐 <b>{role.title()} Login</b>\n\n"
        f"Step 1/3: Enter your <b>Institute Code</b>:\n"
        f"<i>Example: mahaveer_classes or aakash_classes</i>",
        reply_markup=nav_only_keyboard(),
    )


# ── Step 2: ENTER_ORG_ID ──────────────────────────────────

@router.message(LoginFlow.enter_org_id)
async def login_enter_org_id(message: Message, state: FSMContext) -> None:
    # FIX: Always store org_id as lowercase to match DB storage
    org_id = message.text.strip().lower()

    await state.update_data(org_id=org_id)
    data = await state.get_data()
    role = data.get("login_role")

    role_id_examples = {
        "student": "STD102",
        "teacher": "TCH102",
        "owner":   "OWN001",
        "parent":  "PAR_STD001",
    }

    await state.set_state(LoginFlow.enter_user_id)
    await message.answer(
        f"🏢 Institute: <b>{org_id}</b>\n\n"
        f"Step 2/3: Enter your <b>{role.title()} ID</b>:\n"
        f"<i>Example: {role_id_examples.get(role, 'ID001')}</i>",
        reply_markup=nav_only_keyboard(),
    )


# ── Step 3: ENTER_USER_ID ────────────────────────────────

@router.message(LoginFlow.enter_user_id)
async def login_enter_user_id(message: Message, state: FSMContext) -> None:
    # FIX: User IDs (STD001, TCH001, PAR_STD001) are always uppercased
    user_id = message.text.strip().upper()
    data = await state.get_data()
    org_id = data.get("org_id")
    role = data.get("login_role")

    if not org_id:
        await message.answer("❌ Session timed out. Please start /login again.")
        return

    # Parent login has its own dedicated flow (password = last 6 digits of phone)
    if role == "parent":
        await state.update_data(user_id=user_id)
        await state.set_state(LoginFlow.enter_password)
        await message.answer(
            f"🆔 Parent ID: <b>{user_id}</b>\n\n"
            "🔑 Enter your <b>Password</b>:\n"
            "<i>(Last 6 digits of your registered phone number)</i>",
            reply_markup=nav_only_keyboard(),
        )
        return

    # Standard login: check existence scoped to org
    try:
        check = await check_if_needs_password(user_id, org_id)
    except Exception as e:
        logger.error(f"check_if_needs_password failed: {e}")
        await message.answer("⚠️ System error. Please verify your Institute Code and User ID.")
        return

    if not check["exists"]:
        await message.answer(
            f"❌ ID <b>{user_id}</b> not found in institute <b>{org_id}</b>.",
            reply_markup=nav_only_keyboard(),
        )
        return

    await state.update_data(user_id=user_id)

    if check["needs_password"]:
        await state.set_state(LoginFlow.set_new_password)
        await message.answer(
            "🎉 <b>Institute Approved!</b>\n\n"
            "🔑 Please <b>Set a Password</b> (min 4 characters):",
            reply_markup=nav_only_keyboard(),
        )
    else:
        await state.set_state(LoginFlow.enter_password)
        await message.answer(
            f"🆔 ID: <b>{user_id}</b>\n\n"
            "🔑 Enter your <b>Password</b>:",
            reply_markup=nav_only_keyboard(),
        )


# ── Step 4: ENTER_PASSWORD ────────────────────────────────

@router.message(LoginFlow.enter_password)
async def login_enter_password(message: Message, state: FSMContext) -> None:
    telegram_id = message.from_user.id
    password    = message.text.strip()
    data        = await state.get_data()
    user_id     = data.get("user_id", "")
    org_id      = data.get("org_id", "")
    login_role  = data.get("login_role", "")

    try: await message.delete()
    except: pass

    # Parent login — separate service call with org_id for security scoping
    if login_role == "parent":
        result = await parent_login(
            telegram_id=telegram_id,
            parent_id=user_id,
            password=password,
            org_id=org_id,  # FIX: Pass org_id to scope the student lookup
        )
    else:
        # Normal login (Student / Teacher / Owner)
        result = await login(
            telegram_id=telegram_id,
            user_id=user_id,
            org_id=org_id,
            password=password,
        )

    if result["success"]:
        await state.clear()
        session = result["session"]
        text, keyboard = build_dashboard(session)
        await message.answer(f"✅ <b>Login Successful!</b>\n\n{text}", reply_markup=keyboard)
        logger.info(f"Manual login: {user_id}@{org_id}")
    else:
        await message.answer(result.get("message", "❌ Login failed."), reply_markup=nav_only_keyboard())


# ── Logout ────────────────────────────────────────────────

@router.message(Command("logout"))
@router.message(F.text == "/logout")
async def cmd_logout(message: Message, state: FSMContext, user_session: dict = None) -> None:
    await state.clear()
    if not user_session:
        await message.answer("ℹ️ You are not logged in.", reply_markup=landing_keyboard())
        return

    from core.security import delete_session
    await delete_session(message.from_user.id)
    await logout(
        telegram_id=message.from_user.id,
        user_id=user_session.get("user_id"),
        org_id=user_session.get("org_id")
    )

    await message.answer("👋 <b>Logged out successfully.</b>", reply_markup=landing_keyboard())


# ── First Time Set Password ───────────────────────────────

@router.message(LoginFlow.set_new_password)
async def login_set_new_password(message: Message, state: FSMContext) -> None:
    password = message.text.strip()
    data = await state.get_data()

    if len(password) < 4:
        await message.answer("❌ Password too short.", reply_markup=nav_only_keyboard())
        return

    result = await set_initial_password(
        user_id=data.get("user_id"),
        org_id=data.get("org_id"),
        password=password,
        telegram_id=message.from_user.id
    )

    if result["success"]:
        await state.clear()
        text, kb = build_dashboard(result["session"])
        await message.answer(f"✅ <b>Password set! Welcome to Naganaverse.</b>\n\n{text}", reply_markup=kb)
    else:
        await message.answer(result["message"], reply_markup=nav_only_keyboard())
