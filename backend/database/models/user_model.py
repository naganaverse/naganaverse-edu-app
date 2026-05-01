"""
database/models/user_model.py
─────────────────────────────────
Central user model (all roles share this for auth).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    user_id: str
    name: str
    role: str                            # student | teacher | owner | super_admin
    password_hash: str
    status: str = "active"
    org_id: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[int] = None
    failed_attempts: int = 0
    last_failed_attempt: Optional[datetime] = None
    account_locked_until: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "User":
        return cls(
            user_id=record["user_id"],
            org_id=record.get("org_id"),
            name=record["name"],
            role=record["role"],
            phone=record.get("phone"),
            telegram_id=record.get("telegram_id"),
            password_hash=record["password_hash"],
            status=record.get("status", "active"),
            failed_attempts=record.get("failed_attempts", 0),
            last_failed_attempt=record.get("last_failed_attempt"),
            account_locked_until=record.get("account_locked_until"),
            created_at=record.get("created_at"),
        )

    @property
    def is_locked(self) -> bool:
        from datetime import timezone
        if self.account_locked_until:
            return datetime.now(timezone.utc) < self.account_locked_until
        return False

    @property
    def is_active(self) -> bool:
        return self.status == "active"
