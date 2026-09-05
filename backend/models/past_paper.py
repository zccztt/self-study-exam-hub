# -*- coding: utf-8 -*-
"""Past paper (历年真题) model."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.sql import func

from backend.models import Base


class PastPaper(Base):
    """历年真题试卷（完整一套官方试卷）"""
    __tablename__ = "past_papers"
    __table_args__ = (
        Index("ix_past_papers_subject_year", "subject_id", "year", "month"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)  # e.g. "2024年10月 行政管理学 真题"
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False)  # 4 or 10
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=True)  # NULL=全国统考
    total_score = Column(Integer, default=100, nullable=False)
    duration = Column(Integer, default=150, nullable=False)  # 分钟
    question_ids = Column(JSON, nullable=False)  # 有序题目ID列表
    paper_config = Column(JSON)  # 题型配分结构
    source = Column(String(200))  # 来源标注
    is_published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<PastPaper {self.id} - {self.name}>"
