# -*- coding: utf-8 -*-
"""
视频模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from backend.models import Base


class VideoSource(str, enum.Enum):
    """视频来源枚举"""
    BILIBILI = "bilibili"
    NETEASE = "netease"
    TENCENT = "tencent"
    YOUTUBE = "youtube"
    CUSTOM = "custom"


class Video(Base):
    """视频表"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, comment="视频ID")
    title = Column(String(300), nullable=False, comment="视频标题")
    url = Column(String(500), nullable=False, comment="视频URL")
    source = Column(SQLEnum(VideoSource), nullable=False, index=True, comment="视频来源")
    duration = Column(Integer, comment="时长（秒）")
    author = Column(String(100), comment="作者")
    view_count = Column(Integer, default=0, comment="观看次数")
    publish_date = Column(DateTime(timezone=True), comment="发布日期")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True, comment="科目ID")
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True, comment="章节ID")
    thumbnail = Column(String(500), comment="缩略图URL")
    description = Column(Text, comment="视频描述")
    tags = Column(JSON, comment="标签")
    is_active = Column(Integer, default=1, comment="是否有效（0=失效，1=有效）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Video {self.id} - {self.title}>"


class VideoKnowledgePoint(Base):
    """视频-知识点关联表"""
    __tablename__ = "video_knowledge_points"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True, comment="视频ID")
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True, comment="知识点ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<VideoKnowledgePoint V{self.video_id}-KP{self.knowledge_point_id}>"


class VideoQuestion(Base):
    """视频-题目关联表"""
    __tablename__ = "video_questions"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True, comment="视频ID")
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True, comment="题目ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<VideoQuestion V{self.video_id}-Q{self.question_id}>"
