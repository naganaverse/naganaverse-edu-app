"""
handlers/owner/add_student_handler.py
─────────────────────────────────────────────────────────────
FSM States:
  ADD_STD_NAME        → student name
  ADD_STD_CLASS       → class (e.g. Class 10)
  ADD_STD_ROLL        → roll number (numeric)
  ADD_STD_SUBJECTS    → comma-separated subjects
  ADD_STD_FATHER      → father name
  ADD_STD_MOTHER      → mother name
  ADD_STD_PHONE       → parent phone
  ADD_STD_ID          → owner creates student_id (e.g. STD102)
  ADD_STD_PASSWORD    → owner creates password

Validation:
  - student_id globally unique (checked before save)
  - roll_number must be numeric
  - phone minimum 10 digits
  - Max 1000 students per org enforced in owner_service
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsOwner
from services.owner_service import add_student
from keyboards.owner_kb import students_menu_keyboard
from keyboards.common_kb import nav_only_keyboard

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())


class AddStudentFSM(StatesGroup):
    name     = State()
    cls      = State()
    roll     = State()
    subjects = State()
    father   = State()
    mother   = State()
    phone    = State()
    std_id   = State()
    password = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data == "owner:student_add")
async def cb_add_student_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(AddStudentFSM.name)
    await callback.message.edit_text(
        "➕ <b>Add Student</b>\n\n"
        "Step 1/9 — Enter <b>Student Name</b>:\n"
        "<i>Example: Aakash Sharma</i>",
        reply_markup=nav_only_keyboard(),
    )


# ── States ────────────────────────────────────────────────

@router.message(AddStudentFSM.name)
async def msg_std_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Name too short.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(name=name)
    await state.set_state(AddStudentFSM.cls)
    await message.answer(
        f"✅ Name: <b>{name}</b>\n\n"
        "Step 2/9 — Enter <b>Class</b>:\n"
        "<i>Example: Class 10  or  11  or  12</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.cls)
async def msg_std_class(message: Message, state: FSMContext) -> None:
    cls = message.text.strip()
    await state.update_data(cls=cls)
    await state.set_state(AddStudentFSM.roll)
    await message.answer(
        f"✅ Class: <b>{cls}</b>\n\n"
        "Step 3/9 — Enter <b>Roll Number</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.roll)
async def msg_std_roll(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("❌ Roll number must be numeric.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(roll=int(raw))
    await state.set_state(AddStudentFSM.subjects)
    await message.answer(
        f"✅ Roll No: <b>{raw}</b>\n\n"
        "Step 4/9 — Enter <b>Subjects</b>:\n"
        "<i>Comma-separated. Example: Physics, Chemistry, Math</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.subjects)
async def msg_std_subjects(message: Message, state: FSMContext) -> None:
    subjects = [s.strip() for s in message.text.split(",") if s.strip()]
    if not subjects:
        await message.answer("❌ Enter at least one subject.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(subjects=subjects)
    await state.set_state(AddStudentFSM.father)
    await message.answer(
        f"✅ Subjects: <b>{', '.join(subjects)}</b>\n\n"
        "Step 5/9 — Enter <b>Father's Name</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.father)
async def msg_std_father(message: Message, state: FSMContext) -> None:
    await state.update_data(father=message.text.strip())
    await state.set_state(AddStudentFSM.mother)
    await message.answer(
        "Step 6/9 — Enter <b>Mother's Name</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.mother)
async def msg_std_mother(message: Message, state: FSMContext) -> None:
    await state.update_data(mother=message.text.strip())
    await state.set_state(AddStudentFSM.phone)
    await message.answer(
        "Step 7/9 — Enter <b>Parent Phone Number</b>:",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.phone)
async def msg_std_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip().replace(" ", "")
    if not phone.lstrip("+").isdigit() or len(phone) < 10:
        await message.answer("❌ Invalid phone number.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(phone=phone)
    await state.set_state(AddStudentFSM.std_id)
    await message.answer(
        "Step 8/9 — Create <b>Student ID</b>:\n"
        "<i>Example: STD001, STD102</i>\n\n"
        "⚠️ This ID must be unique across the system.",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.std_id)
async def msg_std_id(message: Message, state: FSMContext) -> None:
    std_id = message.text.strip().upper()
    if len(std_id) < 3:
        await message.answer("❌ ID too short. Min 3 characters.", reply_markup=nav_only_keyboard())
        return
    await state.update_data(std_id=std_id)
    await state.set_state(AddStudentFSM.password)
    await message.answer(
        f"✅ Student ID: <code>{std_id}</code>\n\n"
        "Step 9/9 — Create <b>Password</b>:\n"
        "<i>Min 4 characters. Share this with the student.</i>",
        reply_markup=nav_only_keyboard(),
    )


@router.message(AddStudentFSM.password)
async def msg_std_password(message: Message, state: FSMContext, user_session: dict) -> None:
    password = message.text.strip()

    # Delete password message for security
    try:
        await message.delete()
    except Exception:
        pass

    if len(password) < 4:
        await message.answer("❌ Password too short. Min 4 characters.", reply_markup=nav_only_keyboard())
        return

    data = await state.get_data()
    await state.clear()

    result = await add_student(
        org_id=user_session["org_id"],
        owner_id=user_session["user_id"],
        student_id=data["std_id"],
        name=data["name"],
        class_name=data["cls"],
        roll_number=data["roll"],
        subjects=data["subjects"],
        father_name=data["father"],
        mother_name=data["mother"],
        parent_phone=data["phone"],
        password=password,
    )

    if result["success"]:
        parent_id  = f"PAR_{data['std_id']}"
        parent_pwd = data["phone"][-6:]   # last 6 digits of parent phone
        await message.answer(
            result["message"] + f"\n\n"
            f"👨‍👩‍👧 <b>Parent Access Details:</b>\n"
            f"🆔 Parent ID: <code>{parent_id}</code>\n"
            f"🔑 Password: <code>{parent_pwd}</code>\n\n"
            f"Share these with the parent.\n"
            f"Parent can login at @NOTESVERSEBOT → Login as Parent\n\n"
            f"<i>Password is last 6 digits of parent phone number.</i>",
            reply_markup=nav_only_keyboard(),
        )
    else:
        await message.answer(result["message"], reply_markup=nav_only_keyboard())
