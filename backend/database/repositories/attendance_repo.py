"""
database/repositories/attendance_repo.py
Attendance + AttendanceDetails — core engine queries.
"""
from datetime import date
from typing import Dict, List, Optional, Tuple
from loguru import logger

from database.connection import get_pool
from database.models.attendance_model import Attendance, AttendanceDetail


class AttendanceRepository:

    async def create_session(self, a: Attendance) -> Optional[Attendance]:
        """Create the attendance header record for a class+subject+date."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO attendance
                        (org_id, class_name, subject_name, teacher_id, date, present_count, absent_count)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    ON CONFLICT (org_id, class_name, subject_name, date)
                    DO UPDATE SET present_count = EXCLUDED.present_count,
                                  absent_count  = EXCLUDED.absent_count
                    RETURNING *
                    """,
                    a.org_id, a.class_name, a.subject_name, a.teacher_id,
                    a.date, a.present_count, a.absent_count,
                )
                return Attendance.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error creating attendance session for org {a.org_id}: {e}")
            return None

    async def save_details(self, attendance_id: str, details: List[AttendanceDetail]) -> None:
        """Bulk-insert attendance details for all students."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO attendance_details (attendance_id, student_id, status)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    [(attendance_id, d.student_id, d.status) for d in details],
                )
        except Exception as e:
            logger.error(f"DB Error saving attendance details for session {attendance_id}: {e}")

    async def get_student_attendance(self, student_id: str, org_id: str) -> List[dict]:
        """
        Returns per-subject attendance percentage for a student.
        Used by student dashboard attendance view.
        """
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        a.subject_name,
                        COUNT(*) AS total_classes,
                        SUM(CASE WHEN ad.status = 'present' THEN 1 ELSE 0 END) AS present_count
                    FROM attendance_details ad
                    JOIN attendance a ON a.attendance_id = ad.attendance_id
                    WHERE ad.student_id = $1 AND a.org_id = $2
                    GROUP BY a.subject_name
                    ORDER BY a.subject_name
                    """,
                    student_id, org_id,
                )
                result = []
                for r in rows:
                    total = r["total_classes"] or 0
                    present = r["present_count"] or 0
                    pct = round((present / total * 100), 1) if total > 0 else 0.0
                    result.append({
                        "subject_name": r["subject_name"],
                        "total_classes": total,
                        "present_count": present,
                        "absent_count": total - present,
                        "percentage": pct,
                    })
                return result
        except Exception as e:
            logger.error(f"DB Error fetching student attendance for {student_id} in org {org_id}: {e}")
            return []

    async def get_class_attendance_today(self, org_id: str, class_name: str, subject_name: str) -> Optional[Attendance]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM attendance
                    WHERE org_id = $1 AND class_name = $2
                      AND subject_name = $3 AND date = CURRENT_DATE
                    """,
                    org_id, class_name, subject_name,
                )
                return Attendance.from_record(dict(row)) if row else None
        except Exception as e:
            logger.error(f"DB Error fetching class attendance today for org {org_id}: {e}")
            return None

    async def get_unmarked_classes_today(self, org_id: str) -> List[dict]:
        """
        Used by scheduler: find classes where attendance NOT marked today.
        Returns list of {class_name, subject_name, teacher_id}.
        """
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT s.class_name, sub.subject_name, t.teacher_id, t.telegram_id
                    FROM students s
                    CROSS JOIN subjects sub
                    JOIN teachers t ON t.org_id = $1
                    WHERE s.org_id = $1
                      AND sub.org_id = $1
                      AND NOT EXISTS (
                          SELECT 1 FROM attendance a
                          WHERE a.org_id = $1
                            AND a.class_name = s.class_name
                            AND a.subject_name = sub.subject_name
                            AND a.date = CURRENT_DATE
                      )
                    LIMIT 50
                    """,
                    org_id,
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching unmarked classes today for org {org_id}: {e}")
            return []

    async def get_history_by_teacher(self, teacher_id: str, org_id: str, limit: int = 20) -> List[Attendance]:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM attendance
                    WHERE teacher_id = $1 AND org_id = $2
                    ORDER BY date DESC LIMIT $3
                    """,
                    teacher_id, org_id, limit,
                )
                return [Attendance.from_record(dict(r)) for r in rows]
        except Exception as e:
            logger.error(f"DB Error fetching attendance history for teacher {teacher_id}: {e}")
            return []

    async def get_class_report(self, org_id: str, class_name: str) -> List[dict]:
        """Owner attendance report: per-student percentage for a class."""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        s.student_id,
                        s.name,
                        s.parent_phone,
                        COUNT(ad.id) AS total,
                        SUM(CASE WHEN ad.status = 'present' THEN 1 ELSE 0 END) AS present
                    FROM students s
                    LEFT JOIN attendance_details ad ON ad.student_id = s.student_id
                    LEFT JOIN attendance a ON a.attendance_id = ad.attendance_id
                                          AND a.org_id = $1
                                          AND a.class_name = $2
                    WHERE s.org_id = $1 AND s.class = $2
                    GROUP BY s.student_id, s.name, s.parent_phone
                    ORDER BY present DESC
                    """,
                    org_id, class_name,
                )
                result = []
                for r in rows:
                    total = r["total"] or 0
                    present = r["present"] or 0
                    result.append({
                        "student_id": r["student_id"],
                        "name": r["name"],
                        "parent_phone": r["parent_phone"],
                        "total": total,
                        "present": present,
                        "percentage": round((present / total * 100), 1) if total > 0 else 0.0,
                    })
                return result
        except Exception as e:
            logger.error(f"DB Error fetching class report for {class_name} in org {org_id}: {e}")
            return []
            
