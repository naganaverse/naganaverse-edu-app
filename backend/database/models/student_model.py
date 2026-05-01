"""
database/models/student_model.py
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Student:
    student_id: str
    org_id: str
    name: str
    class_name: str # We keep this name in Python to avoid keyword conflicts
    password_hash: str
    roll_number: Optional[int] = None
    subjects: List[str] = field(default_factory=list)
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    parent_phone: Optional[str] = None
    telegram_id: Optional[int] = None
    parent_telegram_id: Optional[int] = None
    account_status: str = "active"
    agreed_fee: int = 0
    current_due: int = 0
    id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Student":
        import json
        subjects = record.get("subjects", [])
        if isinstance(subjects, str):
            subjects = json.loads(subjects)
        return cls(
            id=str(record.get("id", "")),
            org_id=record["org_id"],
            student_id=record["student_id"],
            name=record["name"],
            # 🛡️ TRANSLATION: Map DB column 'class' to Python 'class_name'
            class_name=record.get("class", ""), 
            roll_number=record.get("roll_number"),
            subjects=subjects or [],
            father_name=record.get("father_name"),
            mother_name=record.get("mother_name"),
            parent_phone=record.get("parent_phone"),
            password_hash=record["password_hash"],
            telegram_id=record.get("telegram_id"),
            parent_telegram_id=record.get("parent_telegram_id"),
            account_status=record.get("account_status", "active"),
            agreed_fee=record.get("agreed_fee", 0),
            current_due=record.get("current_due", 0),
            created_at=record.get("created_at"),
        )
        
