"""
database/models/security_model.py
Login attempts, audit logs, suspended accounts, bot activity.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class LoginAttempt:
    status: str                         # success | failed
    user_id: Optional[str] = None
    role: Optional[str] = None
    org_id: Optional[str] = None
    ip_address: Optional[str] = None
    attempt_id: Optional[str] = None
    attempt_time: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "LoginAttempt":
        return cls(
            attempt_id=str(record.get("attempt_id", "")),
            user_id=record.get("user_id"),
            role=record.get("role"),
            org_id=record.get("org_id"),
            ip_address=record.get("ip_address"),
            status=record["status"],
            attempt_time=record.get("attempt_time"),
        )


@dataclass
class AuditLog:
    event_type: str
    user_id: Optional[str] = None
    role: Optional[str] = None
    org_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    log_id: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "AuditLog":
        return cls(
            log_id=str(record.get("log_id", "")),
            event_type=record["event_type"],
            user_id=record.get("user_id"),
            role=record.get("role"),
            org_id=record.get("org_id"),
            details=record.get("details"),
            timestamp=record.get("timestamp"),
        )


@dataclass
class SuspendedAccount:
    user_id: str
    role: str
    org_id: Optional[str] = None
    reason: Optional[str] = None
    suspended_until: Optional[datetime] = None
    id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "SuspendedAccount":
        return cls(
            id=str(record.get("id", "")),
            user_id=record["user_id"],
            role=record["role"],
            org_id=record.get("org_id"),
            reason=record.get("reason"),
            suspended_until=record.get("suspended_until"),
            created_at=record.get("created_at"),
        )
