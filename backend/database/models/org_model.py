"""
database/models/org_model.py
─────────────────────────────────
Organization / Institution dataclass model.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Organization:
    org_id: str
    org_name: str
    owner_name: str
    status: str                          # pending | active | approved | rejected | suspended
    plan_type: str = "starter"
    phone: Optional[str] = None
    city: Optional[str] = None
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Organization":
        return cls(
            id=str(record.get("id", "")),
            org_id=record["org_id"],
            org_name=record["org_name"],
            owner_name=record["owner_name"],
            phone=record.get("phone"),
            city=record.get("city"),
            referral_code=record.get("referral_code"),
            referred_by=record.get("referred_by"),
            status=record["status"],
            plan_type=record.get("plan_type", "starter"),
            created_at=record.get("created_at"),
        )

    @property
    def is_active(self) -> bool:
        return self.status in ("active", "approved")

    @property
    def is_suspended(self) -> bool:
        return self.status == "suspended"
