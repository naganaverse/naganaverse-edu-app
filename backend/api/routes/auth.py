from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from database.repositories.user_repo import UserRepository
from database.repositories.user_repo_security import LoginAttemptRepository
from core.security import verify_password, create_access_token
from loguru import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Models ---

class LoginRequest(BaseModel):
    org_id: str
    user_id: str
    password: str
    role: str  # student | teacher | owner | super_admin

class LoginResponse(BaseModel):
    status: str
    token: str
    user: dict

# --- Repositories ---

_user_repo = UserRepository()
_login_log = LoginAttemptRepository()

# --- Routes ---

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    """
    Authenticate user and return a JWT token.
    Validates against the existing 'users' table and password hashes.
    """
    ip_address = request.client.host
    
    # 1. Fetch User
    user = await _user_repo.get_by_user_id(req.user_id, req.org_id)
    
    if not user:
        await _login_log.log_attempt(req.user_id, req.role, req.org_id, "failed", ip_address)
        raise HTTPException(status_code=401, detail="Invalid Institute Code or User ID")

    # 2. Basic Security Checks
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is not active. Please contact administrator.")
    
    if user.is_locked:
        raise HTTPException(status_code=423, detail="Account is temporarily locked due to multiple failed attempts.")

    # 3. Verify Password
    if not verify_password(req.password, user.password_hash):
        await _user_repo.increment_failed_attempts(user.user_id)
        await _login_log.log_attempt(user.user_id, user.role, user.org_id, "failed", ip_address)
        raise HTTPException(status_code=401, detail="Invalid password")

    # 4. Success Logic
    await _user_repo.clear_failed_attempts(user.user_id)
    await _login_log.log_attempt(user.user_id, user.role, user.org_id, "success", ip_address)

    # 5. Generate Token
    payload = {
        "user_id": user.user_id,
        "org_id": user.org_id,
        "role": user.role,
        "name": user.name
    }
    token = create_access_token(payload)

    return {
        "status": "success",
        "token": token,
        "user": {
            "user_id": user.user_id,
            "org_id": user.org_id,
            "role": user.role,
            "name": user.name,
            "phone": user.phone
        }
    }
