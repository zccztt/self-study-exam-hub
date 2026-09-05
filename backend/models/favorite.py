# -*- coding: utf-8 -*-
"""Favorite models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Text, UniqueConstraint
from sqlalchemy.sql import func

from backend.models import Base


class QuestionFavorite(Base):
    __tablename__ = "question_favorites"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_question_favorites_user_question"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    tags = Column(JSON)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<QuestionFavorite U{self.user_id}-Q{self.question_id}>"


class VideoFavorite(Base):
    __tablename__ = "video_favorites"
    __table_args__ = (UniqueConstraint("user_id", "video_id", name="uq_video_favorites_user_video"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<VideoFavorite U{self.user_id}-V{self.video_id}>"
