from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from loguru import logger

from api.routes.resources import require_role
from database.repositories.fee_repo import FeeRepository
from database.repositories.attendance_repo import AttendanceRepository

router = APIRouter(prefix="/owner", tags=["Owner Analytics"])

# --- Repositories ---
_fee_repo = FeeRepository()
_attendance_repo = AttendanceRepository()

# --- Routes ---

@router.get("/revenue")
async def get_revenue_stats(user: dict = Depends(require_role(["owner"]))):
    """
    Owner only: Get the institute's revenue stats.
    Sums up 'collected_fees' from the fee_transactions table.
    """
    try:
        stats = await _fee_repo.get_org_financial_stats(user["org_id"])
        return {
            "status": "success",
            "data": {
                "total_collected": stats["total_collected"],
                "total_pending": stats["total_pending"]
            }
        }
    except Exception as e:
        logger.error(f"Error in get_revenue_stats: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/attendance-stats")
async def get_attendance_analytics(user: dict = Depends(require_role(["owner"]))):
    """
    Owner only: Get the average attendance percentage for each class.
    Calculates stats across all subjects for every class in the organization.
    """
    try:
        # We'll use a custom query since the repo doesn't have a direct 'average per class' helper
        from database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Query to calculate average attendance % per class
            # Formula: (SUM(present_count) / SUM(present_count + absent_count)) * 100
            rows = await conn.fetch(
                """
                SELECT 
                    class_name,
                    ROUND(AVG((present_count::float / NULLIF(present_count + absent_count, 0)) * 100)::numeric, 1) as avg_attendance
                FROM attendance
                WHERE org_id = 
                GROUP BY class_name
                ORDER BY avg_attendance DESC
                """,
                user["org_id"]
            )
            
            result = [
                {"class_name": r["class_name"], "average_percentage": float(r["avg_attendance"] or 0)}
                for r in rows
            ]
            
            return {
                "status": "success",
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Error in get_attendance_analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/stats")
async def get_owner_dashboard_stats(user: dict = Depends(require_role(["owner"]))):
    """
    Get aggregated high-fidelity dashboard stats for the owner.
    Returns: total_revenue, total_students, avg_attendance, pending_fees
    """
    try:
        # For now, returning high-fidelity demo numbers as defaults
        # In a real scenario, we'd fetch these from the repositories
        return {
            "status": "success",
            "data": {
                "total_revenue": "₹12.5k",
                "total_students": 156,
                "avg_attendance": "92%",
                "pending_fees": "₹2.1L"
            }
        }
    except Exception as e:
        logger.error(f"Error in get_owner_dashboard_stats: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
