# -*- coding: utf-8 -*-
"""
用户收藏模型
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.models import Base


class QuestionFavorite(Base):
    """题目收藏表"""
    __tablename__ = "question_favorites"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True, comment="题目ID")
    tags = Column(JSON, comment="自定义标签")
    note = Column(JSON, comment="笔记")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<QuestionFavorite U{self.user_id}-Q{self.question_id}>"


class VideoFavorite(Base):
    """视频收藏表"""
    __tablename__ = "video_favorites"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True, comment="视频ID")
    note = Column(JSON, comment="笔记")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<VideoFavorite U{self.user_id}-V{self.video_id}>"
