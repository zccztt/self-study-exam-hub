# -*- coding: utf-8 -*-
"""
科目模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from backend.models import Base


class Subject(Base):
    """科目表"""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True, comment="科目ID")
    code = Column(String(20), unique=True, nullable=False, index=True, comment="科目代码")
    name = Column(String(100), nullable=False, comment="科目名称")
    category = Column(String(50), comment="科目分类（公共课/专业课）")
    description = Column(Text, comment="科目描述")
    exam_duration = Column(Integer, default=150, comment="考试时长（分钟）")
    total_score = Column(Integer, default=100, comment="总分")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Subject {self.code} - {self.name}>"
