# -*- coding: utf-8 -*-
"""Study plan models."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from backend.models import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam_date = Column(DateTime(timezone=True), nullable=False)
    daily_hours = Column(Float, nullable=False)
    subjects = Column(JSON, nullable=False)
    preferences = Column(JSON)
    user_context = Column(Text, nullable=True)
    plan_data = Column(JSON)
    status = Column(String(20), default="active", nullable=False, index=True)
    completion_rate = Column(Float, default=0.0, nullable=False)
    expected_pass_rate = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<StudyPlan {self.id} - U{self.user_id}>"


class DailyTask(Base):
    __tablename__ = "daily_tasks"
    __table_args__ = (
        UniqueConstraint("plan_id", "task_date", "subject_id", name="uq_daily_tasks_plan_date_subject"),
        Index("ix_daily_tasks_user_date", "user_id", "task_date"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_date = Column(DateTime(timezone=True), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    chapter_ids = Column(JSON)
    question_count = Column(Integer, default=0, nullable=False)
    video_ids = Column(JSON)
    review_points = Column(JSON)
    is_completed = Column(Boolean, default=False, nullable=False)
    actual_hours = Column(Float)
    completion_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<DailyTask {self.id}>"


class UserMastery(Base):
    __tablename__ = "user_mastery"
    __table_args__ = (
        Index("ix_user_mastery_user_point", "user_id", "knowledge_point_id"),
        Index("ix_user_mastery_user_level", "user_id", "mastery_level"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True)
    mastery_level = Column(Float, default=0.0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    wrong_count = Column(Integer, default=0, nullable=False)
    last_practice_time = Column(DateTime(timezone=True))
    next_review_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserMastery U{self.user_id}-KP{self.knowledge_point_id}>"
