"""
services/resource_service.py
─────────────────────────────────────────────────────────────
Content Library / Notes Engine.

Resource types: notes | worksheet | pyq | important_questions | practice_sheet

Files are stored via Telegram file_id (Telegram handles storage).
file_url stores the Telegram file_id for retrieval.
org_id + class + subject tagging ensures students only
see materials relevant to their batch.
─────────────────────────────────────────────────────────────
"""

from typing import List

from loguru import logger

from database.models.resource_model import Resource
from database.repositories.resource_repo import ResourceRepository
from database.repositories.user_repo_security import AuditLogRepository

_resource_repo = ResourceRepository()
_audit = AuditLogRepository()

VALID_RESOURCE_TYPES = {
    "notes", "worksheet", "pyq", "important_questions", "practice_sheet"
}

RESOURCE_TYPE_LABELS = {
    "notes": "📄 Notes",
    "worksheet": "📝 Worksheet",
    "pyq": "📋 PYQ",
    "important_questions": "⭐ Important Questions",
    "practice_sheet": "🔖 Practice Sheet",
}


async def upload_resource(
    org_id: str,
    class_name: str,
    subject_name: str,
    resource_type: str,
    file_url: str,           # Telegram file_id
    uploaded_by: str,        # teacher_id
    file_name: str = None,
    file_type: str = None,   # pdf | doc | image
) -> dict:
    """
    Save a resource upload with full metadata tagging.
    org_id + class + subject ensures strict batch isolation.
    """
    if resource_type not in VALID_RESOURCE_TYPES:
        return {
            "success": False,
            "message": f"❌ Invalid resource type: {resource_type}",
        }

    resource = Resource(
        org_id=org_id,
        class_name=class_name,
        subject_name=subject_name,
        resource_type=resource_type,
        file_url=file_url,
        uploaded_by=uploaded_by,
        file_name=file_name,
        file_type=file_type,
    )
    saved = await _resource_repo.create(resource)

    await _audit.log(
        "RESOURCE_UPLOADED",
        user_id=uploaded_by, role="teacher", org_id=org_id,
        details={
            "class": class_name, "subject": subject_name,
            "type": resource_type, "file": file_name,
        },
    )

    logger.info(
        f"Resource uploaded | org={org_id} | class={class_name} "
        f"| subject={subject_name} | type={resource_type}"
    )

    return {
        "success": True,
        "resource": saved,
        "message": (
            f"✅ <b>Upload Successful</b>\n\n"
            f"📚 Class: {class_name}\n"
            f"📖 Subject: {subject_name}\n"
            f"📁 Type: {RESOURCE_TYPE_LABELS.get(resource_type, resource_type)}\n"
            f"📄 File: {file_name or 'Uploaded'}"
        ),
    }


async def get_resources(
    org_id: str,
    class_name: str,
    subject_name: str,
    resource_type: str,
) -> dict:
    """
    Fetch resource list for a student.
    Returns list of resources with file_urls for Telegram delivery.
    """
    resources = await _resource_repo.get_by_class_subject_type(
        org_id, class_name, subject_name, resource_type
    )

    if not resources:
        return {
            "success": False,
            "message": (
                f"📭 No {RESOURCE_TYPE_LABELS.get(resource_type, resource_type)} "
                f"found for {subject_name} — {class_name}."
            ),
            "resources": [],
        }

    return {
        "success": True,
        "resources": resources,
        "count": len(resources),
        "header": (
            f"📁 <b>{RESOURCE_TYPE_LABELS.get(resource_type, resource_type)}</b>\n"
            f"📚 {class_name} | 📖 {subject_name}\n"
            f"📦 {len(resources)} file(s) found:"
        ),
    }


async def get_teacher_uploads(org_id: str, teacher_id: str) -> str:
    """List all files uploaded by a specific teacher."""
    resources = await _resource_repo.get_by_teacher(org_id, teacher_id)

    if not resources:
        return "📭 You have no uploaded files yet."

    lines = [f"📂 <b>Your Uploads</b> ({len(resources)} files)\n"]
    for r in resources:
        label = RESOURCE_TYPE_LABELS.get(r.resource_type, r.resource_type)
        lines.append(
            f"• {label} | {r.class_name} | {r.subject_name}\n"
            f"  📄 {r.file_name or 'File'} — {r.resource_id[:8]}...\n"
        )

    return "\n".join(lines)


async def delete_resource(
    resource_id: str,
    org_id: str,
    teacher_id: str,
) -> dict:
    """
    Teachers can only delete their own uploaded files.
    Ownership enforced at repo level via uploaded_by check.
    """
    deleted = await _resource_repo.delete(resource_id, org_id, teacher_id)

    if not deleted:
        return {
            "success": False,
            "message": "❌ File not found or you don't have permission to delete it.",
        }

    await _audit.log(
        "RESOURCE_DELETED",
        user_id=teacher_id, role="teacher", org_id=org_id,
        details={"resource_id": resource_id},
    )

    return {"success": True, "message": "🗑 File deleted successfully."}
