# -*- coding: utf-8 -*-
"""Exam models."""

import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from backend.models import Base


class ExamMode(str, enum.Enum):
    REAL_EXAM = "real_exam"
    RANDOM = "random"
    CHAPTER = "chapter"
    WRONG_QUESTIONS = "wrong_questions"


class ExamStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMEOUT = "timeout"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    mode = Column(String(32), nullable=False, index=True)
    year = Column(Integer)
    month = Column(Integer)
    duration = Column(Integer, default=150, nullable=False)
    total_score = Column(Integer, default=100, nullable=False)
    config = Column(JSON)
    question_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Exam {self.id} - {self.name}>"


class ExamSession(Base):
    __tablename__ = "exam_sessions"
    __table_args__ = (
        Index("ix_exam_sessions_user_status", "user_id", "status"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    status = Column(String(32), default=ExamStatus.IN_PROGRESS.value, nullable=False, index=True)
    ai_grading_status = Column(String(32))  # pending / completed / confirmed / user_modified
    answers = Column(JSON, default=dict)
    score = Column(Integer)
    correct_count = Column(Integer)
    total_count = Column(Integer)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    submitted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ExamSession {self.session_id}>"


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_wrong_questions_user_question"),
        Index("ix_wrong_questions_user_mastered_time", "user_id", "is_mastered", "last_wrong_at"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    session_id = Column(String(100), index=True)
    user_answer = Column(Text)
    wrong_count = Column(Integer, default=1, nullable=False)
    is_mastered = Column(Boolean, default=False, nullable=False)
    tags = Column(JSON)
    note = Column(Text)
    last_wrong_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<WrongQuestion U{self.user_id}-Q{self.question_id}>"


class ExamResult(Base):
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ExamResult session={self.session_id}>"
