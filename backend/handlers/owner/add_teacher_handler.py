"""
handlers/owner/add_teacher_handler.py
─────────────────────────────────────────────────────────────
FSM States:
  ADD_TCH_NAME       → teacher name
  ADD_TCH_SUBJECTS   → comma-separated subjects
  ADD_TCH_CLASSES    → comma-separated assigned classes
  ADD_TCH_PHONE      → phone number
  ADD_TCH_ID         → owner creates teacher_id (TCH001)
  ADD_TCH_PASSWORD   → owner creates password

Validation:
  - teacher_id globally unique
  - Max 50 teachers per org enforced in owner_service
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsOwner
from services.owner_service import add_teacher
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())


class AddTeacherFSM(StatesGroup):
    name     = State()
    subjects = State()
    classes  = State()
    phone    = State()
    tch_id   = State()
    password = State()


@router.callback_query(F.data == "owner:teacher_add")
async def cb_add_teacher_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(AddTeacherFSM.name)
    await callback.message.edit_text(
        "➕ <b>Add Teacher</b>\n\n"
        "Step 1/6 — Enter <b>Teacher Name</b>:\n"
        "<i>Example: Rahul Sharma</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddTeacherFSM.name)
async def msg_tch_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Name too short.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(name=name)
    await state.set_state(AddTeacherFSM.subjects)
    await message.answer(
        f"✅ Name: <b>{name}</b>\n\n"
        "Step 2/6 — Enter <b>Subjects</b>:\n"
        "<i>Comma-separated. Example: Physics, Chemistry</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddTeacherFSM.subjects)
async def msg_tch_subjects(message: Message, state: FSMContext) -> None:
    subjects = [s.strip() for s in message.text.split(",") if s.strip()]
    if not subjects:
        await message.answer("❌ Enter at least one subject.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(subjects=subjects)
    await state.set_state(AddTeacherFSM.classes)
    await message.answer(
        f"✅ Subjects: <b>{', '.join(subjects)}</b>\n\n"
        "Step 3/6 — Enter <b>Assigned Classes</b>:\n"
        "<i>Comma-separated. Example: Class 10, Class 11, Class 12</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddTeacherFSM.classes)
async def msg_tch_classes(message: Message, state: FSMContext) -> None:
    classes = [c.strip() for c in message.text.split(",") if c.strip()]
    if not classes:
        await message.answer("❌ Enter at least one class.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(classes=classes)
    await state.set_state(AddTeacherFSM.phone)
    await message.answer(
        f"✅ Classes: <b>{', '.join(classes)}</b>\n\n"
        "Step 4/6 — Enter <b>Phone Number</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddTeacherFSM.phone)
async def msg_tch_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "")
    if not phone.lstrip("+").isdigit() or len(phone) < 10:
        await message.answer("❌ Invalid phone number.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(phone=phone)
    await state.set_state(AddTeacherFSM.tch_id)
    await message.answer(
        "Step 5/6 — Create <b>Teacher ID</b>:\n"
        "<i>Example: TCH001, TCH102</i>\n\n"
        "⚠️ This ID must be unique.",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddTeacherFSM.tch_id)
async def msg_tch_id(message: Message, state: FSMContext) -> None:
    tch_id = message.text.strip().upper()
    if len(tch_id) < 3:
        await message.answer("❌ ID too short.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(tch_id=tch_id)
    await state.set_state(AddTeacherFSM.password)
    await message.answer(
        f"✅ Teacher ID: <code>{tch_id}</code>\n\n"
        "Step 6/6 — Create <b>Password</b>:\n"
        "<i>Share this with the teacher securely.</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddTeacherFSM.password)
async def msg_tch_password(message: Message, state: FSMContext, user_session: dict) -> None:
    password = message.text.strip()
    try:
        await message.delete()
    except Exception:
        pass

    if len(password) < 4:
        await message.answer("❌ Password too short.", reply_markup=nav_only_keyboard())
        return

    data = await state.get_data()
    await state.clear()

    result = await add_teacher(
        org_id=user_session["org_id"],
        owner_id=user_session["user_id"],
        teacher_id=data["tch_id"],
        name=data["name"],
        subjects=data["subjects"],
        assigned_classes=data["classes"],
        phone=data["phone"],
        password=password,
    )
    await message.answer(result["message"], reply_markup=nav_only_keyboard())
