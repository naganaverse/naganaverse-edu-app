"""
database/models/test_model.py
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class Test:
    org_id: str
    test_name: str
    class_name: str
    subject_name: str
    teacher_id: str
    topic: Optional[str] = None
    test_date: Optional[date] = None
    total_marks: int = 0
    test_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Test":
        return cls(
            test_id=str(record.get("test_id", "")),
            org_id=record["org_id"],
            test_name=record["test_name"],
            class_name=record["class_name"],
            subject_name=record["subject_name"],
            topic=record.get("topic"),
            teacher_id=record["teacher_id"],
            test_date=record.get("test_date"),
            total_marks=record.get("total_marks", 0),
            created_at=record.get("created_at"),
        )


@dataclass
class TestQuestion:
    test_id: str
    question_text: str
    correct_answer: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    marks: int = 1
    id: Optional[str] = None

    @classmethod
    def from_record(cls, record: dict) -> "TestQuestion":
        return cls(
            id=str(record.get("id", "")),
            test_id=str(record["test_id"]),
            question_text=record["question_text"],
            option_a=record.get("option_a"),
            option_b=record.get("option_b"),
            option_c=record.get("option_c"),
            option_d=record.get("option_d"),
            correct_answer=record["correct_answer"],
            marks=record.get("marks", 1),
        )


@dataclass
class TestResult:
    org_id: str
    test_id: str
    student_id: str
    marks: Decimal
    result_id: Optional[str] = None
    submitted_at: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "TestResult":
        return cls(
            result_id=str(record.get("result_id", "")),
            org_id=record["org_id"],
            test_id=str(record["test_id"]),
            student_id=record["student_id"],
            marks=record.get("marks", 0),
            submitted_at=record.get("submitted_at"),
        )
