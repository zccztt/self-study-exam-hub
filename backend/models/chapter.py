# -*- coding: utf-8 -*-
"""
章节和知识点模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.models import Base


class Chapter(Base):
    """章节表"""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True, comment="章节ID")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True, comment="科目ID")
    name = Column(String(200), nullable=False, comment="章节名称")
    order = Column(Integer, default=0, comment="排序")
    parent_id = Column(Integer, ForeignKey("chapters.id"), comment="父章节ID")
    description = Column(Text, comment="章节描述")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Chapter {self.id} - {self.name}>"


class KnowledgePoint(Base):
    """知识点表"""
    __tablename__ = "knowledge_points"

    id = Column(Integer, primary_key=True, index=True, comment="知识点ID")
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True, comment="章节ID")
    name = Column(String(200), nullable=False, comment="知识点名称")
    description = Column(Text, comment="知识点描述")
    importance = Column(String(20), default="medium", comment="重要程度（low/medium/high）")
    frequency = Column(Integer, default=0, comment="考试频次")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<KnowledgePoint {self.id} - {self.name}>"


class QuestionKnowledgePoint(Base):
    """题目-知识点关联表"""
    __tablename__ = "question_knowledge_points"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True, comment="题目ID")
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True, comment="知识点ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<QuestionKnowledgePoint Q{self.question_id}-KP{self.knowledge_point_id}>"
