"""
database/models/announcement_model.py
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Announcement:
    org_id: str
    message: str
    created_by: str
    target_class: Optional[str] = None  # None = all classes
    announcement_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Announcement":
        return cls(
            announcement_id=str(record.get("announcement_id", "")),
            org_id=record["org_id"],
            target_class=record.get("target_class"),
            message=record["message"],
            created_by=record["created_by"],
            created_at=record.get("created_at"),
        )
