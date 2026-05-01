# api/auth.py
import hashlib
import hmac
import urllib.parse
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from config.config import settings
from database.repositories.user_repo import UserRepository
from core.security import create_user_session, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

class TelegramAuthRequest(BaseModel):
    init_data: str

def validate_telegram_data(init_data: str, bot_token: str) -> dict:
    """Validates the initData string received from Telegram TMA."""
    parsed_data = dict(urllib.parse.parse_qsl(init_data))
    
    if "hash" not in parsed_data:
        raise HTTPException(status_code=400, detail="Missing hash in initData")
    
    hash_value = parsed_data.pop("hash")
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash != hash_value:
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")
        
    return json.loads(parsed_data.get("user", "{}"))

@router.post("/telegram")
async def authenticate_telegram_user(request: TelegramAuthRequest):
    """Verifies Telegram user and returns role, tier, and JWT token."""
    try:
        tg_user = validate_telegram_data(request.init_data, settings.BOT_TOKEN)
        telegram_id = tg_user.get("id")
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="User ID not found in payload")

        # Use the clean repository method
        user_record = await UserRepository.get_tma_auth_profile(telegram_id)

        if not user_record:
            raise HTTPException(status_code=404, detail="User not registered or institute inactive.")

        # Create standard session payload
        session_payload = await create_user_session(
            user_id=user_record['user_id'],
            org_id=user_record['org_id'],
            role=user_record['role'],
            telegram_id=telegram_id
        )
        
        # Generate JWT Token for Mini App
        jwt_token = create_access_token(session_payload)

        return {
            "token": jwt_token,
            "user_id": user_record['user_id'],
            "name": user_record['name'],
            "role": user_record['role'],
            "org_id": user_record['org_id'],
            "coaching_name": user_record['org_name'],
            "tier": user_record['plan_type'] # Drives the "Go/Pro/Max" UI logic
        }
            
    except HTTPException:
        # Re-raise known HTTP exceptions so the exact status code reaches the frontend
        raise
    except Exception as e:
        logger.error(f"TMA Auth Error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
        
