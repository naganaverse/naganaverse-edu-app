"""
handlers/teacher/resource_handler.py
─────────────────────────────────────────────────────────────
FSM: NOTES_SELECT_CLASS → NOTES_SELECT_SUBJECT
     → NOTES_SELECT_TYPE → NOTES_UPLOAD_FILE

Stores: Telegram file_id as file_url (Telegram handles storage).
Security: Teachers can only delete their own uploads.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.filters import IsTeacher
from services.resource_service import upload_resource, get_teacher_uploads, delete_resource
from services.teacher_service import get_assigned_classes, get_assigned_subjects
from keyboards.teacher_kb import (
    class_select_keyboard, subject_select_keyboard,
    manage_notes_keyboard, resource_type_keyboard,
)
from keyboards.common_kb import nav_only_keyboard
from database.repositories.resource_repo import ResourceRepository

router = Router()
router.message.filter(IsTeacher())
router.callback_query.filter(IsTeacher())

_resource_repo = ResourceRepository()


class NotesFSM(StatesGroup):
    select_class   = State()
    select_subject = State()
    select_type    = State()
    upload_file    = State()
    awaiting_delete = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data.in_({"teacher:manage_notes", "teacher:resource_library"}))
async def cb_manage_notes(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📂 <b>Manage Notes</b>\n\nChoose an option:",
        reply_markup=manage_notes_keyboard(),
    )


# ── Upload Flow ───────────────────────────────────────────

@router.callback_query(F.data == "notes:upload")
async def cb_upload_start(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    classes = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if not classes:
        await callback.message.edit_text("❌ No classes assigned.", reply_markup=nav_only_keyboard())
        return
    await state.set_state(NotesFSM.select_class)
    await callback.message.edit_text(
        "⬆️ <b>Upload Notes</b>\n\nStep 1 — Select Class:",
        reply_markup=class_select_keyboard(classes, "notes_class"),
    )


@router.callback_query(NotesFSM.select_class, F.data.startswith("notes_class:"))
async def cb_notes_class(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    assigned = await get_assigned_classes(user_session["user_id"], user_session["org_id"])
    if class_name not in assigned:
        await callback.message.edit_text("❌ Not your class.", reply_markup=nav_only_keyboard())
        await state.clear()
        return
    subjects = await get_assigned_subjects(user_session["user_id"], user_session["org_id"])
    await state.update_data(class_name=class_name)
    await state.set_state(NotesFSM.select_subject)
    await callback.message.edit_text(
        f"⬆️ <b>Upload Notes</b>\n📚 {class_name}\n\nStep 2 — Select Subject:",
        reply_markup=subject_select_keyboard(subjects, "notes_subject"),
    )


@router.callback_query(NotesFSM.select_subject, F.data.startswith("notes_subject:"))
async def cb_notes_subject(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    requested_subject = callback.data.split(":", 1)[1]
    
    # 🛡️ SECURITY GUARD: Re-verify against the teacher's actual assigned subjects
    # Fetching directly via the service function to be 100% consistent with Step 1
    allowed_subjects = await get_assigned_subjects(user_session["user_id"], user_session["org_id"])
    
    if requested_subject not in allowed_subjects:
        # Bounce them with an alert pop-up directly on their screen
        await callback.answer(
            "🚫 Unauthorized! You are not assigned to upload materials for this subject.", 
            show_alert=True
        )
        return

    # If they pass the guardrail, update the FSM and proceed
    await callback.answer()
    await state.update_data(subject_name=requested_subject)
    await state.set_state(NotesFSM.select_type)
    
    data = await state.get_data()
    await callback.message.edit_text(
        f"⬆️ <b>Upload Notes</b>\n📚 {data['class_name']} | 📖 {requested_subject}\n\n"
        "Step 3 — Select Resource Type:",
        reply_markup=resource_type_keyboard("upload_type"),
    )


@router.callback_query(NotesFSM.select_type, F.data.startswith("upload_type:"))
async def cb_notes_type(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    resource_type = callback.data.split(":", 1)[1]
    await state.update_data(resource_type=resource_type)
    await state.set_state(NotesFSM.upload_file)
    data = await state.get_data()
    await callback.message.edit_text(
        f"⬆️ <b>Upload Notes</b>\n"
        f"📚 {data['class_name']} | 📖 {data['subject_name']}\n"
        f"📁 Type: {resource_type.replace('_', ' ').title()}\n\n"
        "Step 4 — Send your file (PDF / DOC / Image):",
        reply_markup=nav_only_keyboard(),
    )


@router.message(NotesFSM.upload_file, F.document | F.photo)
async def msg_file_upload(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    data = await state.get_data()

    # Extract file info from document or photo
    if message.document:
        file_id   = message.document.file_id
        file_name = message.document.file_name or "Document"
        file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "doc"
    elif message.photo:
        file_id   = message.photo[-1].file_id
        file_name = "Image"
        file_type = "image"
    else:
        await message.answer("❌ Please send a PDF, DOC, or image file.")
        return

    result = await upload_resource(
        org_id=user_session["org_id"],
        class_name=data["class_name"],
        subject_name=data["subject_name"],
        resource_type=data["resource_type"],
        file_url=file_id,
        uploaded_by=user_session["user_id"],
        file_name=file_name,
        file_type=file_type,
    )
    await state.clear()
    await message.answer(result["message"], reply_markup=nav_only_keyboard())


@router.message(NotesFSM.upload_file)
async def msg_non_file(message: Message) -> None:
    await message.answer(
        "❌ Please send a file (PDF, DOC, or image).",
        reply_markup=nav_only_keyboard(),
    )


# ── View Uploads ──────────────────────────────────────────

@router.callback_query(F.data == "notes:view")
async def cb_view_uploads(callback: CallbackQuery, user_session: dict) -> None:
    await callback.answer()
    text = await get_teacher_uploads(user_session["org_id"], user_session["user_id"])
    await callback.message.edit_text(text, reply_markup=nav_only_keyboard())


# ── Delete File ───────────────────────────────────────────

@router.callback_query(F.data == "notes:delete")
async def cb_delete_start(
    callback: CallbackQuery, state: FSMContext, user_session: dict
) -> None:
    await callback.answer()
    resources = await _resource_repo.get_by_teacher(
        user_session["org_id"], user_session["user_id"]
    )
    if not resources:
        await callback.message.edit_text(
            "📭 No uploaded files to delete.", reply_markup=nav_only_keyboard()
        )
        return

    lines = ["🗑 <b>Delete File</b>\n\nYour uploads:\n"]
    for r in resources:
        lines.append(
            f"🔑 <code>{r.resource_id}</code>\n"
            f"   📄 {r.file_name or 'File'} | {r.class_name} | {r.subject_name}\n"
        )
    lines.append("\nSend the <b>resource ID</b> to delete:")

    await state.set_state(NotesFSM.awaiting_delete)
    await callback.message.edit_text("\n".join(lines), reply_markup=nav_only_keyboard())


@router.message(NotesFSM.awaiting_delete)
async def msg_delete_id(
    message: Message, state: FSMContext, user_session: dict
) -> None:
    resource_id = message.text.strip()
    result = await delete_resource(
        resource_id=resource_id,
        org_id=user_session["org_id"],
        teacher_id=user_session["user_id"],
    )
    await state.clear()
    await message.answer(result["message"], reply_markup=nav_only_keyboard())
     
