"""
database/models/subscription_model.py
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Subscription:
    org_id: str
    plan: str                           # starter | enterprise
    start_date: date
    expiry_date: date
    status: str = "active"
    subscription_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Subscription":
        return cls(
            subscription_id=str(record.get("subscription_id", "")),
            org_id=record["org_id"],
            plan=record["plan"],
            start_date=record["start_date"],
            expiry_date=record["expiry_date"],
            status=record.get("status", "active"),
            created_at=record.get("created_at"),
        )

    @property
    def is_expired(self) -> bool:
        from datetime import date as d
        return self.expiry_date < d.today()
