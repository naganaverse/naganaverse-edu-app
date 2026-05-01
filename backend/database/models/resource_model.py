"""
database/models/resource_model.py
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Resource:
    org_id: str
    class_name: str
    subject_name: str
    resource_type: str                  # notes|worksheet|pyq|important_questions|practice_sheet
    file_url: str
    uploaded_by: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    resource_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Resource":
        return cls(
            resource_id=str(record.get("resource_id", "")),
            org_id=record["org_id"],
            class_name=record["class_name"],
            subject_name=record["subject_name"],
            resource_type=record["resource_type"],
            file_name=record.get("file_name"),
            file_url=record["file_url"],
            file_type=record.get("file_type"),
            uploaded_by=record["uploaded_by"],
            created_at=record.get("created_at"),
        )
