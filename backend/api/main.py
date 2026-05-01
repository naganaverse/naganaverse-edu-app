import sys
from pathlib import Path

# Add the project root to sys.path so we can import database and services
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from loguru import logger

from database.connection import init_pool, close_pool
from services.attendance_service import take_attendance
from api.routes import auth, resources, analytics

app = FastAPI(title="Naganaverse Education API")

# --- Include Routes ---
app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(analytics.router)

# --- Models ---

class AttendanceSubmitRequest(BaseModel):
    org_id: str
    class_name: str
    subject_name: str
    teacher_id: str
    absent_student_ids: List[str]
    attendance_date: Optional[date] = None

# --- Lifecycle ---

@app.on_event("startup")
async def startup():
    await init_pool()
    logger.info("FastAPI started and DB pool initialized.")

@app.on_event("shutdown")
async def shutdown():
    await close_pool()
    logger.info("FastAPI shut down and DB pool closed.")

# --- Routes ---

@app.post("/attendance/submit", tags=["Attendance"])
async def submit_attendance(req: AttendanceSubmitRequest):
    """
    Mark attendance for a class.
    Follows the 'Default-Present' logic from the Telegram Bot.
    """
    try:
        result = await take_attendance(
            org_id=req.org_id,
            class_name=req.class_name,
            subject_name=req.subject_name,
            teacher_id=req.teacher_id,
            absent_student_ids=req.absent_student_ids,
            attendance_date=req.attendance_date or date.today()
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
            
        return {
            "status": "success",
            "data": {
                "present_count": result.get("present_count"),
                "absent_count": result.get("absent_count"),
                "total": result.get("total"),
                "message": result.get("message")
            }
        }
    except Exception as e:
        logger.error(f"Error in submit_attendance: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
