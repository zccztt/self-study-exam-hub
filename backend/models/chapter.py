# -*- coding: utf-8 -*-
"""Chapter and knowledge point models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    order = Column(Integer, default=0, nullable=False)
    parent_id = Column(Integer, ForeignKey("chapters.id"))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Chapter {self.id} - {self.name}>"


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    importance = Column(String(20), default="medium", nullable=False)
    frequency = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgePoint {self.id} - {self.name}>"


class QuestionKnowledgePoint(Base):
    __tablename__ = "question_knowledge_points"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<QuestionKnowledgePoint Q{self.question_id}-KP{self.knowledge_point_id}>"
