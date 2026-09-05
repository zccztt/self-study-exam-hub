# -*- coding: utf-8 -*-
"""Resource / attachment models for questions and past-paper sources."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class Resource(Base):
    """统一资源表 —— PDF / 图片上传到 MinIO，视频保存外部链接。"""

    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, comment="原始文件名或链接标题")
    media_type = Column(String(20), nullable=False, index=True, comment="pdf/image/video/doc")
    storage_type = Column(String(20), nullable=False, comment="minio/external_link")
    minio_object = Column(String(500), nullable=True, comment="MinIO 对象路径")
    external_url = Column(String(1000), nullable=True, comment="外部链接 URL")
    content_type = Column(String(100), nullable=True, comment="MIME type")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    file_hash = Column(String(64), nullable=True, index=True, comment="SHA-256 前缀，去重用")
    content_text = Column(Text, nullable=True, comment="提取/OCR 的文字")
    ocr_status = Column(
        String(20), nullable=False, default="pending",
        comment="pending/processing/completed/failed/skipped",
    )
    thumbnail_object = Column(String(500), nullable=True, comment="缩略图 MinIO 路径")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Resource {self.id} {self.media_type}/{self.storage_type}>"


class QuestionResource(Base):
    """题目 ↔ 资源 多对多关联。"""

    __tablename__ = "question_resources"

    question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    resource_id = Column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sort_order = Column(Integer, nullable=False, default=0, comment="排序序号")


class PaperSourceResource(Base):
    """真题卷源 ↔ 资源 多对多关联。"""

    __tablename__ = "paper_source_resources"

    paper_source_id = Column(
        Integer, ForeignKey("past_paper_sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    resource_id = Column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sort_order = Column(Integer, nullable=False, default=0, comment="排序序号")
