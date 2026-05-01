"""
database/models/attendance_model.py
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass
class Attendance:
    org_id: str
    class_name: str
    subject_name: str
    teacher_id: str
    date: date
    present_count: int = 0
    absent_count: int = 0
    attendance_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Attendance":
        return cls(
            attendance_id=str(record.get("attendance_id", "")),
            org_id=record["org_id"],
            class_name=record["class_name"],
            subject_name=record["subject_name"],
            teacher_id=record["teacher_id"],
            date=record["date"],
            present_count=record.get("present_count", 0),
            absent_count=record.get("absent_count", 0),
            created_at=record.get("created_at"),
        )


@dataclass
class AttendanceDetail:
    attendance_id: str
    student_id: str
    status: str = "present"             # present | absent
    id: Optional[str] = None

    @classmethod
    def from_record(cls, record: dict) -> "AttendanceDetail":
        return cls(
            id=str(record.get("id", "")),
            attendance_id=str(record["attendance_id"]),
            student_id=record["student_id"],
            status=record.get("status", "present"),
        )
