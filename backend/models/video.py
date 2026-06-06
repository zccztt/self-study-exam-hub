# -*- coding: utf-8 -*-
"""Video models."""

import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class VideoSource(str, enum.Enum):
    BILIBILI = "bilibili"
    NETEASE = "netease"
    TENCENT = "tencent"
    YOUTUBE = "youtube"
    CUSTOM = "custom"


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    url = Column(String(500), nullable=False)
    source = Column(String(32), nullable=False, index=True)
    duration = Column(Integer)
    author = Column(String(100))
    view_count = Column(Integer, default=0, nullable=False)
    publish_date = Column(DateTime(timezone=True))
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True)
    thumbnail = Column(String(500))
    description = Column(Text)
    tags = Column(JSON)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Video {self.id} - {self.title}>"


class VideoKnowledgePoint(Base):
    __tablename__ = "video_knowledge_points"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<VideoKnowledgePoint V{self.video_id}-KP{self.knowledge_point_id}>"


class VideoQuestion(Base):
    __tablename__ = "video_questions"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<VideoQuestion V{self.video_id}-Q{self.question_id}>"
