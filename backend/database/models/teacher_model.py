"""
database/models/teacher_model.py
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Teacher:
    teacher_id: str
    org_id: str
    name: str
    password_hash: str
    subjects: List[str] = field(default_factory=list)
    assigned_classes: List[str] = field(default_factory=list)
    telegram_id: Optional[int] = None
    phone: Optional[str] = None
    account_status: str = "active"
    id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Teacher":
        import json
        subjects = record.get("subjects", [])
        classes = record.get("assigned_classes", [])
        if isinstance(subjects, str):
            subjects = json.loads(subjects)
        if isinstance(classes, str):
            classes = json.loads(classes)
        return cls(
            id=str(record.get("id", "")),
            org_id=record["org_id"],
            teacher_id=record["teacher_id"],
            name=record["name"],
            subjects=subjects or [],
            assigned_classes=classes or [],
            password_hash=record["password_hash"],
            telegram_id=record.get("telegram_id"),
            phone=record.get("phone"),
            account_status=record.get("account_status", "active"),
            created_at=record.get("created_at"),
        )
