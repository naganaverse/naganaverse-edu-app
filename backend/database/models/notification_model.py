"""
database/models/notification_model.py
Parent notification model.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ParentNotification:
    org_id: str
    student_id: str
    parent_phone: str
    notification_type: str              # test_result|attendance_report|absence_alert|announcement
    message: str
    notification_id: Optional[str] = None
    sent_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "ParentNotification":
        return cls(
            notification_id=str(record.get("notification_id", "")),
            org_id=record["org_id"],
            student_id=record["student_id"],
            parent_phone=record["parent_phone"],
            notification_type=record["notification_type"],
            message=record["message"],
            sent_at=record.get("sent_at"),
        )
