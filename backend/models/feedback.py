# -*- coding: utf-8 -*-
"""Grading feedback model for correction loop."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class GradingFeedback(Base):
    __tablename__ = "grading_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    feedback_type = Column(String(32), nullable=False)  # score_error, explanation_error, missing_point, other
    expected_score = Column(Integer)
    reason = Column(Text, nullable=False)
    evidence = Column(Text)  # 用户提供的教材引用等
    status = Column(String(32), default="pending", nullable=False)  # pending, accepted, rejected
    admin_comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<GradingFeedback {self.id} Q{self.question_id}>"
