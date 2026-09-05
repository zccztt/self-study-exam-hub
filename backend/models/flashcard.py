# -*- coding: utf-8 -*-
"""Flashcard model for spaced repetition learning."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), index=True)

    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    card_type = Column(String(20), default="auto", nullable=False)  # auto | custom
    tags = Column(String(500))

    # SM-2 spaced repetition state
    ease_factor = Column(Float, default=2.5, nullable=False)
    interval_days = Column(Integer, default=1, nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    next_review = Column(DateTime(timezone=True), nullable=False, index=True)
    last_review = Column(DateTime(timezone=True))

    is_suspended = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Flashcard {self.id} U{self.user_id}>"
