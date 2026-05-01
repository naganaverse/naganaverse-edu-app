"""
handlers/student/resources_handler.py — PATCHED
─────────────────────────────────────────────────────────────
Fix: Smart delivery for Images vs Documents
Logic: Uses file_type stored in FSM to choose correct Telegram method.
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from core.filters import IsStudent
from core.loader import bot
from services.resource_service import get_resources
from keyboards.student_kb import (
    subject_select_keyboard,
    resource_type_keyboard,
)
from keyboards.common_kb import nav_only_keyboard, nav_row

router = Router()
router.callback_query.filter(IsStudent())


class ResourcesFSM(StatesGroup):
    select_subject = State()
    select_type    = State()
    view_files     = State()


# ── Entry ─────────────────────────────────────────────────

@router.callback_query(F.data.in_({"student:resources", "student:resource_library"}))
async def cb_resources_start(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    await state.clear()

    subjects = user_session.get("subjects", [])
    if not subjects:
        await callback.message.edit_text(
            "📭 No subjects enrolled yet.\nContact your institution owner.",
            reply_markup=nav_only_keyboard(),
        )
        return

    await state.set_state(ResourcesFSM.select_subject)
    await callback.message.edit_text(
        "📚 <b>Resources</b>\n\nSelect a subject:",
        reply_markup=subject_select_keyboard(subjects, "res_subject"),
    )


# ── State 1: Subject selected ─────────────────────────────

@router.callback_query(ResourcesFSM.select_subject, F.data.startswith("res_subject:"))
async def cb_res_subject(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    subject_name = callback.data.split(":", 1)[1]

    if subject_name not in user_session.get("subjects", []):
        await callback.message.edit_text("❌ You are not enrolled in this subject.", reply_markup=nav_only_keyboard())
        await state.clear()
        return

    await state.update_data(subject_name=subject_name)
    await state.set_state(ResourcesFSM.select_type)

    await callback.message.edit_text(
        f"📚 <b>Resources</b>\n📖 Subject: <b>{subject_name}</b>\n\nSelect resource type:",
        reply_markup=resource_type_keyboard(),
    )


# ── State 2: Type selected (Now saves file_type) ──────────

@router.callback_query(ResourcesFSM.select_type, F.data.startswith("restype:"))
async def cb_res_type(callback: CallbackQuery, state: FSMContext, user_session: dict) -> None:
    await callback.answer()
    resource_type = callback.data.split(":", 1)[1]
    data          = await state.get_data()
    subject_name  = data["subject_name"]
    org_id        = user_session["org_id"]
    class_name    = user_session.get("class_name", "")

    result = await get_resources(
        org_id=org_id,
        class_name=class_name,
        subject_name=subject_name,
        resource_type=resource_type,
    )

    if not result["success"]:
        await callback.message.edit_text(result["message"], reply_markup=nav_only_keyboard())
        await state.clear()
        return

    resources = result["resources"]
    # 🛡️ IMPORTANT: We save 'file_type' here so we don't have to query DB again later
    await state.update_data(
        resource_type=resource_type,
        files={
            str(r.resource_id): {
                "resource_id": str(r.resource_id),
                "file_url":    r.file_url,
                "file_name":   r.file_name,
                "file_type":   getattr(r, 'file_type', 'document'), # Safeguard
                "subject_name": r.subject_name,
                "resource_type": r.resource_type,
            }
            for r in resources
        },
    )
    await state.set_state(ResourcesFSM.view_files)

    rows = []
    for r in resources:
        icon = "🖼" if getattr(r, 'file_type', '') == "image" else "📄"
        label = r.file_name or f"File {str(r.resource_id)[:8]}"
        rows.append([InlineKeyboardButton(text=f"{icon} {label}", callback_data=f"res_file:{r.resource_id}")])
    
    rows.append(nav_row())
    await callback.message.edit_text(result["header"], reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ── State 3: File tapped → SMART DELIVERY ────────────────

@router.callback_query(ResourcesFSM.view_files, F.data.startswith("res_file:"))
async def cb_res_send_file(callback: CallbackQuery, state: FSMContext) -> None:
    # Use callback.answer() without text first to clear the loading state
    await callback.answer()
    
    resource_id = callback.data.split(":", 1)[1]
    data        = await state.get_data()
    files       = data.get("files", {})
    resource    = files.get(resource_id)

    if not resource:
        await callback.message.answer("❌ File not found. It may have been deleted.", reply_markup=nav_only_keyboard())
        return

    caption = (
        f"<b>{resource.get('file_name') or 'File'}</b>\n"
        f"📖 {resource.get('subject_name', '')} | "
        f"📁 {resource.get('resource_type', '').replace('_', ' ').title()}"
    )

    try:
        # 🛡️ THE FIX: Smart Delivery Logic
        if resource.get("file_type") == "image":
            await callback.message.answer_photo(
                photo=resource["file_url"],
                caption=caption
            )
        else:
            await callback.message.answer_document(
                document=resource["file_url"],
                caption=caption
            )
    except Exception as e:
        logger.error(f"Failed to send resource {resource_id}: {e}")
        await callback.message.answer(
            "❌ Telegram could not send this file. The original message might have been deleted.",
            reply_markup=nav_only_keyboard()
  )
                      
