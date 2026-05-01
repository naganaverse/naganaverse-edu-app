from fastapi import APIRouter, Depends, HTTPException
from database.repositories.student_repo import StudentRepository
from database.repositories.homework_repo import HomeworkRepository
from core.security import decode_access_token # You'll need a dependency for JWT
from typing import List

router = APIRouter(prefix="/student", tags=["Student OS"])

# Example Dependency to protect routes
async def get_current_user(token: str):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid session")
    return payload

@router.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    repo = StudentRepository()
    profile = await repo.get_student_profile(user['telegram_id'])
    return profile

@router.get("/homework/today")
async def get_today_homework(user=Depends(get_current_user)):
    repo = HomeworkRepository()
    # Logic to fetch homework for the user's class from homework_repo
    homework = await repo.get_today_homework(user['org_id'], user['class'])
    return homework
