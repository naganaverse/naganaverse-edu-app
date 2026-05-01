"""
database/models/homework_model.py
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Homework:
    org_id: str
    class_name: str
    subject_name: str
    teacher_id: str
    description: str
    date: date
    homework_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Homework":
        return cls(
            homework_id=str(record.get("homework_id", "")),
            org_id=record["org_id"],
            class_name=record["class_name"],
            subject_name=record["subject_name"],
            teacher_id=record["teacher_id"],
            description=record["description"],
            date=record["date"],
            created_at=record.get("created_at"),
        )
