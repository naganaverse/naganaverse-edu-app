import os
import shutil
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from database.repositories.resource_repo import ResourceRepository
from database.models.resource_model import Resource
from core.security import decode_access_token
from loguru import logger

router = APIRouter(prefix="/resources", tags=["Resources"])

# --- Security Dependency ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Extract and verify JWT token."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

def require_role(allowed_roles: List[str]):
    """Dependency factory for role-based access control."""
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return role_checker

# --- Models ---

class ResourceResponse(BaseModel):
    resource_id: str
    class_name: str
    subject_name: str
    resource_type: str
    file_name: str
    file_url: str
    file_type: str
    is_telegram_file: bool
    created_at: Optional[datetime]

# --- Repository & Config ---

_resource_repo = ResourceRepository()
UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"

# --- Helpers ---

def is_telegram_file_id(url: str) -> bool:
    """Check if the file_url is a Telegram file_id or a standard URL."""
    if url.startswith(("http://", "https://", "uploads/")):
        return False
    return True

# --- Routes ---

@router.get("/list", response_model=List[ResourceResponse])
async def list_resources(
    org_id: str,
    class_name: str,
    subject_name: str,
    resource_type: str = Query(..., description="notes|worksheet|pyq|important_questions|practice_sheet")
):
    """Fetch resources for a student."""
    try:
        resources = await _resource_repo.get_by_class_subject_type(
            org_id=org_id,
            class_name=class_name,
            subject_name=subject_name,
            resource_type=resource_type
        )
        
        result = []
        for r in resources:
            result.append({
                "resource_id": r.resource_id,
                "class_name": r.class_name,
                "subject_name": r.subject_name,
                "resource_type": r.resource_type,
                "file_name": r.file_name or "Unnamed File",
                "file_url": r.file_url,
                "file_type": r.file_type or "unknown",
                "is_telegram_file": is_telegram_file_id(r.file_url),
                "created_at": r.created_at
            })
            
        return result
    except Exception as e:
        logger.error(f"Error in list_resources: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/upload", response_model=ResourceResponse)
async def upload_resource(
    class_name: str = Form(...),
    subject_name: str = Form(...),
    resource_type: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["teacher", "owner"]))
):
    """
    Teacher/Owner only: Upload a new resource file.
    Saves to local 'uploads/' folder and records in DB.
    """
    try:
        # 1. Prepare file path
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        file_path = UPLOADS_DIR / safe_filename
        
        # 2. Save file locally
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Prepare DB record
        # Store a relative path for the file_url so the proxy can resolve it
        relative_url = f"uploads/{safe_filename}"
        file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else "file"
        
        resource_data = Resource(
            org_id=user["org_id"],
            class_name=class_name,
            subject_name=subject_name,
            resource_type=resource_type,
            file_name=file.filename,
            file_url=relative_url,
            file_type=file_extension,
            uploaded_by=user["user_id"]
        )
        
        # 4. Save to DB
        saved_resource = await _resource_repo.create(resource_data)
        
        if not saved_resource:
            # Cleanup file if DB insert fails
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=500, detail="Failed to save resource record to database")
            
        return {
            "resource_id": saved_resource.resource_id,
            "class_name": saved_resource.class_name,
            "subject_name": saved_resource.subject_name,
            "resource_type": saved_resource.resource_type,
            "file_name": saved_resource.file_name,
            "file_url": saved_resource.file_url,
            "file_type": saved_resource.file_type,
            "is_telegram_file": False,
            "created_at": saved_resource.created_at
        }
        
    except Exception as e:
        logger.error(f"Error in upload_resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))
